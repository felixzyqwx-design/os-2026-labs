#!/usr/bin/env python3
"""Run real RV64 probes in isolated copies; never inject into student sources."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--mode', choices=['module1', 'full', 'boot', 'official', 'build'], default='full')
parser.add_argument('--expect-fail', action='store_true')
parser.add_argument('--shutdown-after', type=int)
parser.add_argument('--pmm', choices=['best_fit', 'first_fit'], default='best_fit')
parser.add_argument('--memory', type=int, default=128)
args = parser.parse_args()
args.out.mkdir(parents=True, exist_ok=True)
source = Path(__file__).resolve().parents[2]

def run(name, command, cwd, timeout):
    expired = False
    try:
        result = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        output, status = result.stdout, result.returncode
    except subprocess.TimeoutExpired as error:
        output, status, expired = error.stdout or b'', None, True
    (args.out / (name + '.txt')).write_bytes(output)
    return output.decode(errors='replace'), status, expired

with tempfile.TemporaryDirectory(prefix='lab3-probe-') as temporary:
    root = Path(temporary)
    shutil.copytree(source, root, dirs_exist_ok=True,
        ignore=shutil.ignore_patterns('obj', 'bin', '.qemu.*', '__pycache__'))
    defines = []
    if args.shutdown_after is not None:
        defines.append('-DSHUTDOWN_AFTER=' + str(args.shutdown_after))
    if args.mode in ['module1', 'full']:
        shutil.copyfile(root / 'tools/tests/probe.c', root / 'kern/init/probe.c')
        shutil.copyfile(root / 'tools/tests/probe_registers.S', root / 'kern/init/probe_registers.S')
        init = root / 'kern/init/init.c'
        text = init.read_text()
        where = text.rindex('idt_init();') + len('idt_init();')
        text = text[:where] + '\n    extern void lab3_probe(void);\n    lab3_probe();' + text[where:]
        init.write_text(text)
        if args.mode == 'module1':
            defines.append('-DPROBE_MODULE1')
            trap = root / 'kern/trap/trap.c'
            text = trap.read_text()
            start = text.index('//lab3 function2')
            end = text.index('static inline void trap_dispatch', start)
            text = text[:start] + '''// Test-only handlers isolate module one.
void interrupt_handler(struct trapframe *tf) {}
void exception_handler(struct trapframe *tf) {
    tf->epc += ((*(volatile unsigned short *)tf->epc & 3) == 3) ? 4 : 2;
}
''' + text[end:]
            trap.write_text(text)
    command = ['make', '-j2', 'PMM=' + args.pmm]
    if defines:
        command.append('DEFS+=' + ' '.join(defines))
    output, status, expired = run('build', command, root, 40)
    passed = status == 0 and not expired
    results = {'mode': args.mode, 'build_exit': status, 'build_timeout': expired}
    if passed and args.mode == 'official':
        # Keep original course conditions; only the proven local boot option differs.
        output, status, expired = run('grade', ['make', 'grade'], root, 100)
        results.update(grade_exit=status, grade_timeout=expired)
        passed = status == 0 and not expired and 'Total Score: 100/100' in output
        for log in root.glob('.qemu.*.out'):
            shutil.copyfile(log, args.out / log.name.lstrip('.'))
    elif passed and args.mode != 'build':
        output, status, expired = run('qemu', ['qemu-system-riscv64', '-machine', 'virt', '-m', str(args.memory),
            '-nographic', '-bios', 'default', '-kernel', 'bin/ucore.img', '-no-reboot'], root, 25)
        results.update(qemu_exit=status, qemu_timeout=expired)
        passed = status == 0 and not expired
        passed = passed and not re.search(r'assertion failed|kernel panic|FAIL|Python Exception|Traceback', output, re.I)
        if args.mode in ['module1', 'full']:
            passed = passed and 'LAB3_PROBE_ALL_PASS' in output
            if args.mode == 'full':
                required = ['four exception returns PASS', 'timer boundaries 99/100/101/199/200 PASS',
                    'known and unknown cause dispatch PASS', 'interrupt state, nesting and page recovery PASS']
                passed = passed and all(x in output for x in required)
                passed = passed and output.count('Breakpoint at') == 2 and output.count('Illegal instruction at') == 2
                passed = passed and len(re.findall(r'^100 ticks\r?$', output, re.M)) == 2
        else:
            count = len(re.findall(r'^100 ticks\r?$', output, re.M))
            results['tick_output_count'] = count
            passed = passed and count == (args.shutdown_after or 10)
            manager = 'default' if args.pmm == 'first_fit' else 'best_fit'
            passed = passed and ('memory management: ' + manager + '_pmm_manager') in output
            mapping = re.search(r'physical memory map: \[(0x[0-9a-f]+), (0x[0-9a-f]+)\), free: \[(0x[0-9a-f]+), (0x[0-9a-f]+)\)', output)
            symbols = subprocess.check_output(['riscv64-unknown-elf-nm', 'bin/kernel'], cwd=root).decode()
            end = int(re.search(r'^([0-9a-f]+) [A-Za-z] end$', symbols, re.M)[1], 16)
            memory_end = 0x80000000 + min(args.memory, 128) * 1024 * 1024
            # Independent ABI/layout calculation for the inherited page map.
            descriptor_base = (end + 4095) // 4096 * 4096 - 0xffffffff40000000
            free_start = (descriptor_base + ((memory_end - 0x80000000) // 4096) * 40 + 4095) // 4096 * 4096
            expected_map = [0x80000000, memory_end, free_start, memory_end]
            results['memory_map_expected'] = [hex(x) for x in expected_map]
            actual_map = [int(x, 16) for x in mapping.groups()] if mapping else []
            results['memory_map_actual'] = [hex(x) for x in actual_map]
            passed = passed and actual_map == expected_map
    results['passed'] = bool(passed)
    results['expected_failure_observed'] = bool(args.expect_fail and not passed)
    (args.out / 'summary.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(results, indent=2))
    if not passed:
        print(output[-2000:])
    raise SystemExit(0 if (not passed if args.expect_fail else passed) else 1)
