#!/bin/sh
set -eu
dest="${CODEX_HOME:-$HOME/.codex}/skills/teams-ai-assistant"
src=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)' || { echo '需要 Python 3.9 或更高版本' >&2; exit 1; }
if [ -e "$dest" ]; then
  echo "目标已存在：$dest；请先检查本地修改。" >&2
  exit 1
fi
mkdir -p "$dest/scripts"
cp "$src/SKILL.md" "$src/README.md" "$src/requirements.txt" "$dest/"
cp "$src/scripts/teams.py" "$dest/scripts/"
python3 -m venv "$dest/.venv"
"$dest/.venv/bin/python" -m pip install -r "$dest/requirements.txt"
printf '技能已安装到 %s。请重启 Codex，再使用 Teams AI Assistant 登录。\n' "$dest"
printf '立即登录：%s/.venv/bin/python %s/scripts/teams.py login\n' "$dest" "$dest"
