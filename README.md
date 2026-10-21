# OS 2026 Labs

操作系统课程 Lab 2：物理内存管理。此 `lab2` 分支只保存本次实验；Lab 1 的最终版本在独立的 [`lab1` 分支](https://github.com/felixzyqwx-design/os-2026-labs/tree/lab1)。

## 小组成员

- 邹瑛琦（2412744）
- 丁子昂（2411130）

## 目录

| 目录 | 内容 |
| --- | --- |
| [`code/`](code/) | Lab 2 完整源码与构建脚本 |
| [`report/`](report/) | [实验报告](report/report.md)、[关键提示词](report/prompt.md)、[AI 协作过程](report/ai-process.md)、[分配器复核](report/allocator-review.md)、[构建与运行核验](report/verification.md) |

构建产物 `code/bin/`、`code/obj/` 不纳入版本管理。

## 构建与运行

在已配置 RISC-V 工具链、QEMU、GNU Make 和 Git Unix 工具的 PowerShell 中进入 `code/` 后，默认构建 Best-Fit：

```powershell
mingw32-make -B
qemu-system-riscv64 -machine virt -nographic -bios default -kernel .\bin\ucore.img
```

输出 `best_fit_pmm_manager` 和 `check_alloc_page() succeeded!` 表示默认自检通过。按 `Ctrl+C` 结束 QEMU。Buddy 模式使用 `mingw32-make -B DEFS=-DPMM_BUDDY` 重新构建；详细步骤见[核验记录](report/verification.md)。

实验指导书：[课程网站](http://oslab.mobisys.top/lab2026/_book/)。
