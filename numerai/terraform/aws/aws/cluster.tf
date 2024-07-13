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

data "aws_ami" "ecs_al2" {
  most_recent = true
  filter {
    name   = "name"
    values = ["amzn2-ami-ecs-hvm-*-x86_64-ebs"]
  }
}

resource "aws_launch_template" "node" {
  image_id = data.aws_ami.ecs_al2.id
  update_default_version = true
  dynamic "block_device_mappings" {
    for_each = local.max_node_volume_size > 0 ? {size: local.max_node_volume_size} : {}
    content {
      device_name = "/dev/xvda"

      ebs {
        encrypted = true
        volume_size = local.max_node_volume_size
        volume_type = "gp3"
      }
    }
  }
}

resource "aws_batch_compute_environment" "node" {
  compute_environment_name_prefix = "${local.node_prefix}-"

  compute_resources {
    instance_role = aws_iam_instance_profile.batch_ecs_instance_role.arn

    launch_template {
      launch_template_id = aws_launch_template.node.id
      version            = aws_launch_template.node.latest_version
    }

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

  lifecycle {
    create_before_destroy = true
  }
}


resource "aws_batch_job_queue" "node" {
  name = "${local.node_prefix}-queue"

  state    = "ENABLED"
  priority = 1

  compute_environment_order {
    order = 1
    compute_environment = aws_batch_compute_environment.node.arn
  }
}


#############
# Job Setup #
#############

resource "aws_cloudwatch_log_group" "ec2" {
  for_each = { for name, config in var.nodes : name => config }

  name              = "/ec2/service/${each.key}"
  retention_in_days = "14"
}

resource "aws_batch_job_definition" "node" {
  for_each = { for name, config in var.nodes : name => config }

  name = each.key
  type = "container"
  timeout {
    attempt_duration_seconds = each.value.timeout_minutes * 60
  }

  retry_strategy {
    attempts = 2
    evaluate_on_exit {
      on_reason = "CannotInspectContainerError:*"
      action    = "RETRY"
    }
    evaluate_on_exit {
      on_reason = "CannotPullContainerError:*"
      action    = "RETRY"
    }
    evaluate_on_exit {
      action    = "RETRY"
      on_reason = "CannotStartContainerError:*"
    }
    evaluate_on_exit {
      action    = "RETRY"
      on_reason = "Task failed to start"
    }
    evaluate_on_exit {
      action    = "EXIT"
      on_reason = "*"
    }
  }

  container_properties = jsonencode({
    image            = aws_ecr_repository.node[each.key].repository_url
    executionRoleArn = aws_iam_role.ecs_task_execution_role.arn

    logConfiguration = {
      "logDriver" : "awslogs",
      "options" : {
        "awslogs-group" : aws_cloudwatch_log_group.ec2[each.key].name,
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
