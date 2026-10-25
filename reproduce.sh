#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
PY=.venv/bin/python
"$PY" -m pytest -q > RESULTS/tests-all.txt 2>&1
"$PY" scripts/run_experiments.py > RESULTS/experiment_log.txt 2>&1
"$PY" scripts/make_figures.py
"$PY" scripts/write_report.py
"$PY" scripts/validate_results.py
printf 'Reproduction complete. See RESEARCH_REPORT.md and RESULTS/.\n'
