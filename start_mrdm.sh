#!/bin/bash

# 初始化 mamba 环境钩子并激活环境
eval "$(mamba shell hook --shell bash)"
mamba activate mrdm

cd "$(dirname "$0")"

# 以无头模式（不自动弹窗）启动 Streamlit
streamlit run ui/streamlit_app.py --server.headless=true