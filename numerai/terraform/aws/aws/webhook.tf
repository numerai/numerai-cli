
### Lambda
resource "aws_lambda_function" "submission" {
  for_each = { for name, config in var.nodes : name => config }

  filename      = "${path.module}/main.zip"
  function_name = each.key
  role          = aws_iam_role.iam_for_lambda.arn
  handler       = "main.lambda_handler"

  source_code_hash = filebase64sha256("${path.module}/main.zip")

  runtime = "python3.11"

  environment {
    variables = {
      JOB_DEFINITION = aws_batch_job_definition.node[each.key].name
      JOB_QUEUE      = aws_batch_job_queue.node.name
    }
  }
}

resource "aws_lambda_function_url" "submission" {
  for_each = { for name, config in var.nodes : name => config }

  function_name      = aws_lambda_function.submission[each.key].function_name
  authorization_type = "NONE"
}


### Cloudwatch
# This is to optionally manage the CloudWatch Log Group for the Lambda Function.
# If skipping this resource configuration, also add "logs:CreateLogGroup" to the IAM policy below.
resource "aws_cloudwatch_log_group" "lambda" {
  for_each = { for name, config in var.nodes : name => config }

  name              = "/aws/lambda/${each.key}"
  retention_in_days = 14
}


# cron triggers
resource "aws_cloudwatch_event_rule" "cron_trigger" {
  for_each = {
    for name, config in var.nodes :
    name => lookup(config, "cron", null)
    if lookup(config, "cron", null) != null
  }

  name                = "${each.key}-cron-trigger"
  description         = "Cron-based trigger for lambda ${aws_lambda_function.submission[each.key].arn}"
  schedule_expression = "cron(${trim(each.value, "\"")})"
}
resource "aws_cloudwatch_event_target" "cron_target" {
  for_each = {
    for name, config in var.nodes :
    name => lookup(config, "cron", null)
    if lookup(config, "cron", null) != null
  }

  rule = aws_cloudwatch_event_rule.cron_trigger[each.key].name
  arn  = aws_lambda_function.submission[each.key].arn
}
resource "aws_lambda_permission" "cron_permission" {
  for_each = {
    for name, config in var.nodes :
    name => lookup(config, "cron", null)
    if lookup(config, "cron", null) != null
  }
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.submission[each.key].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.cron_trigger[each.key].arn
}


########################
# Lambda Function Role #
########################

resource "aws_iam_role" "iam_for_lambda" {
  name = "${local.node_prefix}-lambda"

  assume_role_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        Action : "sts:AssumeRole",
        Principal : {
          "Service" : "lambda.amazonaws.com"
        },
        Effect : "Allow",
        Sid : ""
      }
    ]
  })
}

resource "aws_iam_policy" "lambda_logging" {
  name        = "${local.node_prefix}-lambda-logging"
  path        = "/"
  description = "IAM policy for logging from a lambda"

  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        Action : [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource : "arn:aws:logs:*:*:*",
        Effect : "Allow"
      },
      {
        Effect : "Allow",
        Action : "batch:SubmitJob",
        Resource : "*"
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.iam_for_lambda.name
  policy_arn = aws_iam_policy.lambda_logging.arn
}
