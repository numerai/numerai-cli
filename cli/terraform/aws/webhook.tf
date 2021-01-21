
### Lambda
resource "aws_lambda_layer_version" "node_modules" {
  layer_name = "node_modules"
  filename = "layer.zip"
}

resource "aws_lambda_function" "submission" {
  filename      = "lambda.zip"
  function_name = local.app_prefix
  role          = aws_iam_role.iam_for_lambda.arn
  handler       = "exports.handler"

  # The filebase64sha256() function is available in Terraform 0.11.12 and later
  # For Terraform 0.11.11 and earlier, use the base64sha256() function and the file() function:
  # source_code_hash = "${base64sha256(file("lambda_function_payload.zip"))}"
  source_code_hash = filebase64sha256("lambda.zip")

  runtime    = "nodejs10.x"
  depends_on = [
    aws_iam_role_policy_attachment.lambda_logs,
    aws_iam_role_policy_attachment.lambda_ecsTaskExecutionRole,
    aws_cloudwatch_log_group.lambda
  ]

  layers = [
    aws_lambda_layer_version.node_modules.arn
  ]

  environment {
    variables = {
      security_group = aws_security_group.ecs_tasks.id
      subnet         = aws_subnet.public.*.id[0]
      ecs_cluster    = aws_ecs_cluster.main.id
      ecs_task_arns  = jsonencode([for task_def in aws_ecs_task_definition.app: task_def.arn])
    }
  }
}


### Cloudwatch
# This is to optionally manage the CloudWatch Log Group for the Lambda Function.
# If skipping this resource configuration, also add "logs:CreateLogGroup" to the IAM policy below.
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${local.app_prefix}"
  retention_in_days = 14
}


### API Gateway
resource "aws_api_gateway_rest_api" "app" {
  name        = "${local.app_prefix}-gateway"
  description = "API Gateway for Numerai webhook"
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
    aws_api_gateway_integration.submit,
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
  source_arn = "${replace(aws_api_gateway_deployment.app.execution_arn, var.gateway_stage_path, "")}*/*"
}


### IAM
resource "aws_iam_role" "iam_for_lambda" {
  name = "${local.app_prefix}-lambda"

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

# See also the following AWS managed policy: AWSLambdaBasicExecutionRole
resource "aws_iam_policy" "lambda_logging" {
  name        = "${local.app_prefix}-lambda-logging"
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
