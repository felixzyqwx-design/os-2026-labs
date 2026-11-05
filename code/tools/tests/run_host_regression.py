#!/usr/bin/env python3
"""Native model test of the actual First-Fit linked-list implementation."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--compare-original', type=Path)
args = parser.parse_args()
args.out.mkdir(parents=True, exist_ok=True)
tests = Path(__file__).resolve().parent
rows = []
with tempfile.TemporaryDirectory(prefix='lab3-first-fit-') as directory:
    variants = [('current', None)]
    if args.compare_original:
        variants.insert(0, ('original', args.compare_original.resolve()))
    for name, original in variants:
        binary = str(Path(directory) / name)
        command = ['gcc', '-std=gnu99', '-g', '-O1', '-Wall', '-Wextra', '-Werror',
            '-Wno-sign-compare', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
            '-I' + str(tests / 'include'), '-I' + str(tests.parents[1] / 'kern/mm'),
            str(tests / 'first_fit_tail.c'), '-o', binary]
        if original:
            command.append('-DFIRSTFIT_SOURCE="' + str(original) + '"')
        built = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20)
        (args.out / (name + '-build.txt')).write_bytes(built.stdout)
        assert built.returncode == 0, built.stdout.decode(errors='replace')
        run = subprocess.run([binary], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=5)
        (args.out / (name + '.txt')).write_bytes(run.stdout)
        if original:
            passed = run.returncode != 0 and b'pages[3].page_link.prev' in run.stdout
        else:
            passed = run.returncode == 0 and b'FIRST FIT TAIL PASS' in run.stdout
        rows.append(dict(variant=name, exit=run.returncode, expected_failure=bool(original), passed=passed))
        assert passed, run.stdout.decode(errors='replace')
(args.out / 'summary.json').write_text(json.dumps(rows, indent=2) + '\n')
print(json.dumps(rows, indent=2))
