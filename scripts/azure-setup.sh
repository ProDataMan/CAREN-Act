#!/usr/bin/env bash
# One-time setup steps that grant permissions. Review before running.
# Already done: database CAREN_Act on postgresdata (free serverless), resource group CARENAct,
# Container Apps environment caren-act-env, container app caren-act-server (managed identity), env vars.
set -euo pipefail

APP_ID=$(az ad app list --display-name ohana-belltown-github-deploy --query "[0].appId" -o tsv)  # existing "ohana-belltown-github-deploy" app registration (also used by No_Limit_Auto_Salon)
SUB=$(az account show --query id -o tsv)
TENANT=$(az account show --query tenantId -o tsv)
REPO=ProDataMan/CAREN-Act

# 1. Let GitHub Actions on CAREN-Act main sign in to Azure (OIDC, no stored secrets)
az ad app federated-credential create --id "$APP_ID" --parameters '{
  "name": "caren-act-main",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:ProDataMan/CAREN-Act:ref:refs/heads/main",
  "audiences": ["api://AzureADTokenExchange"]
}'

# GitHub now sends subjects with immutable owner/repo IDs (repo:Owner@<id>/Repo@<id>:...).
# Add that form too; the IDs come from the GitHub API.
OWNER_ID=$(gh api "repos/$REPO" --jq .owner.id)
REPO_ID=$(gh api "repos/$REPO" --jq .id)
az ad app federated-credential create --id "$APP_ID" --parameters "{
  \"name\": \"caren-act-main-withid\",
  \"issuer\": \"https://token.actions.githubusercontent.com\",
  \"subject\": \"repo:ProDataMan@${OWNER_ID}/CAREN-Act@${REPO_ID}:ref:refs/heads/main\",
  \"audiences\": [\"api://AzureADTokenExchange\"]
}"

# 2. Allow that identity to update resources in the CARENAct resource group only
az role assignment create --assignee "$APP_ID" --role Contributor \
  --scope "/subscriptions/$SUB/resourceGroups/CARENAct"

# 3. Tell the workflow which identity to use (same secret names as Ohana_Belltown)
gh secret set AZURE_CLIENT_ID       -R "$REPO" -b "$APP_ID"
gh secret set AZURE_TENANT_ID       -R "$REPO" -b "$TENANT"
gh secret set AZURE_SUBSCRIPTION_ID -R "$REPO" -b "$SUB"

# 4. Database access for the app: run server/sql/grant-app-identity.sql in the Azure Portal
#    query editor for CAREN_Act (sign in with Microsoft Entra).

# 5. Allow pushing workflow files and container images, then push:
#    gh auth refresh -s workflow,write:packages && git push
#
# 6. After the first workflow run, make the image public so Azure can pull it (same as Ohana's):
#    https://github.com/users/ProDataMan/packages/container/caren-act-server/settings  ->  Change visibility -> Public
