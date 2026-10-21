# Lab 2：物理内存管理

本目录包含 Lab 2 的完整源码及报告。默认构建运行 Best-Fit；定义 `PMM_BUDDY` 后可运行 Buddy System。

## 目录

- `code/`：实验源码与构建脚本（`kern/`、`libs/`、`tools/`、`Makefile`）。
- [report/report.md](report/report.md)：实验目的、必做练习、结果与 OS 原理联系。
- [report/prompt.md](report/prompt.md)：各练习的任务规范、关键提示词及设计说明。
- [report/ai-process.md](report/ai-process.md)：AI 辅助分析、测试与修正记录。
- [report/allocator-review.md](report/allocator-review.md)：First-Fit、Best-Fit、Buddy 的设计及测试复核。
- [report/verification.md](report/verification.md)：本机版本、复现命令、实际输出与未覆盖范围。

`lab2.md` 是指向完整报告的简短入口。

## 运行

在已配置 RISC-V 工具链、QEMU、GNU Make 和 Git Unix 工具的 PowerShell 中进入 `lab2/code/`：

```powershell
mingw32-make -B
qemu-system-riscv64 -machine virt -nographic -bios default -kernel .\bin\ucore.img
```

观察到 `best_fit_pmm_manager` 与 `check_alloc_page() succeeded!` 即说明默认自检到达成功位置。按 `Ctrl+C` 结束 QEMU。Buddy 模式先运行 `mingw32-make -B DEFS=-DPMM_BUDDY`，启动方式相同；运行后用 `mingw32-make -B` 恢复默认镜像。详见 [核验记录](report/verification.md)。

选做的 SLUB 和硬件内存探测 Challenge 未纳入本次实现。
