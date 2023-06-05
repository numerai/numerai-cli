
### ECS
resource "aws_ecs_cluster" "main" {
  name = local.node_prefix
}

resource "aws_ecs_task_definition" "node" {
  for_each = { for name, config in var.nodes : name => config }

  family                   = each.key
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = each.value.cpu
  memory                   = each.value.memory
  execution_role_arn       = aws_iam_role.ecsTaskExecutionRole.arn

  container_definitions = jsonencode([
    {
      cpu : parseint(each.value.cpu, 10),
      image : aws_ecr_repository.node[each.key].repository_url,
      memory : parseint(each.value.memory, 10),
      name : each.key,
      networkMode : "awsvpc",
      portMappings : [
        {
          containerPort : var.node_container_port,
          hostPort : var.node_container_port
        }
      ],
      logConfiguration : {
        "logDriver" : "awslogs",
        "options" : {
          "awslogs-group" : aws_cloudwatch_log_group.ecs[each.key].name,
          "awslogs-region" : var.aws_region,
          "awslogs-stream-prefix" : "ecs"
        }
      }
    }
  ])
}


### Cloudwatch
resource "aws_cloudwatch_log_group" "ecs" {
  for_each = { for name, config in var.nodes : name => config }

  name              = "/fargate/service/${each.key}"
  retention_in_days = "14"
}


### ECR
resource "aws_ecr_repository" "node" {
  for_each     = { for name, config in var.nodes : name => config }
  force_delete = true
  name         = each.key
}


### IAM
resource "aws_iam_role" "ecsTaskExecutionRole" {
  name = "${local.node_prefix}-ecs"
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

resource "aws_iam_role_policy_attachment" "ecsTaskExecutionRole_policy" {
  role       = aws_iam_role.ecsTaskExecutionRole.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}
