# ---- Must set (see terraform.tfvars.example) --------------------------------
variable "region" {
  type        = string
  description = "Region of the existing VPC."
}

variable "vpc_id" {
  type        = string
  description = "Existing permanent VPC."
}

variable "public_subnet_id" {
  type        = string
  description = "Public subnet (route to an IGW) for the API instance."
}

variable "db_subnet_ids" {
  type        = list(string)
  description = "At least 2 subnets in different AZs for the RDS subnet group (private is fine, RDS needs no internet)."
}

variable "route53_zone_id" {
  type        = string
  description = "Hosted zone that contains api_fqdn."
}

variable "api_fqdn" {
  type        = string
  description = "e.g. api.aws.rootcause.ducthang.dev (lowercase)."

  validation {
    condition     = var.api_fqdn == lower(var.api_fqdn)
    error_message = "api_fqdn must be lowercase (the IAM condition on _acme-challenge compares exact strings)."
  }
}

variable "letsencrypt_email" {
  type = string
}

variable "artifacts_bucket" {
  type        = string
  description = "Existing bucket. Holds releases/ (app tarball from CI) and certs/ (Let's Encrypt backup)."
}

# ---- Sensible defaults -------------------------------------------------------
variable "release_key" {
  type        = string
  default     = "releases/rag-api-latest.tar.gz"
  description = "S3 key of the app tarball. requirements.txt must be at the archive root."
}

variable "app_module" {
  type        = string
  default     = "app.main:app"
  description = "uvicorn target."
}

variable "use_staging_cert" {
  type        = bool
  default     = false
  description = "true while iterating on user_data: staging certs are untrusted but have generous rate limits. Uses a separate S3 backup key."
}

variable "instance_type" {
  type    = string
  default = "t3.small"
}

variable "python_version" {
  type    = string
  default = "3.11"
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "db_engine_version" {
  type        = string
  default     = "16"
  description = "Major only; RDS picks the latest minor. pgvector needs >= 15."
}

variable "db_storage_gb" {
  type    = number
  default = 20
}
