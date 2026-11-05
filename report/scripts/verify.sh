#!/bin/sh
# Run from any working directory; all probe injection happens in temporary copies.
set -eu
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
code_dir=$(CDPATH= cd -- "$script_dir/../../code" && pwd)
out=${1:-/tmp/lab3-reproduction}
mkdir -p "$out"
out=$(CDPATH= cd -- "$out" && pwd)
cd "$code_dir"
python3 tools/tests/run_lab3.py --mode full --out "$out/full-best-fit"
python3 tools/tests/run_lab3.py --mode full --pmm first_fit --out "$out/full-first-fit"
python3 tools/tests/run_lab3.py --mode boot --out "$out/boot-default"
python3 tools/tests/run_lab3.py --mode boot --memory 64 --shutdown-after 2 --out "$out/boot-64"
python3 tools/tests/run_lab3.py --mode boot --memory 256 --shutdown-after 2 --out "$out/boot-256"
python3 tools/tests/run_host_regression.py --out "$out/first-fit-tail"
python3 tools/tests/check_build_switch.py --out "$out/build-switch"
python3 tools/tests/run_lab3.py --mode official --out "$out/official-grade"
python3 tools/tests/debug_lab3.py --mode exceptions --out "$out/gdb-exceptions"
python3 tools/tests/debug_lab3.py --mode timer --out "$out/gdb-timer"
printf 'Lab 3 reproduction passed. Logs: %s\n' "$out"
