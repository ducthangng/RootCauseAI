SHELL  := /bin/bash
HEALTH ?= /health

.PHONY: up down status env shell

up: ## ~10 min, dominated by RDS. Blocks until the API answers over HTTPS.
	terraform init -input=false
	terraform apply -auto-approve
	curl -fsS --retry 60 --retry-delay 10 --retry-all-errors --max-time 10 \
	  "https://$$(terraform output -raw api_fqdn)$(HEALTH)"

down: ## Destroys EC2 + RDS + DNS record + TF-owned SSM params. VPC and hand-made params stay.
	terraform destroy -auto-approve

status: ## Everything tagged Project=rootcause that is still alive (am I still paying?)
	@aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=rootcause \
	  --query 'ResourceTagMappingList[].ResourceARN' --output text | tr '\t' '\n'

env: ## Prints SECRETS in clear text.
	@aws ssm get-parameters-by-path --path /rootcause/ --with-decryption \
	  --query 'Parameters[].[Name,Value]' --output text

shell: ## SSM session on the instance (no SSH, no key pair).
	@$$(terraform output -raw shell)
