#!/bin/bash

eval "$(mamba shell hook --shell bash)"
mamba activate mrdm

project_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_dir"
exec streamlit run ui/streamlit_app.py --server.headless=true
