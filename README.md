# Lab 3：中断与异常

邹瑛琦（2412744）、丁子昂（2411130）。

代码来自 2026-11-04 核对的课程 Lab 3 官方骨架（包内目录 `lab3_new`），选择性继承 Lab 2 的物理内存初始化与分配器实现。

## 功能

- 补全 Trap 现场恢复和汇编到 C 的调用，保持官方现场布局与保存逻辑。
- 实现时钟中断、其他中断分类、未知原因输出，以及 16/32 位断点和非法指令返回。
- 默认使用 Best-Fit；可通过 `PMM=first_fit` 选择 First-Fit。保留 Lab 3 内存管理中的中断保护与原子位操作。
- 默认每 100 次时钟中断输出一次，累计输出 10 次后关机。10 是本组实现选择，网页没有给出阈值数值；可用 `DEFS+=-DSHUTDOWN_AFTER=2` 更改。

## 构建与运行

在已有 WSL Ubuntu 环境进入 `code/`：

```bash
make
make qemu
make grade
```

调试用两个终端分别执行 `make debug`、`make gdb`。本机 `riscv64-unknown-elf-gdb` 已有包装入口，实际使用 gdb-multiarch。QEMU 使用 `-kernel` 装载；官方评分脚本只同步这一装载参数，原断言、输出判据和分值保留。

## 补充验证

以下脚本在临时副本注入测试，输出目录由调用者指定：

```bash
python3 tools/tests/run_lab3.py --mode full --out /tmp/lab3-full
python3 tools/tests/run_lab3.py --mode boot --out /tmp/lab3-boot
python3 tools/tests/debug_lab3.py --mode exceptions --out /tmp/lab3-gdb-exceptions
python3 tools/tests/debug_lab3.py --mode timer --out /tmp/lab3-gdb-timer
python3 tools/tests/run_host_regression.py --out /tmp/lab3-first-fit
python3 tools/tests/check_build_switch.py --out /tmp/lab3-build-switch
```

本轮结果：官方评分 100/100；Best-Fit/First-Fit 内核探针、默认 10 次输出关机、64/256 MiB 内存边界、配置切换，以及 4 次异常和 2 次时钟的 GDB 现场验证均通过。主机回归仅验证 First-Fit 链表行为，不能代替 RV64 内核验证。

## 报告与证据

[实验报告](report/report.md)包含两个模块的 spec、实现说明、两处正文思考、测试调试、实际问题和 OS 原理联系。[关键提示词](report/prompt.md)按实现与测试分别记录，并标明提炼稿来源。三张配图及其原始证据见 [report/evidence](report/evidence/README.md)。

从 `code/` 可执行 `sh ../report/scripts/verify.sh /tmp/lab3-reproduction` 复现十类检查。图片生成脚本使用 Pillow，需要可显示中文的字体。本年度旧 Challenge 已取消，范围说明保留在报告中。

本实验使用独立的 `lab3` 分支，代码和报告一同提交。
