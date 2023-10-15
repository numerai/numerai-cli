###############
# ECR and IAM #
###############

resource "aws_ecr_repository" "node" {
  for_each     = { for name, config in var.nodes : name => config }
  force_delete = true
  name         = each.key
}

resource "aws_iam_role" "ecs_task_execution_role" {
  name = local.node_prefix
  assume_role_policy = jsonencode({
    Version : "2012-10-17",
    Statement : [{
      Effect : "Allow",
      Action : "sts:AssumeRole",
      Principal : {
        Service : [
          "ecs-tasks.amazonaws.com"
        ]
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_role" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}


#############################
# Batch compute environment #
#############################
data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "batch_ecs_instance_role" {
  name               = "batch_ecs_instance_role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json
}

resource "aws_iam_role_policy_attachment" "batch_ecs_instance_role" {
  role       = aws_iam_role.batch_ecs_instance_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
}

resource "aws_iam_instance_profile" "batch_ecs_instance_role" {
  name = "batch_ecs_instance_role"
  role = aws_iam_role.batch_ecs_instance_role.name
}

data "aws_iam_policy_document" "batch_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["batch.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "aws_batch_service_role" {
  name               = "aws_batch_service_role"
  assume_role_policy = data.aws_iam_policy_document.batch_assume_role.json
}

resource "aws_iam_role_policy_attachment" "aws_batch_service_role" {
  role       = aws_iam_role.aws_batch_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole"
}

resource "aws_batch_compute_environment" "node" {
  compute_environment_name = local.node_prefix

  compute_resources {
    instance_role = aws_iam_instance_profile.batch_ecs_instance_role.arn

    max_vcpus = 64

    security_group_ids = [
      aws_security_group.ecs_tasks.id
    ]

    subnets = [for s in aws_subnet.public : s.id]

    type                = "EC2"
    allocation_strategy = "BEST_FIT"
    instance_type       = ["optimal"]
  }

  service_role = aws_iam_role.aws_batch_service_role.arn
  type         = "MANAGED"
  depends_on   = [aws_iam_role_policy_attachment.aws_batch_service_role]
}


#############
# Job Setup #
#############

resource "aws_cloudwatch_log_group" "ecs" {
  for_each = { for name, config in var.nodes : name => config }

  name              = "/ec2/service/${each.key}"
  retention_in_days = "14"
}


resource "aws_batch_job_queue" "node" {
  for_each = { for name, config in var.nodes : name => config }

  name = each.key

  state    = "ENABLED"
  priority = 1

  compute_environments = [
    aws_batch_compute_environment.node.arn
  ]
}

resource "aws_batch_job_definition" "node" {
  for_each = { for name, config in var.nodes : name => config }

  name = each.key
  type = "container"
  timeout {
    attempt_duration_seconds = 3600
  }

  container_properties = jsonencode({
    image            = aws_ecr_repository.node[each.key].repository_url
    executionRoleArn = aws_iam_role.ecs_task_execution_role.arn

    logConfiguration = {
      "logDriver" : "awslogs",
      "options" : {
        "awslogs-group" : aws_cloudwatch_log_group.ecs[each.key].name,
        "awslogs-region" : var.aws_region,
        "awslogs-stream-prefix" : "ecs"
      }
    }

    resourceRequirements = [
      {
        type  = "VCPU"
        value = tostring(each.value.cpu / 1024)
      },
      {
        type  = "MEMORY"
        value = tostring(each.value.memory)
      }
    ]
  })
}
