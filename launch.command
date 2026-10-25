#!/bin/zsh
# Double-click on macOS or run ./launch.command from Terminal.
cd -- "$(dirname -- "$0")" || exit 1
if [[ ! -x .venv/bin/python ]]; then
  echo 'Create a Python 3.12 virtual environment and install requirements first; see README.md.'
  exit 1
fi
exec .venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
