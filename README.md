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

输出 `best_fit_pmm_manager` 和 `check_alloc_page() succeeded!` 表示默认自检通过。按 `Ctrl+C` 结束 QEMU。Buddy 模式可用 `mingw32-make PMM=buddy` 构建，`mingw32-make` 恢复 Best-Fit；构建配置变化会自动使目标文件重新编译。原有 `DEFS=-DPMM_BUDDY` 方式仍可使用。初次 Windows 运行记录见[核验记录](report/verification.md)。

## WSL / Linux 复测

在仓库根目录进入 `code/` 后：

```sh
make
make qemu
make PMM=buddy
make qemu PMM=buddy
make PMM=first_fit
make qemu PMM=first_fit
make
make grade
```

每个 QEMU 会持续运行，先按 `Ctrl+A`，松开后按 `X` 退出，再执行下一条命令。评分使用独立临时副本，保留原有测试；评分原始内核输出保存在 `code/.qemu.out`。默认 Best-Fit 的预期评分为 `Total Score: 20/20`，该分数不覆盖 Buddy 或 QEMU 源码调试任务。

从仓库根目录运行自动复测，输出目录自行指定：

```sh
python3 report/scripts/verify_lab2.py --out /tmp/lab2-checks
python3 code/tools/tests/run_host.py --out /tmp/lab2-host-checks
python3 report/scripts/check_page_init.py --out /tmp/lab2-page-checks
python3 report/scripts/check_mapping.py --out /tmp/lab2-mapping-checks
```

自动复测覆盖不同 RAM 配置、模式切换与官方评分；主机测试用真实分配器源码配合独立占用记录执行两万次操作，并启用 ASan/UBSan。内存边界检查只在临时副本改写 DTB 查询返回值。映射检查读取客体 `satp`、页表项并核对虚实地址；它不代替 QEMU 源码级 TLB 调试。脚本需要 Linux/WSL 中已有的 GCC、RISC-V 工具链、GDB、QEMU 和 Python 3。

## QEMU 源码级页表与 TLB 调试

另外准备官方 QEMU 8.2.2 的独立调试构建，启用 `--enable-debug --enable-tcg-interpreter`，使用 `-O0 -g3`，保留源码目录。TCI 让两次加载的命中和未命中路径都能在 C 层观察；它用于本次功能调试，不用于评估硬件 TLB 性能。构建配置与源码散列见 [构建记录](report/evidence/2026-10-25-qemu-build-manifest.json)。

在本机 WSL 的仓库根目录运行：

```sh
python3 report/scripts/debug_qemu_mmu.py \
  --qemu /home/felix/oslab-tools/qemu-8.2.2/build/qemu-system-riscv64 \
  --source /home/felix/oslab-tools/qemu-8.2.2 \
  --out /tmp/lab2-mmu-check
```

其他机器应将前两个参数换成对应的调试二进制与源码路径。脚本协调宿主 GDB 和客体 GDB，在临时客体 RAM 中分别执行 Bare/Sv39 的两条 `ld` 指令，检查首次未命中、翻译与填充、再次命中，以及加载值；完成后恢复现场并清理本次 QEMU。

本轮实际数据为 `0xffffffffc1004000 → 0x81004000`，启动页表在根层遇到 1 GiB 叶子，只读一个 PTE；两次加载均读得 `0x1122334455667788`。八条结构化记录见 [MMU 结果](report/evidence/2026-10-25-mmu-host-summary.json)，完整的[宿主日志](report/evidence/2026-10-25-mmu-host-gdb.txt)与[客体日志](report/evidence/2026-10-25-mmu-guest-gdb.txt)分别保存。

实验指导书：[课程网站](http://oslab.mobisys.top/lab2026/_book/)。
