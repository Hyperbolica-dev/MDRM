#!/usr/bin/env bash
set -euo pipefail

environment_name="${MRDM_ENVIRONMENT:-mrdm}"
if command -v mamba >/dev/null 2>&1; then
    environment_manager=mamba
    run_options=()
elif command -v conda >/dev/null 2>&1; then
    environment_manager=conda
    run_options=(--no-capture-output)
else
    printf '需要先安装 conda 或 mamba。\n' >&2
    exit 3
fi

project_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_dir"
if [[ -z "${TYPESAFE_API_KEY:-}" && -f "$project_dir/.streamlit/typesafe_api_key" ]]; then
    IFS= read -r TYPESAFE_API_KEY < "$project_dir/.streamlit/typesafe_api_key"
    export TYPESAFE_API_KEY
fi
exec "$environment_manager" run "${run_options[@]}" --name "$environment_name" python -m streamlit run ui/streamlit_app.py --server.headless=true --server.address=127.0.0.1
