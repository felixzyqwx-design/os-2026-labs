# OS 2026 Labs

操作系统课程实验仓库。

## 小组成员

- 邹瑛琦（2412744）
- 丁子昂（2411130）

## 目录

- `code/`：Lab 1 完整源代码
- `report/report.md`：实验报告
- `report/prompt.md`：关键提示词及设计说明
- `report/images/`：构建、QEMU 和 GDB 测试截图
- `report/evidence/`：2026 年 10 月 9 日复测的原始命令输出
- `report/branch-review.md`：入口布局复核与链接顺序对照实验
- `report/ai-process.md`：按阶段整理的 AI 协作记录
- `report/scripts/verify_lab1.py`：构建、链接顺序和 GDB 验证脚本

当前分支对应 Lab 1：最小可执行 RISC-V 内核与启动流程。

## 运行

在已安装 RISC-V 工具链、QEMU 和 GDB 的 Ubuntu/WSL 终端中：

```bash
cd code
make
make qemu
```

QEMU 中按 `Ctrl+A`，松开后按 `X` 退出。调试时，终端 A 运行 `make debug`，终端 B 在同一目录运行 `make gdb`。

从仓库根目录执行完整复测：

```bash
python3 report/scripts/verify_lab1.py --tag retest
```

实验指导书：[课程网站](http://oslab.mobisys.top/lab2026/_book/)。
