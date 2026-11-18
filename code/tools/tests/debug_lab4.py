#!/usr/bin/env python3
"""Exercise the current normal ELF with a real QEMU and guest GDB."""
from pathlib import Path
import argparse
import hashlib
import json
import socket
import subprocess
import time

p = argparse.ArgumentParser()
p.add_argument('--output', required=True)
args = p.parse_args()
root = Path(__file__).resolve().parents[2]
out = Path(args.output).resolve()
out.mkdir(parents=True, exist_ok=False)
with (out/'build.log').open('w') as log:
    subprocess.run(['make','-j2'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
with socket.socket() as sock:
    sock.bind(('127.0.0.1',1234))

commands = '''set pagination off
set confirm off
set architecture riscv:rv64
file bin/kernel
target remote localhost:1234
hbreak kern_init
continue
printf "CHECKPOINT kern_init PC=%#lx\\n", $pc
delete breakpoints
hbreak proc_init
continue
finish
printf "CHECKPOINT PCB idle=%d init=%d current=%d\\n", idleproc->pid, initproc->pid, current->pid
p/x initproc->context
p/x *initproc->tf
p/x boot_pgdir_va[511]
delete breakpoints
hbreak schedule
continue
printf "CHECKPOINT schedule current=%d need=%d\\n", current->pid, current->need_resched
delete breakpoints
hbreak proc_run
continue
printf "CHECKPOINT proc_run target=%d\\n", proc->pid
delete breakpoints
hbreak switch_to
continue
printf "CHECKPOINT switch_to from=%#lx to=%#lx\\n", $a0, $a1
set $fromctx = (struct context *)$a0
set $toctx = (struct context *)$a1
p/x *$toctx
stepi 14
p/x *$fromctx
delete breakpoints
hbreak forkret
continue
printf "CHECKPOINT forkret current=%d satp=%#lx sp=%#lx\\n", current->pid, $satp, $sp
delete breakpoints
hbreak forkrets
continue
printf "CHECKPOINT forkrets frame=%#lx\\n", $a0
delete breakpoints
hbreak __trapret
continue
printf "CHECKPOINT trapret frame=%#lx\\n", $sp
delete breakpoints
hbreak kernel_thread_entry
continue
printf "CHECKPOINT entry pc=%#lx sp=%#lx s0=%#lx s1=%#lx status=%#lx\\n", $pc, $sp, $s0, $s1, $sstatus
delete breakpoints
hbreak init_main
continue
printf "CHECKPOINT init_main current=%d\\n", current->pid
x/s $a0
detach
quit
'''
(out/'commands.gdb').write_text(commands)
with (out/'qemu.log').open('w') as log:
    qemu = subprocess.Popen(['make','debug'],cwd=root,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    try:
        time.sleep(0.7)
        result = subprocess.run(['gdb-multiarch','-batch','-nx','-x',str(out/'commands.gdb')],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=25)
        (out/'gdb.log').write_text(result.stdout)
        result.check_returncode()
        time.sleep(0.2)
    finally:
        import os, signal
        if qemu.poll() is None:
            os.killpg(qemu.pid,signal.SIGTERM)
        qemu.wait(timeout=3)
expected = ['kern_init','PCB idle=0 init=1 current=0','schedule','proc_run target=1','switch_to','forkret current=1','forkrets','trapret','entry','init_main current=1']
assert all('CHECKPOINT '+value in result.stdout for value in expected), result.stdout
assert 'Cannot access memory' not in result.stdout and 'Error in sourced' not in result.stdout
summary = dict(passed=True, checkpoints=expected, elf_sha256=hashlib.sha256((root/'bin/kernel').read_bytes()).hexdigest(), qemu_command='make debug', gdb_command='gdb-multiarch -batch -nx -x commands.gdb', evidence=str(out))
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(result.stdout)
print(json.dumps(summary,indent=2))
