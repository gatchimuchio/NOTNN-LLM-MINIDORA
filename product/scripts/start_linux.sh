#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
if [ ! -x .venv/bin/minidora ]; then
  python3 -m venv .venv
  . .venv/bin/activate
  python -m pip install --upgrade pip
  python -m pip install -e ".[documents]"
else
  . .venv/bin/activate
fi
[ -f config/minidora.toml ] || cp config/minidora.toml.example config/minidora.toml
exec minidora serve "$@"
