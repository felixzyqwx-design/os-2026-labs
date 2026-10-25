#!/usr/bin/env python3
"""Run the real allocator sources under native GCC ASan/UBSan in Linux/WSL."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
args.out.mkdir(parents=True, exist_ok=True)
tests = Path(__file__).resolve().parent
code = tests.parents[1]
with tempfile.TemporaryDirectory(prefix='lab2-host-') as temp:
    for kind in ('best_fit', 'buddy'):
        binary = str(Path(temp) / kind)
        command = ['gcc', '-std=gnu99', '-g', '-O1', '-Wall', '-Wextra',
                   '-Werror', '-Wno-unused-variable', '-Wno-unused-but-set-variable',
                   '-Wno-sign-compare',  # The unmodified course checks use int totals.
                   '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                   '-I' + str(tests / 'include'), '-I' + str(code / 'kern/mm'),
                   str(tests / 'allocator_host.c'), '-o', binary]
        if kind == 'buddy':
            command.append('-DTEST_BUDDY')
        build = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (args.out / ('host-' + kind + '-build.txt')).write_bytes(build.stdout)
        if build.returncode:
            raise SystemExit(build.stdout.decode(errors='replace'))
        run = subprocess.run([binary], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             timeout=60)
        (args.out / ('host-' + kind + '.txt')).write_bytes(run.stdout)
        print(run.stdout.decode(errors='replace'), flush=True)
        if run.returncode or b'HOST PASS' not in run.stdout:
            raise SystemExit('Host check failed: ' + kind)
