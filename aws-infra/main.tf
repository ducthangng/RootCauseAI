data "aws_caller_identity" "me" {}

data "aws_ssm_parameter" "al2023_ami" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

locals {
  name       = "rootcause"
  param_path = "/rootcause" # every env var of the app lives here as /rootcause/<ENV_NAME>
  cert_key   = "certs/${var.api_fqdn}/letsencrypt${var.use_staging_cert ? "-staging" : ""}.tgz"
  db_name    = "rootcause"
  db_user    = "rootcause"
}

# ---- Security groups ---------------------------------------------------------
# No port 22: use SSM Session Manager (`make shell`).
resource "aws_security_group" "api" {
  name_prefix = "${local.name}-api-"
  description = "RAG API: 80/443 in, all out"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_security_group" "db" {
  name_prefix = "${local.name}-db-"
  description = "Postgres from the API instance only"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.api.id]
  }

  lifecycle {
    create_before_destroy = true
  }
}

# ---- IAM: what the instance may do -------------------------------------------
data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "api" {
  statement {
    sid       = "ReadAppEnv"
    actions   = ["ssm:GetParametersByPath", "ssm:GetParameters", "ssm:GetParameter"]
    resources = [
      "arn:aws:ssm:${var.region}:${data.aws_caller_identity.me.account_id}:parameter${local.param_path}",
      "arn:aws:ssm:${var.region}:${data.aws_caller_identity.me.account_id}:parameter${local.param_path}/*",
    ]
  }

  statement {
    sid     = "ReadReleaseAndCerts"
    actions = ["s3:GetObject"]
    resources = [
      "arn:aws:s3:::${var.artifacts_bucket}/${var.release_key}",
      "arn:aws:s3:::${var.artifacts_bucket}/certs/*",
    ]
  }

  # No s3:ListBucket on purpose: a missing key answers 403 instead of 404, and
  # user_data treats any head-object failure as "not there yet".
  statement {
    sid       = "BackupCerts"
    actions   = ["s3:PutObject"]
    resources = ["arn:aws:s3:::${var.artifacts_bucket}/certs/*"]
  }

  # certbot DNS-01: may only write TXT records named _acme-challenge.<fqdn>.
  statement {
    sid       = "AcmeLookup"
    actions   = ["route53:ListHostedZones", "route53:GetChange"]
    resources = ["*"]
  }

  statement {
    sid       = "AcmeTxtOnly"
    actions   = ["route53:ChangeResourceRecordSets"]
    resources = ["arn:aws:route53:::hostedzone/${var.route53_zone_id}"]

    condition {
      test     = "ForAllValues:StringEquals"
      variable = "route53:ChangeResourceRecordSetsNormalizedRecordNames"
      values   = ["_acme-challenge.${var.api_fqdn}"]
    }

    condition {
      test     = "ForAllValues:StringEquals"
      variable = "route53:ChangeResourceRecordSetsRecordTypes"
      values   = ["TXT"]
    }
  }
}

resource "aws_iam_role" "api" {
  name_prefix        = "${local.name}-api-"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.api.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy" "api" {
  name   = "api"
  role   = aws_iam_role.api.id
  policy = data.aws_iam_policy_document.api.json
}

resource "aws_iam_instance_profile" "api" {
  name_prefix = "${local.name}-api-"
  role        = aws_iam_role.api.name
}

# ---- RDS ---------------------------------------------------------------------
resource "random_password" "db" {
  length  = 32
  special = false
}

resource "aws_db_subnet_group" "this" {
  name       = "${local.name}-db"
  subnet_ids = var.db_subnet_ids
}

resource "aws_db_instance" "this" {
  identifier        = "${local.name}-db"
  engine            = "postgres"
  engine_version    = var.db_engine_version
  instance_class    = var.db_instance_class
  allocated_storage = var.db_storage_gb
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = local.db_name
  username = local.db_user
  password = random_password.db.result

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false
  multi_az               = false

  # Ephemeral by design: data is re-loaded from S3 after every `make up`.
  backup_retention_period = 0
  skip_final_snapshot     = true
  deletion_protection     = false
  apply_immediately       = true

  lifecycle {
    ignore_changes = [engine_version]
  }
}

# ---- App env: /rootcause/<NAME> in SSM Parameter Store ------------------------
# Terraform owns the DB_* params (they change every `up`).
# You own everything else, created once by hand, e.g.:
#   aws ssm put-parameter --name /rootcause/OPENAI_API_KEY --type SecureString --value sk-...
# The instance loads the whole path at boot, so a new env var needs NO Terraform change.
resource "aws_ssm_parameter" "plain" {
  for_each = {
    DB_HOST = aws_db_instance.this.address
    DB_PORT = tostring(aws_db_instance.this.port)
    DB_NAME = local.db_name
    DB_USER = local.db_user
  }

  name  = "${local.param_path}/${each.key}"
  type  = "String"
  value = each.value
}

resource "aws_ssm_parameter" "db_password" {
  name  = "${local.param_path}/DB_PASSWORD"
  type  = "SecureString"
  value = random_password.db.result
}

# ---- API instance ------------------------------------------------------------
resource "aws_instance" "api" {
  ami                         = data.aws_ssm_parameter.al2023_ami.value
  instance_type               = var.instance_type
  subnet_id                   = var.public_subnet_id
  associate_public_ip_address = true
  vpc_security_group_ids      = [aws_security_group.api.id]
  iam_instance_profile        = aws_iam_instance_profile.api.name

  user_data = templatefile("${path.module}/user_data.sh.tpl", {
    region         = var.region
    fqdn           = var.api_fqdn
    email          = var.letsencrypt_email
    bucket         = var.artifacts_bucket
    cert_key       = local.cert_key
    release_key    = var.release_key
    param_path     = local.param_path
    app_module     = var.app_module
    python_version = var.python_version
    staging_flag   = var.use_staging_cert ? "--staging" : ""
  })
  user_data_replace_on_change = true

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  root_block_device {
    volume_type = "gp3"
    volume_size = 20
    encrypted   = true
  }

  tags = { Name = "${local.name}-api" }

  # Env params + IAM must exist before first boot.
  depends_on = [
    aws_ssm_parameter.plain,
    aws_ssm_parameter.db_password,
    aws_iam_role_policy.api,
    aws_iam_role_policy_attachment.ssm_core,
  ]

  lifecycle {
    ignore_changes = [ami] # newer AL2023 must not replace a running box
  }
}

# ---- DNS: the record that changes on every `up` --------------------------------
# Zone not in Route53 (e.g. Cloudflare)? Replace this resource AND the certbot
# plugin in user_data.sh.tpl.
resource "aws_route53_record" "api" {
  zone_id         = var.route53_zone_id
  name            = var.api_fqdn
  type            = "A"
  ttl             = 60
  records         = [aws_instance.api.public_ip]
  allow_overwrite = true
}
