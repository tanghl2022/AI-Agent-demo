# G1 Approved Baseline and Implementation Status

- Gate: G1 APPROVED，含 D14 Minor Design Change 及本次用户批准的 Error Trace ID Contract Clarification。
- Phase: IMPLEMENT / T1。
- CT-01: RESOLVED；第 4 节例外优先，诊断 Trace 与业务 Evidence 标识严格分离。
- 基线：requirement、behaviors 保持原文；decisions、contracts 仅同步获批澄清；tasks 同步验收要求。
- 活跃实施工作区：C:\Users\86187\.codex\worktrees\inventory-analysis\wms-agent-demo
- Branch: codex/inventory-analysis
- Base commit: 10d5ed6576bcebab397c229f384834e9701c4aa1
- 未 push，未 merge。

## Current frozen content hashes

| Artifact | SHA256 |
|---|---|
| requirement.md | 356A87D668B61E6F32E7271C088084996BB4AD2A73A78A79FF0BC6A000C83731 |
| behaviors.md | 1DAE263AB689FB2B7E469131FCAF762704C01B879887E5A86C5C46AAD358CBBE |
| decisions.md | 92900A9B77B88D11EBCD51142A16FFE7A9F1AE2C57425CC6D02D006015D06FEB |
| contracts.md | 651E5EA6581C6A166018A84D59EC070AFD8E3B73F6F23D8A413D594AA3A9A4DD |
| tasks.md | C50F5892C1C870501C60840FA4065FF9BB5AAA4267B91142DF75F00AACDFAB71 |

## Pre-flight contract consistency review

- 第 3/4/14 节：上下文建立前 FAILED 可以有空 evidences 和独立 error.traceId；不要求伪造 subject 身份或 Evidence。
- 第 4/14 节：facts/possibleCauses 非空 evidenceIds 和 unknowns 中存在的 evidenceIds 必须引用同一 Result 的 Evidence。
- 第 11/17 节：诊断错误仅用于排障关联，不支持 FACT/POSSIBLE_CAUSE；阶段未产生的关联键不伪造。
- D8/D9、T1/T2：引用规则与上下文失败处理已同步。
- D14 与契约第 15 节：Renderer 仅表达 Result；Error Trace 不成为业务事实来源。
- T1→T2→T5/T6→T7：Request Context、结果模型、MCP/子 Agent、API 职责保持原 DAG。
- 检查未发现其他需改变批准契约的冲突；无新增异常、原因、Evidence 类型或业务范围。

## T1 progress and verification

- 实现 RequestContext、State 逐轮重置、缺参/缺身份/缺仓库补问、Node 防御性校验、HTTP/SSE 可信上下文传递。
- RequestContext.authorization 不进入序列化结果、日志表示或 Checkpoint。
- T1 RED batch 1: 13 failed（缺少目标行为）；GREEN: 13 passed。
- T1 RED batch 2: 6 failed / 13 passed（服务/API 接入缺失）；GREEN: 19 passed。
- 增加真实 Graph 的 3 个受限上下文 Agent Evaluation 用例和 1 个 Checkpoint 隔离用例。
- 原基线：79 passed。首次完整回归：99 passed / 3 failed；旧分析测试未提供获批的可信上下文前置条件，已补齐 fixture，原有断言保留。
- 最终完整回归：103 passed in 21.44s（含 24 项 T1 测试、真实 Graph 的受限上下文 Agent Evaluation、Checkpoint 隔离、既有 MCP/Integration/Architecture 测试）。
- 诊断 Trace 日志关联：新增用例先 RED（返回 ID 无对应日志），最小修复后完整 suite GREEN。
- 独立 T1 代码审查通过：未发现高、中严重度缺陷；审查员未独立重跑测试。
- T1：实现与当前任务验证完成；不代表 D-001 整体 DoD 或 G2 通过。
- T2–T10 尚未完成；结构化 SubAgent ainvoke 和 MCP 可信元数据转发按 T6/T5 实施，本轮不宣称已交付。
- 生产认证/Session 层须建立类型化 RequestContext；缺失时本实现 fail closed，不从客户端身份头或自然语言建立身份。

## Test environment

- 原 backend/.venv 启动器引用已失效的 Python 路径。
- 使用 D:\software\python\python.exe（Python 3.13）及原虚拟环境依赖；缺失的 mcp==1.30.0 与 jsonschema 安装在隔离工作区 .test-deps，未改全局 Python 环境。
- .test-deps 已加入本地 Git exclude；未改变项目依赖声明。

