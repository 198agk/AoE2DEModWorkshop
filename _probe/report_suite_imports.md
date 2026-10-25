# 注册套件的可 import 性：一次普查（2026-10-25）

**结论先说**：133 条注册的 py 套件里，**69 条有 `__main__` 守卫，64 条没有**；其中 **37 条
没有守卫、却在模块级以 `sys.exit(...)` 结尾** —— import 它们会**直接结束调用它的进程**
（`SystemExit` 逃出 import）。这份文件是测量记录，不是待修清单的替代品。

## 怎么发现的（两次，都是我自己付的钱）

1. `_probe/run_suites.py`：我为了复用它的 `_FAIL_RE`，写了一个 `from _probe import
   run_suites`，结果 import **直接起了一整轮 131 条**（十分钟仍停在 `test_panel_*`）。
   已修：驱动段搬进 `def main():` + `if __name__ == "__main__":`，并有常驻钉子
   `_probe/test_runner_contract.py`（A 段在子进程里真 import 一次并计时）。
2. `_probe/test_full_sweep.py`：我为了读它的豁免表 / 覆盖判据，`import` 了一次，
   又是整轮 20 分钟扫描（后台 job `pwsh-71ffb094da3d4766`，已 kill）。
   **这一条没有修**（见下）。

## 普查方法

`_probe/tmp_guard_census.py`（一次性，未登记）：

- 从 `_probe/run_suites.py` 的 `SUITES` 拿全部登记的相对路径；
- 对每个文件读源码，找 `^if __name__ == ['"]__main__['"]:`；
- 把守卫**之前**的部分里，行首的 `sys.exit(` 与 `subprocess.run(` 计数，当作「模块级会做事」的代理。

这是**代理判据**，不是证明：模块级 `for` 循环里做事、或调别的函数，这个测法看不见。
它的用途只是把「哪些文件我绝对不能 import」列出来。

## 读数

```
registered py suites: 133  with a __main__ guard: 69  without: 64
without a guard, but ending in sys.exit : 37
without a guard and without a top-level exit : 27
```

没有守卫但以 `sys.exit` 结尾的 37 条（**import 会结束进程**），按文件大小排列：

| 套件 | `sys.exit` | 字节 |
|---|---|---|
| `_probe/test_availability_dat_half.py` | 1 | 7660 |
| `_probe/test_bundle_dat_half_e2e.py` | 1 | 6523 |
| `_probe/test_button_groups.py` | 1 | 5309 |
| `_probe/test_button_slots.py` | 1 | 5188 |
| `_probe/test_dat_carrier.py` | 1 | 12375 |
| `_probe/test_dat_edit_routes.py` | 1 | 9422 |
| `_probe/test_dat_grant_route.py` | 1 | 6648 |
| `_probe/test_dat_half_count.py` | 1 | 10238 |
| `_probe/test_datgrant.py` | 1 | 12513 |
| `_probe/test_decisive_subjects.py` | 1 | 7095 |
| `_probe/test_effect_walk.py` | 1 | 6760 |
| `_probe/test_enabling_research.py` | 1 | 8351 |
| `_probe/test_enabling_vs_effect.py` | 1 | 8150 |
| `_probe/test_info_json_shape.py` | 1 | 5085 |
| `_probe/test_mod_name_resolution.py` | 1 | 12617 |
| `_probe/test_panel_is_not_build_menu.py` | 1 | 6119 |
| `_probe/test_panel_shape.py` | 1 | 9263 |
| `_probe/test_panel_tree_agreement.py` | 1 | 10315 |
| `_probe/test_panel_vs_dat_train.py` | 1 | 6419 |
| `_probe/test_protocol_subjects.py` | 1 | 12493 |
| `_probe/test_revoke_chain_closed.py` | 1 | 5572 |
| `_probe/test_screen_vocabulary.py` | 1 | 5620 |
| `_probe/test_smoke5_design.py` | 1 | 9176 |
| `_probe/test_smoke6_result.py` | 1 | 10883 |
| `_probe/test_smoke8_control_b.py` | 1 | 8608 |
| `_probe/test_subject_instantiable.py` | 1 | 5203 |
| `_probe/test_tech_cost.py` | 1 | 13600 |
| `_probe/test_tech_intent.py` | 1 | 11512 |
| `_probe/test_test_validity.py` | 1 | 6475 |
| `_probe/test_time_gate_and_tooltip.py` | 1 | 13980 |
| `_probe/test_trigtech_space.py` | 1 | 10236 |
| `_probe/test_v2_semantic_diff.py` | 1 | 8665 |
| `_probe/test_v4_reproduces_incas.py` | 1 | 4841 |
| `_probe/test_zero_mod_experiment.py` | 1 | 19427 |
| `_probe/probe_button_slot_collision.py` | 1 | 5968 |
| `_probe/probe_free_slot_rule.py` | 1 | 8225 |
| `_probe/probe_slot_grouping.py` | 1 | 6244 |

## 为什么 `_probe/test_full_sweep.py` 这次不修

它是 402 行、**驱动逻辑全部在模块级**（`ast` 数出 70+ 个顶层语句，其中大量 `for` /
`Expr`），要加守卫就得把整段缩进进 `def main():`。**我没有在不动它的前提下验证等价性的
手段**：唯一能证明「重构后行为不变」的测试就是它自己，而要跑它要 20 分钟，且它现在一
import 就退出进程。

结论：**保持现状，但在报告里点明它的形状** —— 任何脚本想读它的表，必须
`ast.literal_eval` 读源码（`_probe/test_sweep_exemptions.py` 正是这么做的），绝不能 import。

## 这条记录想防的失败

不是「import 一个套件会慢」，是**一次 import 会让调用它的进程静默消失**：
`sys.exit` 抛的是 `SystemExit`，它会穿过 `import` 继续往外抛，而 `try/except Exception`
抓不到它（它不是 `Exception` 的子类）。所以「我在探针里 import 一下那个套件」会表现为
探针什么都没打印、退出码却是套件的结论。

## 诚实边界

- 37 这个数字依赖那个代理判据；**没有验证过**每一条在真的 import 时都会退出（那要 37 次
  import，其中几次会跑很久）。样本只有 2 次真实观察：`run_suites.py`（已修）与
  `test_full_sweep.py`（未修）。
- 27 条「没有守卫也没有顶层 exit」不等于「import 无害」：它们可能仍然在模块级做重活。
