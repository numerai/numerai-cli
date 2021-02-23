
### ECS
resource "aws_ecs_cluster" "main" {
  name = local.node_prefix
}

resource "aws_ecs_task_definition" "node" {
  count = length(var.nodes)
  family                   = local.node_names[count.index]
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.nodes[count.index].cpu
  memory                   = var.nodes[count.index].memory
  execution_role_arn       = aws_iam_role.ecsTaskExecutionRole.arn

  container_definitions = jsonencode([
    {
      cpu: var.nodes[count.index].cpu,
      image: aws_ecr_repository.node[count.index].repository_url,
      memory: var.nodes[count.index].memory,
      name: local.node_names[count.index],
      networkMode: "awsvpc",
      portMappings: [
        {
          containerPort: var.node_container_port,
          hostPort: var.node_container_port
        }
      ],
      logConfiguration: {
          "logDriver": "awslogs",
          "options": {
              "awslogs-group": aws_cloudwatch_log_group.ecs[count.index].name,
              "awslogs-region": var.aws_region,
              "awslogs-stream-prefix": "ecs"
          }
      }
    }
  ])
}


### Cloudwatch
resource "aws_cloudwatch_log_group" "ecs" {
  count = length(var.nodes)
  name              = "/fargate/service/${local.node_names[count.index]}"
  retention_in_days = "14"
}


### ECR
resource "aws_ecr_repository" "node" {
  count = length(var.nodes)
  name = local.node_names[count.index]
}


### IAM
resource "aws_iam_role" "ecsTaskExecutionRole" {
  name               = "${local.node_prefix}-ecs"
  assume_role_policy = jsonencode({
    Version: "2012-10-17",
    Statement: [{
      Effect: "Allow",
      Action: "sts:AssumeRole",
      Principal: {
        Service: "ecs-tasks.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecsTaskExecutionRole_policy" {
  role       = aws_iam_role.ecsTaskExecutionRole.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}
