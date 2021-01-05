terraform {
  required_version = "~> 0.14.0"
}

# Specify the provider and access details
provider "aws" {
  profile = "default"
  region  = var.aws_region
  version = "~> 3.22.0"
}

### Network

# Fetch AZs in the current region
data "aws_availability_zones" "available" {}

resource "aws_vpc" "main" {
  cidr_block = "172.17.0.0/16"
}

# Create var.az_count public subnets, each in a different AZ
resource "aws_subnet" "public" {
  count                   = var.az_count
  cidr_block              = cidrsubnet(aws_vpc.main.cidr_block, 8, var.az_count + count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  vpc_id                  = aws_vpc.main.id
  map_public_ip_on_launch = true
}

# IGW for the public subnet
resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id
}

# Route the public subnet traffic through the IGW
resource "aws_route" "internet_access" {
  route_table_id         = aws_vpc.main.main_route_table_id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.gw.id
}

### Security

# Traffic to the ECS Cluster security group
resource "aws_security_group" "ecs_tasks" {
  name        = "${var.app_name}-tasks"
  description = "allow inbound access from evertone"
  vpc_id      = aws_vpc.main.id

  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
  }
}

### IAM

resource "aws_iam_role" "ecsTaskExecutionRole" {
  name               = "${var.app_name}-ecs"
  assume_role_policy = data.aws_iam_policy_document.assume_role_policy.json
}

data "aws_iam_policy_document" "assume_role_policy" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy_attachment" "ecsTaskExecutionRole_policy" {
  role       = aws_iam_role.ecsTaskExecutionRole.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

### Cloudwatch

resource "aws_cloudwatch_log_group" "logs" {
  name              = "/fargate/service/${var.app_name}"
  retention_in_days = "14"
}

### ECR

resource "aws_ecr_repository" "app" {
  name = var.app_name
}

### ECS

resource "aws_ecs_cluster" "main" {
  name = "${var.app_name}-ecs-cluster"
}

resource "aws_ecs_task_definition" "app" {
  family                   = var.app_name
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.fargate_cpu
  memory                   = var.fargate_memory
  execution_role_arn       = aws_iam_role.ecsTaskExecutionRole.arn

  container_definitions = jsonencode([
    {
      cpu:var.fargate_cpu,
      image: aws_ecr_repository.app.repository_url,
      memory:var.fargate_memory,
      name: "app",
      networkMode: "awsvpc",
      portMappings: [
        {
          containerPort: var.app_port,
          hostPort: var.app_port
        }
      ],
      logConfiguration: {
          "logDriver": "awslogs",
          "options": {
              "awslogs-group": "/fargate/service/${var.app_name}",
              "awslogs-region": var.aws_region,
              "awslogs-stream-prefix": "ecs"
          }
      }
    }
  ])
}

### Lambda
resource "aws_iam_role" "iam_for_lambda" {
  name = "${var.app_name}-lambda"

  assume_role_policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
      {
        Action: "sts:AssumeRole",
        Principal: {
          "Service": "lambda.amazonaws.com"
        },
        Effect: "Allow",
        Sid: ""
      }
    ]
  })
}

# This is to optionally manage the CloudWatch Log Group for the Lambda Function.
# If skipping this resource configuration, also add "logs:CreateLogGroup" to the IAM policy below.
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.app_name}"
  retention_in_days = 14
}

# See also the following AWS managed policy: AWSLambdaBasicExecutionRole
resource "aws_iam_policy" "lambda_logging" {
  name        = "${var.app_name}_lambda_logging"
  path        = "/"
  description = "IAM policy for logging from a lambda"

  policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
      {
        Action: [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource: "arn:aws:logs:*:*:*",
        Effect: "Allow"
      },
      {
        Effect: "Allow",
        Action: "ecs:RunTask",
        Resource: "*"
      },
      {
        Effect: "Allow",
        Action: "iam:PassRole",
        Resource: aws_iam_role.ecsTaskExecutionRole.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.iam_for_lambda.name
  policy_arn = aws_iam_policy.lambda_logging.arn
}

resource "aws_iam_role_policy_attachment" "lambda_ecsTaskExecutionRole" {
  role       = aws_iam_role.iam_for_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "archive_file" "exports_js" {
  source_file = "exports.js"
  output_path = "exports.zip"
  type = "zip"
}

resource "aws_lambda_function" "submission" {
  filename      = archive_file.exports_js
  function_name = var.app_name
  role          = aws_iam_role.iam_for_lambda.arn
  handler       = "exports.handler"

  # The filebase64sha256() function is available in Terraform 0.11.12 and later
  # For Terraform 0.11.11 and earlier, use the base64sha256() function and the file() function:
  # source_code_hash = "${base64sha256(file("lambda_function_payload.zip"))}"
  source_code_hash = filebase64sha256("lambda.zip")

  runtime    = "nodejs10.x"
  depends_on = [
    "aws_iam_role_policy_attachment.lambda_logs",
    "aws_iam_role_policy_attachment.lambda_ecsTaskExecutionRole",
    "aws_cloudwatch_log_group.lambda"
  ]

  environment {
    variables = {
      ecs_arn            = aws_ecs_task_definition.app.arn
      ecs_cluster        = aws_ecs_cluster.main.id
      ecs_security_group = aws_security_group.ecs_tasks.id
      ecs_subnet         = aws_subnet.public.*.id[0]
    }
  }
}

resource "aws_api_gateway_rest_api" "app" {
  name        = "${var.app_name}-gateway"
  description = "Terraform Serverless Application for ${var.app_name}"
}

resource "aws_api_gateway_resource" "submit" {
  rest_api_id = aws_api_gateway_rest_api.app.id
  parent_id   = aws_api_gateway_rest_api.app.root_resource_id
  path_part   = "submit"
}

resource "aws_api_gateway_method" "submit" {
  rest_api_id   = aws_api_gateway_rest_api.app.id
  resource_id   = aws_api_gateway_resource.submit.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "submit" {
  rest_api_id = aws_api_gateway_rest_api.app.id
  resource_id = aws_api_gateway_method.submit.resource_id
  http_method = aws_api_gateway_method.submit.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.submission.invoke_arn
}

resource "aws_api_gateway_deployment" "app" {
  depends_on = [
    "aws_api_gateway_integration.submit",
  ]

  rest_api_id = aws_api_gateway_rest_api.app.id
  stage_name  = var.gateway_stage_path
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.submission.arn
  principal     = "apigateway.amazonaws.com"

  # The /*/* portion grants access from any method on any resource
  # within the API Gateway "REST API".
  source_arn = "${replace(aws_api_gateway_deployment.app.execution_arn, "${var.gateway_stage_path}", "")}*/*"
}
