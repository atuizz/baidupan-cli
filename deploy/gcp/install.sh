#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/home/saonianatui/baidupan-cli}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
mkdir -p "$APP_DIR"

rsync -av --delete ./ "$APP_DIR"/ --exclude '.git' --exclude '.venv' --exclude '__pycache__'

cd "$APP_DIR"
$PYTHON_BIN -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .[dev]

echo "installed into $APP_DIR"
echo "next:"
echo "1. export BDPAN_BIN=/home/saonianatui/.local/bin/bdpan"
echo "2. sudo copy deploy/gcp/baidupan-cli.service to /etc/systemd/system/"
echo "3. sudo systemctl enable --now baidupan-cli"
