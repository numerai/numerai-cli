locals {
  node_prefix = "numerai-submission"
  node_names = flatten([for node in var.nodes: [
    "${local.node_prefix}-${node.name}"
  ]])
}
