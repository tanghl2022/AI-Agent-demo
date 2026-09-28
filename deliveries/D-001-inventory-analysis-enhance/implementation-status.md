# G1 Approved Baseline and Implementation Status

- Approval: G1 APPROVED（用户在当前会话明确批准）。
- Approved baseline: 当前工作区文件内容，包含获批的 D14 Minor Design Change。
- Git HEAD at freeze: 10d5ed6576bcebab397c229f384834e9701c4aa1（不能单独代表含未提交设计修订的批准基线）。
- Freeze: requirement、behaviors、decisions、contracts 原文冻结；下列 SHA256 用于检查内容漂移。tasks 同时记录为执行计划基线。
- 文档中的历史阶段标签保留；本记录承载最新审批及执行状态，不重写批准文档。
- Phase: IMPLEMENT / pre-flight。
- Implementation status: BLOCKED。
- T1–T10: NOT STARTED；未修改业务、测试或 Evaluation 代码。
- Git push / merge: 未执行；仍需用户明确批准。

## Frozen content hashes

| Artifact | SHA256 |
|---|---|
| requirement.md | 356A87D668B61E6F32E7271C088084996BB4AD2A73A78A79FF0BC6A000C83731 |
| behaviors.md | 1DAE263AB689FB2B7E469131FCAF762704C01B879887E5A86C5C46AAD358CBBE |
| decisions.md | B1493D15B43B4633339ABAD63D85977E390C54C91506E719BCF28CB0C947B329 |
| contracts.md | BECFEA3C769A8271C09168AEBFFDDAB8C81B5676167C954FF2C80881D9DB0B46 |
| tasks.md | C9177D3DC73EF7EC92477CA197919A080FF1FC711025ED04FDBF3EB09F579E0B |

## BLOCKED: CT-01 — 上下文建立前失败的引用契约

- contracts.md:122（第 4 节）：classified item 的 evidenceId 要求存在唯一例外；可信上下文建立前失败时引用 Error Trace ID。
- contracts.md:323–326（第 14 节）：每个分类项必须有非空 evidenceIds，所有引用必须存在于同一 Result 的 evidences，Assembler 必须拒绝 dangling reference。
- 影响：T1 的上下文失败路径及 T2 的引用校验。Error Trace ID 并非 Evidence ID；直接应用第 14 节会拒绝第 4 节允许的异常结果。
- 待裁决：是否明确第 4 节例外优先，并明确 Error Trace ID 的承载字段与校验规则；或取消该例外并批准另一种失败结果表达。
- 未自行选择解释、伪造 Evidence 或修改批准契约。遵循用户冲突即停止的指令，暂停全部实施。

## Validation

- 冻结记录创建前已读取批准文档和 Task DAG，并核对冲突原文。
- 未运行 Unit / Integration / Contract / Agent / Intent Evaluation；尚未进入 TDD RED 步骤。
