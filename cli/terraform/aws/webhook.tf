
### Lambda
resource "aws_lambda_layer_version" "node_modules" {
  layer_name = "node_modules"
  filename = "layer.zip"
}

resource "aws_lambda_function" "submission" {
  count = length(var.nodes)
  filename      = "lambda.zip"
  function_name = local.node_names[count.index]
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
      ecs_task_arn  = aws_ecs_task_definition.node[count.index].arn
    }
  }
}


### Cloudwatch
# This is to optionally manage the CloudWatch Log Group for the Lambda Function.
# If skipping this resource configuration, also add "logs:CreateLogGroup" to the IAM policy below.
resource "aws_cloudwatch_log_group" "lambda" {
  count             = length(var.nodes)
  name              = "/aws/lambda/${local.node_names[count.index]}"
  retention_in_days = 14
}
resource "aws_cloudwatch_log_group" "gateway" {
  name              = "/aws/apigateway/${local.node_prefix}"
  retention_in_days = 14
}

### API Gateway
resource "aws_apigatewayv2_api" "submit" {
  name        = "${local.node_prefix}-gateway"
  description = "API Gateway for Numerai webhook"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "submit" {
  count = length(var.nodes)
  api_id = aws_apigatewayv2_api.submit.id
  integration_type = "AWS_PROXY"

  connection_type           = "INTERNET"
  description               = "Serverless Prediction Node Trigger for ${local.node_names[count.index]}"
  integration_method        = "POST"
  integration_uri           = aws_lambda_function.submission[count.index].invoke_arn

}

resource "aws_apigatewayv2_route" "submit" {
  count = length(var.nodes)
  api_id = aws_apigatewayv2_api.submit.id
  route_key = "POST /${var.nodes[count.index].name}"

  target = "integrations/${aws_apigatewayv2_integration.submit[count.index].id}"
}

resource "aws_apigatewayv2_deployment" "submit" {
  api_id = aws_apigatewayv2_api.submit.id

  triggers = {
    redeployment = sha1(join(",", list(
      jsonencode(aws_apigatewayv2_integration.submit),
      jsonencode(aws_apigatewayv2_route.submit),
    )))
  }

  depends_on = [
    aws_apigatewayv2_integration.submit,
    aws_apigatewayv2_route.submit
  ]

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_apigatewayv2_stage" "submit" {
  api_id = aws_apigatewayv2_api.submit.id
  name = "predict"

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.gateway.arn
    format = join(", ", [
      "$context.requestId",
      "$context.identity.sourceIp",
      "$context.requestTime",
      "$context.httpMethod",
      "$context.routeKey",
      "$context.status",
      "$context.error.message",
      "$context.integration.error"
    ])
  }

  auto_deploy = true
}

### IAM
resource "aws_lambda_permission" "gateway" {
  count = length(var.nodes)
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.submission[count.index].arn
  principal     = "apigateway.amazonaws.com"

  # The */* portion grants access from any method on any resource
  # within the API Gateway "REST API".
  source_arn = "${replace(
    aws_apigatewayv2_stage.submit.execution_arn,
    aws_apigatewayv2_stage.submit.name,
    "")}*/*${split(" ", aws_apigatewayv2_route.submit[count.index].route_key)[1]}"
}

resource "aws_iam_role" "iam_for_lambda" {
  name = "${local.node_prefix}-lambda"

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
  name        = "${local.node_prefix}-lambda-logging"
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
