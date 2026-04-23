#!/bin/sh
# Installed as /usr/bin/vocotype — runs project under /opt/vocotype-ubuntu
set -e
APP_DIR=/opt/vocotype-ubuntu
PY="$APP_DIR/.venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "VocoType: 虚拟环境未就绪。请执行: sudo apt install --reinstall vocotype-ubuntu（需联网完成 pip 安装）" >&2
  exit 1
fi
exec "$PY" "$APP_DIR/main.py" "$@"
