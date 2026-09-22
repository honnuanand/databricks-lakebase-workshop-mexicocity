#!/usr/bin/env bash
# Deploy the capstone dashboard to Databricks Apps.
# You do not write any code; this packages the provided app and pushes it.
#
# Prerequisites:
#   - You are logged in: databricks auth login --profile "$LB_PROFILE"
#   - You edited app.yaml's LAKEBASE_* values for your setup.
#   - You ran the SP grant step (see the journey's Step 1) so the app can reach Lakebase.
#
# Usage:  bash deploy.sh [app-name]   (default app name: capstone-dashboard)
set -euo pipefail

APP_NAME="${1:-capstone-dashboard}"
PROFILE="${LB_PROFILE:?set LB_PROFILE (see 00-setup/auth.md)}"
cd "$(dirname "$0")"

echo "Deploying '$APP_NAME' to Databricks Apps (profile: $PROFILE)..."
echo

# The Databricks CLI syncs this folder to the app's workspace source and starts it.
# The app runs the command in app.yaml (uvicorn main:app), reading LAKEBASE_* from app.yaml.
databricks apps deploy "$APP_NAME" \
  --source-code-path "$(pwd)" \
  --profile "$PROFILE"

echo
echo "Deployed. Find '$APP_NAME' under Apps in your workspace."
echo "If the app cannot reach Lakebase (permission denied), run the SP grant step again"
echo "with the app's Service Principal, then re-run this deploy. See the journey Step 6."
