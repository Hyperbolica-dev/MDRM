#!/bin/bash

eval "$(mamba shell hook --shell bash)"
mamba activate mrdm

project_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_dir"
if [[ -z "${TYPESAFE_API_KEY:-}" && -f "$project_dir/.streamlit/typesafe_api_key" ]]; then
    IFS= read -r TYPESAFE_API_KEY < "$project_dir/.streamlit/typesafe_api_key"
    export TYPESAFE_API_KEY
fi
exec streamlit run ui/streamlit_app.py --server.headless=true --server.address=127.0.0.1
