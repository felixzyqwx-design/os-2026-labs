# 本次验证证据

这些文件来自 2026-11-04 的 Lab 3 技术验收，与本分支源码对应。普通启动、官方注入测试、补充内核探针和 GDB 调试分别保留，图片是日志或数据排版。

| 文件 | 内容 |
| --- | --- |
| `results.json` | 十类技术检查与实际 make/qemu/grade 入口的退出状态；内存配置、切换构建等明细 |
| `grade.txt` | 官方评分完整输出，35+25+40=100 |
| `grade-context.txt`、`grade-illegal.txt`、`grade-timer.txt` | 官方三项注入用例的原始客体日志 |
| `boot.txt` | 默认启动、页分配自检及十行时钟输出；退出状态在 results.json |
| `probe-best-fit.txt`、`probe-first-fit.txt` | 真实 RV64 内核探针输出，包含合成 frame 分类和边界检查 |
| `gdb-exceptions.json`、`gdb-timer.json` | 四次异常和两次真实时钟的现场观察数据 |
| `gdb-exceptions.txt`、`gdb-timer.txt` | 对应 GDB 原始日志；调试采用临时源码副本，日志中临时路径是运行路径 |
| `failure-excerpts.txt` | 实际失败摘录，分别标明阶段和原文件名 |
| `grade-loader.diff` | 与官方 Lab 3 评分脚本比较，仅调整本机装载行 |
| `entry-disassembly.txt` | 实际 ELF 入口与起始指令；与镜像首指令已核对 |
| `source-audit.json` | 相对官方骨架的约束核对与源码散列，不包括编译产物 |
| `official-source.json` | 报告验收前重读 12 页及官方 ZIP 的来源、时间与散列 |
| `image-sources.json` | 三张图片所使用的原始证据、字段和图片散列 |

`source-audit.json` 的代码散列对应 `code/` 下相对路径；`official-source.json` 中 file 字段是网页原文件名，网页缓存保留在仓库外。主机 ASan/UBSan 回归仅证明链表行为，其测试替身不能代替 RV64 内核与原子操作验证。
