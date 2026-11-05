#!/usr/bin/env python3
"""Check effective-option rebuilds in one directory without make clean."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
args.out.mkdir(parents=True, exist_ok=True)
source = Path(__file__).resolve().parents[2]
rows = []
with tempfile.TemporaryDirectory(prefix='lab3-switch-') as directory:
    root = Path(directory)
    shutil.copytree(source, root, dirs_exist_ok=True,
        ignore=shutil.ignore_patterns('obj', 'bin', '.qemu.*', '__pycache__'))
    for case, pmm in enumerate(['best_fit', 'first_fit', 'best_fit']):
        built = subprocess.run(['make', '-j2', 'PMM=' + pmm, 'DEFS+=-DSHUTDOWN_AFTER=2'],
            cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=40)
        (args.out / (str(case) + '-build.txt')).write_bytes(built.stdout)
        assert built.returncode == 0
        run = subprocess.run(['qemu-system-riscv64', '-machine', 'virt', '-nographic',
            '-bios', 'default', '-kernel', 'bin/ucore.img'], cwd=root,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=10)
        (args.out / (str(case) + '-qemu.txt')).write_bytes(run.stdout)
        expected = 'default' if pmm == 'first_fit' else 'best_fit'
        passed = run.returncode == 0 and ('memory management: ' + expected + '_pmm_manager').encode() in run.stdout
        passed = passed and run.stdout.count(b'100 ticks') == 2
        rows.append(dict(case=case, pmm=pmm, build_exit=built.returncode, qemu_exit=run.returncode, passed=passed))
        assert passed
    unchanged = subprocess.run(['make', '-j2', 'PMM=best_fit', 'DEFS+=-DSHUTDOWN_AFTER=2'],
        cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20)
    (args.out / 'unchanged-build.txt').write_bytes(unchanged.stdout)
    assert unchanged.returncode == 0 and b'+ cc' not in unchanged.stdout
(args.out / 'summary.json').write_text(json.dumps(rows, indent=2) + '\n')
print(json.dumps(rows, indent=2))
