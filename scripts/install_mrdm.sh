#!/usr/bin/env bash
set -euo pipefail

repository_url="${MRDM_REPOSITORY_URL:-https://github.com/Hyperbolica-dev/MDRM.git}"
project_dir="${MRDM_DIR:-$HOME/MDRM}"
environment_name="${MRDM_ENVIRONMENT:-mrdm}"

command -v git >/dev/null 2>&1 || { printf '需要先安装 Git。\n' >&2; exit 3; }
if command -v mamba >/dev/null 2>&1; then
    environment_manager=mamba
elif command -v conda >/dev/null 2>&1; then
    environment_manager=conda
else
    printf '需要先安装 conda 或 mamba。\n' >&2
    exit 3
fi

if [[ -e "$project_dir" && ! -d "$project_dir/.git" ]]; then
    printf '目标目录已存在但不是 MDRM Git 仓库：%s\n' "$project_dir" >&2
    exit 2
fi

if [[ -d "$project_dir/.git" ]]; then
    current_origin="$(git -C "$project_dir" remote get-url origin)"
    if [[ "${current_origin%.git}" != "${repository_url%.git}" ]]; then
        printf '目标仓库来源不同，停止更新：%s\n' "$project_dir" >&2
        exit 2
    fi
    if [[ -n "$(git -C "$project_dir" status --porcelain)" ]]; then
        printf '存在未提交改动，请先自行整理，再更新。\n' >&2
        exit 2
    fi
    if [[ "$(git -C "$project_dir" branch --show-current)" != main ]]; then
        printf '当前不是 main 分支，停止自动更新。\n' >&2
        exit 2
    fi
    git -C "$project_dir" pull --ff-only origin main
else
    git clone --branch main "$repository_url" "$project_dir"
fi

environment_list="$("$environment_manager" env list)"
if awk -v name="$environment_name" '$1 == name {found=1} END {exit !found}' <<< "$environment_list"; then
    "$environment_manager" env update --name "$environment_name" --file "$project_dir/environment.yaml"
else
    "$environment_manager" env create --name "$environment_name" --file "$project_dir/environment.yaml" --yes
fi

cd "$project_dir"
export MRDM_ENVIRONMENT="$environment_name"
exec bash scripts/start_mrdm.sh
