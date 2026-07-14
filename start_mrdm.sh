#!/bin/bash

# 初始化 mamba 环境钩子并激活环境
eval "$(mamba shell hook --shell bash)"
mamba activate mrdm

# 切换到项目目录（请将这里的路径替换为你实际的绝对路径）
cd /home/user/dev/projects/RCS/

# 以无头模式（不自动弹窗）启动 Streamlit
streamlit run ui/streamlit_app.py --server.headless=true