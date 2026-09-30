output "api_fqdn" {
  value = var.api_fqdn
}

output "api_url" {
  value = "https://${var.api_fqdn}"
}

output "instance_id" {
  value = aws_instance.api.id
}

output "db_endpoint" {
  value = aws_db_instance.this.address
}

output "env_path" {
  value       = local.param_path
  description = "SSM path holding the app env vars."
}

output "shell" {
  value = "aws ssm start-session --region ${var.region} --target ${aws_instance.api.id}"
}
