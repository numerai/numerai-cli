locals {
  node_prefix = "numerai-submission"
  max_node_volume_size = max([for node, config in var.nodes : lookup(config, "volume", 0)]...)
}
