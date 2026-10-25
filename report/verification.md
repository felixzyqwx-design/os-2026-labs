# Lab 2 构建、运行与调试核验

更新日期：2026-10-25。报告中的数值对应以下日志；复现时地址可随链接结果变化。算法说明见[实验报告](report.md)。

## 1. 环境与记录来源

| 用途 | 环境 |
| --- | --- |
| 10-21 初次实验记录 | Windows PowerShell、SiFive GCC-Metal 10.2.0、Make 4.2.1、QEMU 5.1.0，来自原实验稿 |
| 10-22、10-25 内核复测 | WSL Ubuntu 24.04.1、RISC-V GCC 13.2.0、ld 2.42、Make 4.3、系统 QEMU 8.2.2、GDB 15.1 |
| 10-25 QEMU 源码调试 | 官方 QEMU 8.2.2 独立构建，`-O0 -g3`、debug、TCI；随源码附带的 OpenSBI 1.3.1 |

本轮重新执行的是 WSL 测试；Windows 一行保留初次环境记录。系统 QEMU 使用的 OpenSBI 为 1.3，与独立构建分开。构建产物 `code/bin/kernel` 为带符号 ELF，`code/bin/ucore.img` 为启动裸镜像，均不入库。

## 2. 手动构建和切换管理器

在 WSL/Linux 中进入仓库根目录，再执行：

```sh
cd code
make
make qemu
make PMM=buddy
make qemu PMM=buddy
make PMM=first_fit
make qemu PMM=first_fit
make
make grade
```

每次 QEMU 自检完成后，先按 `Ctrl+A`，松开后按 `X` 退出，再执行下一条命令。内核此时仍在等待循环。Makefile 会比较有效编译配置，模式变化自动重编译；兼容旧用法 `make DEFS=-DPMM_BUDDY`。Windows 可用 `mingw32-make` 替代 `make`；原稿使用 `-B` 强制构建，当前不再要求靠 `-B` 切换模式。

默认 Best-Fit 本轮关键输出：

```text
memory management: best_fit_pmm_manager
physical memory map: [0x0000000080000000, 0x0000000088000000), free: [0x0000000080347000, 0x0000000088000000)
check_alloc_page() succeeded!
satp virtual address: 0xffffffffc0205000
satp physical address: 0x0000000080205000
```

最后两行是引导页表的虚拟、物理地址，实际 CSR `satp` 还包含模式位；本轮调试读到 `0x8000000000080205`。Buddy 关键输出为 `buddy_pmm_manager`、`buddy checks: split, round-up, free and counts passed` 和自检完成标记；First-Fit 显示 `default_pmm_manager`。

`make grade` 使用临时副本注入原课程测试，并将原始内核输出复制到 `code/.qemu.out`。10-25 评分为：

```text
  -check page init:                          OK
  -check best fit:                           OK
Total Score: 20/20
```

原始内核输出同时包含 `[Test 1] Page Init: PASS`、`[Test 2] Best-Fit: PASS`。该分数不覆盖 Buddy 和 QEMU 源码调试。

## 3. 自动回归与边界测试

从仓库根目录运行，输出目录可自行更换：

```sh
python3 report/scripts/verify_lab2.py --out /tmp/lab2-regression
python3 code/tools/tests/run_host.py --out /tmp/lab2-host
python3 report/scripts/check_page_init.py --out /tmp/lab2-page-init
python3 report/scripts/check_mapping.py --out /tmp/lab2-mapping
```

| 脚本 | 实测覆盖与判定 |
| --- | --- |
| `verify_lab2.py` | 10-25 共 14 项：默认构建，128/64/256 MiB 启动，Buddy 构建/符号/启动，First-Fit 构建/启动，恢复默认构建/符号/启动，评分及原始内核标记；全部通过 |
| `run_host.py` | 10-22 使用真实 Best-Fit、Buddy 源码，分别完成 20,000 次固定种子操作、3001 页耗尽与逆序回收，ASan/UBSan 通过 |
| `check_page_init.py` | 10-22 在临时副本覆写 DTB 查询：零容量、错误基址、加法溢出、内存末端低于内核、描述符空间不足、非整页尾部、无完整空闲页；7 项通过 |
| `check_mapping.py` | 10-22 客体 GDB 读取 `satp` 与根 PTE，核对高地址指令和对应物理地址字节；不进入 QEMU 源码 |

边界脚本保留正式源码与 DTB 解析器。零完整空闲页用例仅在副本中将常规分配自检替换为空闲数为零的断言；其余正常初始化用例要求自检完成且无 panic，非法输入则要求指定报错。自动启动测试按有界观察窗口收集输出，出现完成标记且无错误才通过；摘要中的 `timed_out` 表示窗口到期后由脚本停止持续运行的内核。

另验证过 `CC=false` 构建失败会传回失败，临时评分副本和本次进程完成清理；相同构建参数再次执行时不重复编译。见下方 10-22 的对应日志。

## 4. QEMU 源码级页表与 TLB 调试

需要 Linux/WSL 下的宿主 GDB、`gdb-multiarch` 和带符号的 QEMU 源码构建。独立构建的关键配置为：

```sh
./configure --target-list=riscv64-softmmu --enable-debug \
  --enable-tcg --enable-tcg-interpreter --enable-fdt \
  --disable-pie --extra-cflags='-O0 -g3'
make -j2
```

配置命令在独立 QEMU 构建目录中执行，系统需有相应构建依赖。本机使用精简组件与局部 SDK 路径，完整实际配置、官方源码 URL 和 SHA256 见[构建记录](evidence/2026-10-25-qemu-build-manifest.json)。无需 `make install`。官方源码压缩包 SHA256 为 `847346c1b82c1a54b2c38f6edbd85549edeb17430b7d4d3da12620e2962bc4f3`。

在本机 WSL 的课程仓库根目录执行：

```sh
python3 report/scripts/debug_qemu_mmu.py \
  --qemu /home/felix/oslab-tools/qemu-8.2.2/build/qemu-system-riscv64 \
  --source /home/felix/oslab-tools/qemu-8.2.2 \
  --out /tmp/lab2-mmu
```

其他机器将前两个路径换为自己的构建和源码。控制脚本协调 `mmu_host.py` 与 `mmu_guest.py`：宿主 GDB 启动 QEMU 并观察 C 分支，客体 GDB 在 Bare 和 Sv39 下执行两次加载。目标地址分别为 `0x81004000`、`0xffffffffc1004000`，两者均对应物理地址 `0x81004000`。

通过判据包括：两种模式首次查询未命中、翻译及填充被捕获、第二次查询命中、两次加载均为 `0x1122334455667788`；宿主和客体日志分别出现 `MMU HOST CHECK COMPLETE`、`MMU GUEST CHECK COMPLETE`，控制脚本成功退出。最终检查没有遗留本次 QEMU；脚本按记录的 PID、二进制与端口确认进程归属。具体函数、PTE 和计算见报告第 4 节。

## 5. 证据索引

| 内容 | 文件 |
| --- | --- |
| 10-25 的 14 项回归 | [摘要](evidence/2026-10-25-regression-summary.json)、[默认启动](evidence/2026-10-25-regression-boot-default.txt)、[Buddy 启动](evidence/2026-10-25-regression-boot-buddy.txt)、[First-Fit 启动](evidence/2026-10-25-regression-boot-first-fit.txt) |
| 10-25 课程评分 | [评分日志](evidence/2026-10-25-regression-grade.txt)、[原始内核输出](evidence/2026-10-25-regression-grade-kernel.txt) |
| 10-22 多 RAM 配置 | [64 MiB](evidence/2026-10-22-review-verified-boot-default-64.txt)、[256 MiB](evidence/2026-10-22-review-verified-boot-default-256.txt) |
| 10-22 分配器主机测试 | [Best-Fit](evidence/2026-10-22-review-host-host-best_fit.txt)、[Buddy](evidence/2026-10-22-review-host-host-buddy.txt) |
| 10-22 初始化边界与客体映射 | [7 项摘要](evidence/2026-10-22-review-page-init-summary.json)、[客体 GDB](evidence/2026-10-22-review-mapping-mapping-gdb.txt) |
| 10-22 启动失败定位 | [GDB](evidence/2026-10-22-review-boot-probe-gdb.txt)、[异常跟踪](evidence/2026-10-22-review-boot-probe-traps.txt) |
| 10-22 构建与评分修正 | [换行核对](evidence/2026-10-22-review-grade-checkout-eol.txt)、[预期构建失败](evidence/2026-10-22-review-grade-expected-build-failure.txt)、[相同配置无重建输出](evidence/2026-10-22-review-build-no-change.txt) |
| 10-25 QEMU 源码调试 | [宿主 GDB](evidence/2026-10-25-mmu-host-gdb.txt)、[客体 GDB](evidence/2026-10-25-mmu-guest-gdb.txt)、[结构化观察](evidence/2026-10-25-mmu-host-summary.json)、[最终检查](evidence/2026-10-25-mmu-final-checks.json) |
| 源码调试过程中的失败 | [标注来源的日志摘录](evidence/2026-10-25-mmu-failure-excerpts.txt) |

日志仅将终端 NUL 字节显示为 `\x00`，图片为这些记录的摘录排版。图片生成源为 [render_results.py](scripts/render_results.py)。
