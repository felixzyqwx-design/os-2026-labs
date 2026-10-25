#!/usr/bin/env python3
"""Build and boot Lab 2 with bounded, evidence-based checks (run in Linux/WSL)."""
import argparse
import json
import os
from pathlib import Path
import re
import signal
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--baseline', action='store_true', help='record the original source failures')
args = parser.parse_args()
repo = Path(__file__).resolve().parents[2]
code = repo / 'code'
args.out.mkdir(parents=True, exist_ok=True)
results = []

def run(name, command, expected=(), timeout=60, boot=False):
    process = subprocess.Popen(command, cwd=code, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, start_new_session=True)
    expired = False
    try:
        data, _ = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        expired = True
        os.killpg(process.pid, signal.SIGTERM)
        data, _ = process.communicate(timeout=5)
    finally:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    text = data.decode(errors='replace')
    (args.out / (name + '.txt')).write_bytes(data)
    error = bool(re.search(r'kernel panic|assertion failed|\bFAIL\b|\bWRONG\b|\berror:', text, re.I))
    passed = (not error and all(marker in text for marker in expected)
              and (boot or (process.returncode == 0 and not expired)))
    result = dict(name=name, command=command, exit=process.returncode,
                  timed_out=expired, passed=passed, expected=list(expected))
    results.append(result)
    print(json.dumps(result), flush=True)
    return passed

def boot(name, manager, memory=128, extra=()):
    return run(name, ['qemu-system-riscv64', '-machine', 'virt', '-m', str(memory),
        '-nographic', '-bios', 'default', '-kernel', 'bin/ucore.img'],
        ('memory management: ' + manager + '_pmm_manager',
         'check_alloc_page() succeeded!') + tuple(extra), timeout=3, boot=True)

run('build-default', ['make', '-B', '-j2'])
boot('boot-default', 'best_fit')
if not args.baseline:
    for memory in (64, 256):
        boot('boot-default-' + str(memory), 'best_fit', memory)
run('build-buddy', ['make', '-j2', 'DEFS=-DPMM_BUDDY'])
run('symbols-buddy', ['riscv64-unknown-elf-nm', 'bin/kernel'], ('buddy_pmm_manager',))
boot('boot-buddy', 'buddy', extra=('buddy checks:',))
if not args.baseline:
    run('build-first-fit', ['make', '-j2', 'PMM=first_fit'])
    boot('boot-first-fit', 'default')
run('build-default-again', ['make', '-j2'])
run('symbols-default-again', ['riscv64-unknown-elf-nm', 'bin/kernel'], ('best_fit_pmm_manager',))
boot('boot-default-again', 'best_fit')
run('grade', ['make', 'grade'], ('-check page init:', '-check best fit:',
    'Total Score: 20/20'))
grade_output = code / '.qemu.out'
if grade_output.exists():
    text = grade_output.read_text(errors='replace')
    (args.out / 'grade-kernel.txt').write_text(text)
    markers = ('[Test 1] Page Init: PASS', '[Test 2] Best-Fit: PASS')
    results.append(dict(name='grade-kernel-markers', passed=all(
        marker in text for marker in markers) and not re.search(
        r'kernel panic|assertion failed|\bFAIL\b', text, re.I)))
else:
    results.append(dict(name='grade-kernel-markers', passed=False))
(args.out / 'summary.json').write_text(json.dumps(results, indent=2) + '\n')
failed = [result['name'] for result in results if not result['passed']]
print('FAILED: ' + ', '.join(failed) if failed else 'ALL CHECKS PASSED')
raise SystemExit(bool(failed))
