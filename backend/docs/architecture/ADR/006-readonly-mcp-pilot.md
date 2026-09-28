# ADR-006：库存分析只读 MCP 试点

状态：Accepted，2026-09-25。补充 ADR-005；不开展全量 MCP 改造。

用户明确选择以 MCP 为当前演进方向，并要求实现库存分析、依据、可见调用及错误处理。
沿用现有 mcp-server，采用官方 Python SDK 的独立 Streamable HTTP 服务，只暴露库存与库位查询。
Agent 启动发现工具、验证白名单与 Schema，注入 InventoryAnalysisSubAgent；固定查询和冻结保持原链路。

选择 SDK 直接映射为 StructuredTool，以保留 isError/structuredContent 和领域结果校验；第一期不额外引入适配库。
客户端每次调用自行创建会话，代价是初始化开销，收益是异步任务与凭据隔离简单、生命周期明确。
默认 local；mcp 模式不静默回退，发现失败阻止启动，调用失败返回受控错误。

本期不包括写工具、Resources、Prompts、多 Server 动态配置、用户级委托、MCP OAuth 或公共部署。
证据是查询记录和事实清单，不声称完成了对模型自然语言推断的形式化验证。
