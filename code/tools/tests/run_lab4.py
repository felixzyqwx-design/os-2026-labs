#!/usr/bin/env python3
"""Run real RV64 supplemental probes in a fresh copy, never inject into the source."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

parser = argparse.ArgumentParser()
parser.add_argument('--output', required=True)
parser.add_argument('--memory', default='128M')
parser.add_argument('--segments', action='store_true')
parser.add_argument('--fixed-stack', action='store_true')
parser.add_argument('--boundary', choices=['invalid-base','zero','overflow','no-kernel','descriptors','no-free','fragment'])
args = parser.parse_args()
source = Path(__file__).resolve().parents[2]
source_hashes = {str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in source.rglob('*') if p.is_file() and
                 not any(x in p.relative_to(source).parts for x in ('obj','bin','__pycache__'))}
out = Path(args.output).resolve()
out.mkdir(parents=True, exist_ok=False)
tree = out / 'code'
shutil.copytree(source, tree, ignore=shutil.ignore_patterns('obj','bin','__pycache__','.gdb.in','.qemu.out','.*.log'))
def edit(rel, old, new):
    path = tree / rel
    text = path.read_text()
    assert text.count(old) == 1, (rel,old)
    path.write_text(text.replace(old,new))

edit('kern/mm/pmm.c', 'struct Page *alloc_pages(size_t n)', 'struct Page *lab4_real_alloc_pages(size_t n)')
edit('kern/mm/kmalloc.c', 'kmalloc(size_t size)\n{', 'lab4_real_kmalloc(size_t size)\n{')
edit('kern/process/proc.c', 'void proc_run(struct proc_struct *proc)', 'void lab4_real_proc_run(struct proc_struct *proc)')
edit('kern/init/init.c', '    pmm_init();', '    extern void lab4_extra_pmm(void);\n    pmm_init();\n    lab4_extra_pmm();')
edit('kern/process/proc.c', '#include <proc.h>', '#include <proc.h>\nstatic void lab4_extra_create(void);\nstatic int lab4_extra_threads(void *);')
edit('kern/process/proc.c', '    set_proc_name(initproc, "init");', '    set_proc_name(initproc, "init");\n    lab4_extra_create();')
start = (tree/'kern/process/proc.c').read_text()
begin = start.index('    cprintf("this initproc')
end = start.index('\n}',begin)
(tree/'kern/process/proc.c').write_text(start[:begin]+'    return lab4_extra_threads(arg);'+start[end:]+ '\n'+('#define TEST_SEGMENTS\n' if args.segments else '')+(tree/'tools/tests/extra.inc').read_text())
edit('kern/trap/trap.c', 'void exception_handler(struct trapframe *tf) {', 'extern bool lab4_extra_fault(struct trapframe *tf);\nvoid exception_handler(struct trapframe *tf) {\n    if (lab4_extra_fault(tf)) return;')
shutil.copyfile(tree/'tools/tests/register_probe.S', tree/'kern/process/register_probe.S')
if args.fixed_stack:
    text = (tree/'kern/process/proc.c').read_text()
    text = text.replace('#include <proc.h>', '#include <proc.h>\nvoid lab4_fixed_switch(struct context *, struct context *, uintptr_t);\nstatic int lab4_fixed_experiment(void *);', 1)
    text = text.replace('return lab4_extra_threads(arg);', 'return lab4_fixed_experiment(arg);', 1)
    old = '            write_csr(satp, ((uintptr_t)SATP_MODE_SV39 << 60) |\n                            (proc->pgdir >> RISCV_PGSHIFT));\n            flush_tlb();\n            switch_to(&prev->context, &proc->context);'
    assert text.count(old) == 1
    text = text.replace(old, '            lab4_fixed_switch(&prev->context, &proc->context,\n                ((uintptr_t)SATP_MODE_SV39 << 60) | (proc->pgdir >> RISCV_PGSHIFT));')
    (tree/'kern/process/proc.c').write_text(text+'\n'+(tree/'tools/tests/fixed_stack.inc').read_text())
    shutil.copyfile(tree/'tools/tests/fixed_switch.S', tree/'kern/process/fixed_switch.S')
expected = '[Extra ALL] PASS'
expected_panic = False
if args.boundary:
    case = args.boundary
    injected = {
        'invalid-base': 'mem_base += PGSIZE;',
        'zero': 'mem_size = 0;',
        'overflow': 'mem_size = (uint64_t)-1;',
        'no-kernel': 'mem_size = 0x100000;',
        'descriptors': 'mem_size = (uintptr_t)end - PHYSICAL_MEMORY_OFFSET - DRAM_BASE + PGSIZE;',
    }
    if case in ('no-free','fragment'):
        extra = f'''uintptr_t test_end = ROUNDUP((uintptr_t)end - PHYSICAL_MEMORY_OFFSET, PGSIZE) + 16 * PGSIZE;
        for (int i = 0; i < 16; ++i) {{
            struct Page *first = (struct Page *)ROUNDUP((uintptr_t)end, PGSIZE);
            uintptr_t descriptor_end = (uintptr_t)(first + PPN(test_end) - nbase) - PHYSICAL_MEMORY_OFFSET;
            test_end = {'descriptor_end + 7' if case == 'fragment' else 'ROUNDUP(descriptor_end, PGSIZE)'};
        }}
        mem_size = test_end - DRAM_BASE;'''
        expected = '[Boundary no free complete page] PASS'
        edit('kern/mm/pmm.c', '    page_init();', '    page_init();\n    assert(nr_free_pages() == 0);\n    cprintf("[Boundary no free complete page] PASS\\n");\n    sbi_shutdown();')
    else:
        extra = injected[case]
        expected_panic = True
        expected = 'invalid physical memory reported by DTB' if case in ('invalid-base','zero','overflow') else 'no usable kernel memory' if case == 'no-kernel' else 'kernel and Page descriptors exceed physical memory'
    edit('kern/mm/pmm.c','uint64_t mem_base = get_memory_base(), mem_size = get_memory_size();',
         'uint64_t mem_base = get_memory_base(), mem_size = get_memory_size();\n    /* Synthetic boundary input in the test copy only. */\n    '+extra)
begin = time.monotonic()
with (out/'build.log').open('w') as log:
    result = subprocess.run(['make','-j2'],cwd=tree,stdout=log,stderr=subprocess.STDOUT,timeout=60)
if result.returncode:
    print((out/'build.log').read_text()[-5000:])
    raise SystemExit(result.returncode)
command = ['qemu-system-riscv64','-machine','virt','-m',args.memory,'-nographic','-bios','default','-kernel','bin/ucore.img']
try:
    result = subprocess.run(command,cwd=tree,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=15)
    output = result.stdout
except subprocess.TimeoutExpired as error:
    (out/'run.log').write_bytes(error.stdout or b'')
    raise
(out/'run.log').write_text(output)
passed = result.returncode == 0 and expected in output and (expected_panic == ('kernel panic' in output))
summary = dict(passed=passed, exit=result.returncode, seconds=round(time.monotonic()-begin,3), command=command,
               synthetic_boundary=args.boundary, expected=expected,
               source_sha256=source_hashes,
               checks=[x for x in output.splitlines() if x.startswith(('[Extra','[Fixed stack'))])
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(output[-6000:])
print(json.dumps({k:v for k,v in summary.items() if k!='source_sha256'},indent=2))
raise SystemExit(0 if passed else 1)
