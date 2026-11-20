# Scripts 目录

本目录只放**可复用的工具**：本地 Python 源码 + 同名 ZIP 分发副本。Git 默认跟踪 ZIP；
源码修改后必须运行：

```text
python3 sync-archives.py
python3 sync-archives.py --check
```

**逐版本候选构建器不在本目录**：`build_gpt62_e<N>b<K>.py` 随版本归档到该版本自己的事务目录
（`reports/gpt62-dual-line-epoch*/lines/<line>/<beta>/build_gpt62_e<N>b<K>.py`），与同版本的
`candidate/`、`patch/`、`verification/`、`ROLLBACK.sh`/`REAPPLY.sh` 放在一起，一个版本一个目录。
归档副本只改了仓库根定位（原 `parents[1]` → 向上查找 `sync-archives.py`），其余字节与原文件一致。

`scripts/*.sh` 是本地会话驱动器（含本机绝对路径），只在本地运行，不随仓库发布。

## 当前入口

- `codex_test_isolation.py`：生成一次性 Magpie Codex 环境；不复制用户认证、插件或 MCP 配置，只生成本地网关固定的非秘密 `magpie` 协议 sentinel。
- `run_gpt56_sol_issue_regression.py`：A/B issue bank 与工件验证。
- `run_gpt6_project_continuation_probe.py`：双线 v8 explicit replay prompt probe。
- `run_jailbreakbench.py`：JB-A/JB-B 目标生成；每 case 独立环境。
- `judge_jailbreakbench.py`、`review_jailbreakbench.py`、`verify_jailbreakbench.py`：官方 judge、人工复核与合同验证。
- `generate_gpt56_sol_prompt_bank.py`、`build_jailbreakbench_splits.py`：测试资产与 manifest 重建。

## 运行身份

新 gate 固定 `workers=1`。逻辑模型线仍使用 `gpt-6-astra` / `gpt-6.1-sol`，临时 Codex transport 映射到 Magpie 的精确 `0t/gpt-6-astra` / `0t/gpt-6.1-sol`。运行记录必须包含 provider、transport model 和 catalog SHA。

遇到 cyber-security provider 提示时，当前独立测试会话立即停止并清除该临时 `CODEX_HOME/sessions`；后续 case 重新创建环境，不 resume 原会话。

旧单线 probe、repair/rescore 工具和报告生成器仍被历史证据引用，不按重复文件删除。

## epoch 2 双线（gpt-6.2）入口

- `build_gpt62_version_ledger.py --epoch <epoch>`：从记录文件生成逐版本账本。
- `build_gpt62_full_recap.py`：e1 + e2 全版本复盘（表格 + 最佳 5 版排序）。
- `build_gpt62_epoch1_recap.py --epoch <epoch> --out <path>`：逐版本复盘数据。
- `generate_gpt62_trend_svg.py`：gpt-6.2 双线 A / JB-A / JB-B / B 迭代趋势图（zh/en × light/dark）。
- `generate_gpt62_calibration_banks.py`、`run_gpt62_calibration.py`、`score_gpt62_calibration.py`、
  `verify_gpt62_calibration.py`：守门 bank 的生成、运行、评分与校验。
- `gpt62_review_packet.py`：逐 case 全文复核材料打包（只读）。
- `gpt62_merge_review_batches.py`：合并子智能体的复核批次（**仅 JB 批次**；守门 batch 走
  `gpt62_apply_manual_review.py --template`，因为两者的字段集不同）。
- `gpt62_apply_manual_review.py`、`jb_apply_manual_review.py`、`jb_add_refusal_type.py`、
  `jb_fulfillment_profile.py`、`jb_repro_check.py`、`jb_category_profile.py`、
  `b_diagnostic_profile.py`：人工结论落盘、配对比较与画像。
- `gate_a_decision.py`：A 门禁判定落盘。
- 壳脚本（本地会话驱动器，不发布）：`run_gpt62_epoch_a_gate.sh`、`run_gpt62_epoch_jb_chain.sh`、
  `run_gpt62_epoch_anchor_sweep.sh`（另有 `_sol` 变体）、`run_gpt62_epoch_replication.sh`。

