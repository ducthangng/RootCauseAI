#!/bin/bash
# Rendered by Terraform, runs once as root on first boot.
# Log: /var/log/cloud-init-output.log
set -euxo pipefail

export AWS_DEFAULT_REGION="${region}"
FQDN="${fqdn}"
BUCKET="${bucket}"
CERT_KEY="${cert_key}"
RELEASE_KEY="${release_key}"
PY="python${python_version}"

dnf install -y nginx jq "$PY" "$PY-pip"

# ---- 1. App env: every SSM param under ${param_path}/ becomes NAME=value ------
aws ssm get-parameters-by-path --path "${param_path}/" --with-decryption --output json \
  | jq -r '.Parameters[] | "\(.Name | split("/") | last)=\(.Value | tojson)"' > /etc/rootcause.env
chmod 600 /etc/rootcause.env

# ---- 2. TLS: restore cert from S3, else issue via DNS-01, then back up --------
# Restoring instead of re-issuing is what keeps repeated up/down under Let's
# Encrypt's 5-duplicate-certs-per-week limit. No cron: instances are short-lived,
# `renew` at boot covers the 90-day expiry.
$PY -m venv /opt/certbot
/opt/certbot/bin/pip install --quiet certbot certbot-dns-route53
CERTBOT=/opt/certbot/bin/certbot

if aws s3api head-object --bucket "$BUCKET" --key "$CERT_KEY" >/dev/null 2>&1; then
  aws s3 cp "s3://$BUCKET/$CERT_KEY" /tmp/letsencrypt.tgz
  tar -xzf /tmp/letsencrypt.tgz -C /etc
  $CERTBOT renew --quiet   # no-op unless < 30 days left
else
  $CERTBOT certonly --dns-route53 -d "$FQDN" -m "${email}" \
    --agree-tos --non-interactive ${staging_flag}
fi
tar -czf /tmp/letsencrypt.tgz -C /etc letsencrypt
aws s3 cp /tmp/letsencrypt.tgz "s3://$BUCKET/$CERT_KEY"
rm -f /tmp/letsencrypt.tgz

# ---- 3. nginx ------------------------------------------------------------------
cat > /etc/nginx/conf.d/rag-api.conf <<NGINX
server {
  listen 80;
  server_name $FQDN;
  return 301 https://\$host\$request_uri;
}
server {
  listen 443 ssl;
  server_name $FQDN;
  ssl_certificate     /etc/letsencrypt/live/$FQDN/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/$FQDN/privkey.pem;
  location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
  }
}
NGINX
nginx -t
systemctl enable --now nginx

# ---- 4. App: tarball from S3 -> venv -> systemd --------------------------------
if aws s3api head-object --bucket "$BUCKET" --key "$RELEASE_KEY" >/dev/null 2>&1; then
  useradd --system --home /opt/rag-api --shell /sbin/nologin rag || true
  mkdir -p /opt/rag-api
  aws s3 cp "s3://$BUCKET/$RELEASE_KEY" /tmp/release.tgz
  tar -xzf /tmp/release.tgz -C /opt/rag-api
  $PY -m venv /opt/rag-api/venv
  /opt/rag-api/venv/bin/pip install --quiet -r /opt/rag-api/requirements.txt
  chown -R rag:rag /opt/rag-api

  cat > /etc/systemd/system/rag-api.service <<UNIT
[Unit]
Description=RootCause RAG API
After=network-online.target
Wants=network-online.target

[Service]
User=rag
WorkingDirectory=/opt/rag-api
EnvironmentFile=/etc/rootcause.env
ExecStart=/opt/rag-api/venv/bin/uvicorn ${app_module} --host 127.0.0.1 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
UNIT
  systemctl daemon-reload
  systemctl enable --now rag-api
else
  echo "WARN: no release at s3://$BUCKET/$RELEASE_KEY - nginx returns 502 until you upload one and re-run: systemctl restart rag-api" >&2
fi
