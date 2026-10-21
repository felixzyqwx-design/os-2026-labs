# OS 2026 Labs

操作系统课程实验仓库。每次实验独立存放，源码和报告不会混在一起。

## 小组成员

- 邹瑛琦（2412744）
- 丁子昂（2411130）

## 目录

| 实验 | 源码 | 报告与说明 |
| --- | --- | --- |
| Lab 1：最小内核启动 | [`lab1/code/`](lab1/code/) | [`lab1/report/report.md`](lab1/report/report.md) |
| Lab 2：物理内存管理 | [`lab2/code/`](lab2/code/) | [`lab2/README.md`](lab2/README.md)、[`lab2/report/report.md`](lab2/report/report.md) |

`lab1` 分支保留 Lab 1 的原始最终提交；`lab2` 分支在此基础上按上述目录整理，并加入 Lab 2。两个实验的构建产物 `bin/`、`obj/` 均不纳入版本管理。

## 构建与运行

进入对应实验的 `code/` 目录后构建。Lab 1 的复测脚本在 [`lab1/report/scripts/verify_lab1.py`](lab1/report/scripts/verify_lab1.py)，Lab 2 的两种内存分配模式和核验步骤见 [`lab2/report/verification.md`](lab2/report/verification.md)。

实验指导书：[课程网站](http://oslab.mobisys.top/lab2026/_book/)。
