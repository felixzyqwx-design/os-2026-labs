#!/usr/bin/env python3
"""Test page_init boundaries using DTB getter overrides in disposable source copies.

The real DTB parser and submission sources are left unchanged. QEMU output
before pmm_init still describes the actual machine, while the getters deliberately
return the selected test case. Run under Linux/WSL.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
args.out.mkdir(parents=True, exist_ok=True)
code = Path(__file__).resolve().parents[2] / 'code'
records = []

def boot(directory):
    process = subprocess.Popen(['qemu-system-riscv64', '-machine', 'virt',
        '-nographic', '-bios', 'default', '-kernel', 'bin/ucore.img'],
        cwd=directory, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        start_new_session=True)
    try:
        data, _ = process.communicate(timeout=2)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGTERM)
        data, _ = process.communicate(timeout=5)
    return data.decode(errors='replace')

with tempfile.TemporaryDirectory(prefix='lab2-page-init-') as temp:
    directory = Path(temp)
    shutil.copytree(code, directory, dirs_exist_ok=True,
        ignore=shutil.ignore_patterns('obj', 'bin', '.qemu.out', '.gdb.in'))
    dtb = directory / 'kern/driver/dtb.c'
    original_dtb = dtb.read_text()
    pmm = directory / 'kern/mm/pmm.c'
    original_pmm = pmm.read_text()
    cases = [
        ('zero-size', 0x80000000, 0, 'invalid physical memory reported by DTB'),
        ('wrong-base', 0x80001000, 0x8000000, 'invalid physical memory reported by DTB'),
        ('overflow', 0x80000000, 0xffffffffffffffff, 'invalid physical memory reported by DTB'),
        ('below-kernel', 0x80000000, 0x100000, 'no usable kernel memory'),
        ('no-descriptor-room', 0x80000000, 0x201000,
         'kernel and Page descriptors exceed physical memory'),
        ('partial-tail', 0x80000000, 0x4000123, 'check_alloc_page() succeeded!'),
        ('no-full-free-page', 0x80000000, 0, 'satp physical address:'),
    ]
    # First obtain the linked descriptor-start address for the zero-free-page
    # case. Later getter-only changes do not alter BSS layout.
    probe = subprocess.run(['make', '-j2'], cwd=directory,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if probe.returncode:
        raise SystemExit(probe.stdout.decode(errors='replace'))
    symbols = subprocess.check_output(['riscv64-unknown-elf-nm', 'bin/kernel'],
                                      cwd=directory, text=True)
    end_va = int(re.search(r'^([0-9a-f]+)\s+\w\s+end$', symbols, re.M)[1], 16)
    descriptor_start = ((end_va - 0xffffffff40000000 + 4095) // 4096) * 4096
    layout = subprocess.check_output(['gdb-multiarch', '-q', '-nx', '-batch',
        '-ex', 'file bin/kernel', '-ex', 'p sizeof(struct Page)'], cwd=directory,
        text=True)
    descriptor_size = int(re.search(r'=\s*(\d+)', layout)[1])
    count = ((descriptor_start - 0x80000000 + 4096 - descriptor_size - 1)
             // (4096 - descriptor_size))
    for name, base, size, expected in cases:
        zero_free = name == 'no-full-free-page'
        if zero_free:
            size = count * 4096
        body = re.sub(r'uint64_t get_memory_base\(void\)\s*\{.*?\}',
            'uint64_t get_memory_base(void) { return 0x%xULL; }' % base,
            original_dtb, flags=re.S)
        body = re.sub(r'uint64_t get_memory_size\(void\)\s*\{.*?\}',
            'uint64_t get_memory_size(void) { return 0x%xULL; }' % size,
            body, flags=re.S)
        dtb.write_text(body)
        # pmm_init normally tests allocations immediately. Skip only that call
        # in the zero-free-page fixture, because allocating there must fail.
        pmm.write_text(original_pmm.replace('    check_alloc_page();',
            '    assert(nr_free_pages() == 0);') if zero_free else original_pmm)
        build = subprocess.run(['make', '-j2'], cwd=directory,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (args.out / (name + '-build.txt')).write_bytes(build.stdout)
        if build.returncode:
            raise SystemExit(build.stdout.decode(errors='replace'))
        text = boot(directory)
        (args.out / (name + '.txt')).write_text(text)
        passed = expected in text
        if name == 'partial-tail':
            free_range = re.search(r'free: \[0x([0-9a-f]+), 0x([0-9a-f]+)\)', text)
            passed &= (bool(free_range) and int(free_range[2], 16) == 0x84000000)
        if zero_free:
            free_range = re.search(r'free: \[0x([0-9a-f]+), 0x([0-9a-f]+)\)', text)
            passed &= bool(free_range) and free_range[1] == free_range[2]
        if name in ('partial-tail', 'no-full-free-page'):
            passed &= 'kernel panic' not in text
        record = dict(name=name, getter_base=hex(base), getter_size=hex(size),
                      expected=expected, passed=bool(passed))
        records.append(record)
        print(json.dumps(record), flush=True)
(args.out / 'summary.json').write_text(json.dumps(records, indent=2) + '\n')
raise SystemExit(any(not row['passed'] for row in records))
