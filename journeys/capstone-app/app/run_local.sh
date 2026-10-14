#!/usr/bin/env bash
# Run the capstone dashboard on your own machine, against your Lakebase branch.
# You do not need to write any code; this just starts the provided app.
#
# Prerequisites: finish 00-setup, and have these set in your shell:
#   LB_PROFILE, LB_PROJECT, LB_BRANCH, LB_SCHEMA
#
# Usage:  bash run_local.sh
set -euo pipefail

cd "$(dirname "$0")/backend"

# Map the workshop's LB_* env vars to the app's LAKEBASE_* names (local dev uses your profile).
export LAKEBASE_PROFILE="${LB_PROFILE:?set LB_PROFILE (see 00-setup/auth.md)}"
export LAKEBASE_PROJECT="${LB_PROJECT:?set LB_PROJECT (see 00-setup/provision.md)}"
export LAKEBASE_BRANCH="${LB_BRANCH:-production}"
export LAKEBASE_SCHEMA="${LB_SCHEMA:-bank}"

echo "Installing backend dependencies (first run only)..."
pip install -q -r requirements.txt

echo
echo "Starting the dashboard on http://localhost:8000"
echo "  serving schema=$LAKEBASE_SCHEMA on branch=$LAKEBASE_BRANCH (project=$LAKEBASE_PROJECT)"
echo "  open http://localhost:8000 in your browser; Ctrl-C to stop."
echo
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
