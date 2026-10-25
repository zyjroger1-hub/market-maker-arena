#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
PY=${ARENA_PYTHON:-.venv/bin/python}
"$PY" -m pytest -q > RESULTS/tests-all.txt 2>&1
"$PY" scripts/run_experiments.py > RESULTS/experiment_log.txt 2>&1
"$PY" scripts/make_figures.py
"$PY" scripts/run_mechanism_study.py > RESULTS/mechanism_experiment_log.txt 2>&1
"$PY" scripts/make_mechanism_figures.py
"$PY" scripts/write_report.py
"$PY" scripts/write_mechanism_report.py
"$PY" scripts/check_original_regression.py
"$PY" scripts/validate_results.py
"$PY" scripts/validate_mechanisms.py
printf 'Reproduction complete. See RESEARCH_REPORT.md and RESULTS/.\n'
