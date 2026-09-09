#!/bin/bash
set -e
cd -- "$(dirname -- "$0")"
python3 -m venv .mac-build-env
.mac-build-env/bin/python -m pip install pyinstaller==6.22.2
.mac-build-env/bin/python build_mac.py
