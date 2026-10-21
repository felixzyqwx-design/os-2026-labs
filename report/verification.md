# Lab 2 构建与运行核验记录

记录日期：2026 年 10 月 21 日。本文摘录本地终端实际观察到的关键输出，**不是未经剪裁的终端原始日志**；完整命令可按下文重新执行。技术含义见 [实验报告](report.md)，测试边界见 [分配器复核](allocator-review.md)。

## 环境

| 工具 | 本机版本 |
| --- | --- |
| RISC-V GCC | SiFive GCC-Metal 10.2.0-2020.12.8，GCC 10.2.0 |
| QEMU | SiFive QEMU 5.1.0-2020.08.1 |
| GNU Make | 4.2.1（Windows 命令名 `mingw32-make`） |
| 宿主环境 | Windows PowerShell；构建时还需 Git 提供的 Unix 工具 |

版本由上述工具的 `--version` 输出核对。本次核验最初在独立工作目录 `D:\操作系统\lab2\lab2_new` 进行；当前 `lab2` 分支的源码位于根目录 `code/`。构建产物 `bin/kernel` 为带符号 ELF，`bin/ucore.img` 为启动用裸镜像；产物不等于源码提交。

## 默认 Best-Fit

在配置好工具链、QEMU、Make 和 Git Unix 工具的 PowerShell 中：

```powershell
Set-Location 'D:\操作系统\os-2026-labs\code'
mingw32-make -B
qemu-system-riscv64 -machine virt -nographic -bios default -kernel .\bin\ucore.img
```

本次完整编译生成了 `bin/kernel` 和 `bin/ucore.img`。最后一次恢复默认模式后，QEMU 的关键输出为：

```text
Physical Memory from DTB:
  Base: 0x0000000080000000
  Size: 0x0000000008000000 (128 MB)
memory management: best_fit_pmm_manager
physical memory map: [0x0000000080000000, 0x0000000088000000], free: [0x0000000080347000, 0x0000000088000000]
check_alloc_page() succeeded!
```

`free` 起点是本次编译的值，不应作为未来版本的固定断言。内核打印后进入预期的无限循环，在该 PowerShell 交互环境下按 `Ctrl+C` 结束 QEMU。

## Buddy 模式

只改变编译参数不一定使旧目标文件重编译，所以使用 `-B`：

```powershell
mingw32-make -B DEFS=-DPMM_BUDDY
qemu-system-riscv64 -machine virt -nographic -bios default -kernel .\bin\ucore.img
```

重新编译后 QEMU 的关键输出为：

```text
memory management: buddy_pmm_manager
buddy checks: split, round-up, free and counts passed
check_alloc_page() succeeded!
```

Buddy 自检包括 1/3/5 页请求、向上取整、释放计数、无效请求以及“没有仍可合并的同阶空闲伙伴”。验证后再次运行 `mingw32-make -B`，把当前目录的生成镜像恢复为默认 Best-Fit，并在 QEMU 中确认默认模式输出。

## 入库后路径复测

在本分支的 `code/` 目录重新执行完整编译和 QEMU 启动。默认模式出现 `memory management: best_fit_pmm_manager` 与 `check_alloc_page() succeeded!`；Buddy 模式出现 `memory management: buddy_pmm_manager`、`buddy checks: split, round-up, free and counts passed` 与 `check_alloc_page() succeeded!`。最后重新编译默认模式。运行中的 QEMU 用 `Ctrl+C` 结束。

## 课程注入测试与未覆盖部分

在新增 Buddy 之前，曾在**独立临时副本**用 `tools/inject.py` 注入课程测试，观察到：

```text
[Test 1] Page Init: PASS
[Test 2] Best-Fit: PASS
```

该注入测试只覆盖 Page Init 与默认 Best-Fit，不包含 Buddy。新增 Buddy 后已重新运行默认 Best-Fit 自检及 Buddy 自检；Buddy 检查是本项目新增的测试。选做 SLUB 与 QEMU 源码级页表查询不在本次运行记录中。

