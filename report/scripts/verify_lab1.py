#!/usr/bin/env python3
"""Run Lab 1 evidence collection in Ubuntu/WSL, using only the standard library.

Usage (from the repository root):
    python3 report/scripts/verify_lab1.py --tag 2026-10-09

Each QEMU process is owned by this script and stopped in a finally block.
The link-order experiment builds temporary images without changing source files.
"""

import argparse
import re
import shlex
import signal
import socket
import subprocess
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CODE = ROOT / "code"
PREFIX = "riscv64-unknown-elf-"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--tag", required=True, help="Evidence filename tag, e.g. 2026-10-09")
args = parser.parse_args()
if not re.fullmatch(r"[A-Za-z0-9_-]+", args.tag):
    parser.error("Use letters, numbers, underscores or hyphens for the tag")
EVIDENCE = ROOT / "report" / "evidence"
EVIDENCE.mkdir(exist_ok=True)


def run(argv, *, input_text=None, timeout=30):
    result = subprocess.run(argv, cwd=CODE, input=input_text, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            timeout=timeout)
    output = "$ " + shlex.join(str(arg) for arg in argv) + "\n" + result.stdout
    if result.returncode:
        raise RuntimeError(output + f"\nexit={result.returncode}")
    return output, result.stdout


def save(name, parts):
    path = EVIDENCE / f"{args.tag}-{name}.txt"
    # Make terminal NUL bytes visible so GitHub can display the log as text.
    path.write_text("\n".join(parts).replace("\x00", "\\x00"), encoding="utf-8")
    print(f"Saved {path.relative_to(ROOT)}", flush=True)


def stop(process):
    if process.poll() is None:
        process.send_signal(signal.SIGINT)
    try:
        return process.communicate(timeout=3)[0]
    except subprocess.TimeoutExpired:
        process.kill()
        return process.communicate()[0]


def qemu_output(image, seconds=3):
    argv = ["qemu-system-riscv64", "-machine", "virt", "-nographic",
            "-monitor", "none", "-bios", "default", "-kernel", str(image)]
    process = subprocess.Popen(argv, cwd=CODE, text=True, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    try:
        try:
            output = process.communicate(timeout=seconds)[0]
        except subprocess.TimeoutExpired:
            output = stop(process)
    finally:
        if process.poll() is None:
            stop(process)
    return "$ " + shlex.join(argv) + "\n" + output


build = [f"Evidence tag: {args.tag}", "Working directory: code/"]
for tool in ("make", PREFIX + "gcc", PREFIX + "ld", PREFIX + "gdb", "qemu-system-riscv64"):
    _, output = run([tool, "--version"])
    build.append(output.splitlines()[0])
for argv in (["make", "clean"], ["make"], [PREFIX + "readelf", "-h", "bin/kernel"],
             [PREFIX + "readelf", "-SW", "bin/kernel"],
             [PREFIX + "readelf", "-lW", "bin/kernel"],
             [PREFIX + "nm", "-n", "bin/kernel"],
             [PREFIX + "objdump", "-d", "--disassemble=kern_entry", "bin/kernel"]):
    output, _ = run(argv)
    build.append(output)
save("build", build)

boot = qemu_output("bin/ucore.img")
assert "(THU.CST) os is loading ..." in boot, boot
assert "0x0000000080200000" in boot and "S-mode" in boot, boot
save("qemu", [boot, "PASS: firmware hands off to 0x80200000 in S-mode; kernel prints."])

_, objects_text = run(["make", "--no-print-directory", "-s", "print-kobjs"])
objects = shlex.split(objects_text)
entry_object = "obj/kern/init/entry.o"
init_object = "obj/kern/init/init.o"
assert entry_object in objects and init_object in objects
swapped = [init_object, entry_object] + [item for item in objects if item not in (entry_object, init_object)]
layout = ["Controlled variable: order of init.o and entry.o in the link command.",
          "Compiler and other objects are identical in all cases."]

with tempfile.TemporaryDirectory(prefix="lab1-entry-review-") as temp_name:
    temp = Path(temp_name)
    _, old_entry = run(["git", "show", "89b10a3:code/kern/init/entry.S"])
    _, old_linker = run(["git", "show", "89b10a3:code/tools/kernel.ld"])
    old_script = temp / "old.ld"
    old_script.write_text(old_linker, encoding="utf-8")
    _, cflags = run(["make", "--no-print-directory", "-s", "print-cflags"])
    _, kcflags = run(["make", "--no-print-directory", "-s", "print-kcflags"])
    old_object = temp / "old-entry.o"
    run([PREFIX + "gcc", *shlex.split(cflags + kcflags), "-x", "assembler-with-cpp",
         "-c", "-o", str(old_object), "-"], input_text=old_entry)
    _, ldflags = run(["make", "--no-print-directory", "-s", "print-ldflags"])
    for name, order, script, fixed in (
        ("old-entry-first", objects, old_script, False),
        ("old-init-first", swapped, old_script, False),
        ("fixed-init-first", swapped, CODE / "tools/kernel.ld", True),
    ):
        elf = temp / (name + ".elf")
        image = temp / (name + ".img")
        actual_objects = [str(old_object) if item == entry_object and not fixed else item for item in order]
        command, _ = run([PREFIX + "ld", *shlex.split(ldflags), "-T", str(script),
                          "-o", str(elf), *actual_objects])
        run([PREFIX + "objcopy", str(elf), "--strip-all", "-O", "binary", str(image)])
        _, symbols_text = run([PREFIX + "nm", "-n", str(elf)])
        symbols = {line.split()[-1]: int(line.split()[0], 16)
                   for line in symbols_text.splitlines() if len(line.split()) == 3}
        _, header = run([PREFIX + "readelf", "-h", str(elf)])
        boot_output = qemu_output(image)
        printed = "(THU.CST) os is loading ..." in boot_output
        layout.extend([f"CASE: {name}", command,
                       next(line.strip() for line in header.splitlines() if "Entry point address" in line),
                       f"kern_entry = {symbols['kern_entry']:#x}",
                       f"kern_init  = {symbols['kern_init']:#x}",
                       f"Kernel printed: {printed}"])
        if name == "old-init-first":
            assert symbols["kern_entry"] != 0x80200000 and not printed, boot_output
        else:
            assert symbols["kern_entry"] == 0x80200000 and printed, boot_output
        if fixed:
            assert image.read_bytes() == (CODE / "bin/ucore.img").read_bytes()
            layout.append("PASS: fixed swapped-order image equals the normal image byte for byte.")
    layout.append("PASS: old layout depends on object order; dedicated entry section removes this dependence.")
save("entry-layout", layout)

_, console_disassembly = run([PREFIX + "objdump", "-d", "--disassemble=sbi_console_putchar", "bin/kernel"])
ecall_match = re.search(r"^\s*([0-9a-f]+):.*\becall\b", console_disassembly, re.M)
assert ecall_match, console_disassembly
ecall_address = int(ecall_match.group(1), 16)
with socket.socket() as listener:
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
qemu_argv = ["qemu-system-riscv64", "-machine", "virt", "-nographic", "-monitor", "none",
             "-bios", "default", "-kernel", "bin/ucore.img", "-S", "-gdb", f"tcp:127.0.0.1:{port}"]
qemu = subprocess.Popen(qemu_argv, cwd=CODE, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
commands = [
    "set pagination off", "set confirm off", "file bin/kernel", "set arch riscv:rv64",
    f"target remote 127.0.0.1:{port}",
    'python assert int(gdb.parse_and_eval("$pc")) == 0x1000',
    "info registers pc", "x/6i 0x1000", "x/2gx 0x1018", "x/3i 0x80200000",
    "break *0x80000000", "continue",
    'python assert int(gdb.parse_and_eval("$pc")) == 0x80000000',
    "info registers pc a0 a1 a2", "x/8i 0x80000000",
    "break *kern_entry", "continue", "info registers pc sp ra",
    'python assert int(gdb.parse_and_eval("$pc")) == 0x80200000',
    "p/x (unsigned long)&bootstack", "p/x (unsigned long)&bootstacktop",
    "p/d (unsigned long)&bootstacktop - (unsigned long)&bootstack",
    'python assert int(gdb.parse_and_eval("(unsigned long)&bootstacktop - (unsigned long)&bootstack")) == 8192',
    "disassemble /r kern_entry", 'python saved_ra = int(gdb.parse_and_eval("$ra"))',
    "si", "info registers pc sp ra", "si", "info registers pc sp ra",
    'python assert int(gdb.parse_and_eval("$sp")) == int(gdb.parse_and_eval("(unsigned long)&bootstacktop"))',
    "si", "info registers pc sp ra",
    'python assert int(gdb.parse_and_eval("$pc")) == int(gdb.parse_and_eval("(unsigned long)&kern_init"))',
    'python assert int(gdb.parse_and_eval("$ra")) == saved_ra',
    "p/x (unsigned long)&edata", "p/x (unsigned long)&end",
    f"break *{ecall_address:#x}", "continue", "info registers pc a0 a7",
    'python assert int(gdb.parse_and_eval("$a0")) == ord("(")',
    'python assert int(gdb.parse_and_eval("$a7")) == 1',
    "p/x $mtvec", "break *($mtvec & ~3)", "continue",
    "info registers pc mcause mepc mstatus",
    'python assert int(gdb.parse_and_eval("$mcause")) == 9',
    f'python assert int(gdb.parse_and_eval("$mepc")) == {ecall_address}',
    'python assert (int(gdb.parse_and_eval("$mstatus")) >> 11) & 3 == 1',
    'python print("PASS: reset -> OpenSBI -> kernel; stack=8192; tail preserves ra; SBI ecall causes S-to-M trap.")',
    "detach", "quit",
]
try:
    time.sleep(0.3)
    if qemu.poll() is not None:
        raise RuntimeError(qemu.communicate()[0])
    argv = [PREFIX + "gdb", "-nx", "-batch"]
    for command in commands:
        argv.extend(["-ex", command])
    gdb_command, gdb_output = run(argv, timeout=25)
    if "Python Exception" in gdb_output or "Error occurred" in gdb_output:
        raise RuntimeError("GDB assertions failed even though the batch exit code was zero:\n" + gdb_output)
    assert "PASS: reset -> OpenSBI -> kernel" in gdb_output, gdb_output
finally:
    qemu_log = stop(qemu)
save("gdb", ["$ " + shlex.join(qemu_argv), "GDB commands:", *commands, "GDB output:",
             gdb_output, "QEMU output after detach:", qemu_log])
print("PASS: build, boot, link-order regression and GDB checks completed; owned QEMU processes stopped.")
