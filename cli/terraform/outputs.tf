output "submission_url" {
  value = module.aws[0].submission_url
}

output "docker_repos" {
  value = jsondecode(jsonencode(module.aws[0].docker_repos))
}
