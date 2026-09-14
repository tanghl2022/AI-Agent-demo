# Tool Calling

Tool 是 Agent 可调用的受控外部能力，不是把 WMS 业务规则交给 LLM。

本 Demo 只有只读 Tool：`query_stock`、`query_inventory_detail`、`query_location`。真实生产环境中，写操作必须通过受控 WMS API，并加入权限、参数校验、状态机、幂等、事务和人工审批。

同名 Tool 可以并行多次调用，因此生命周期关联不能只依赖 toolName；当前 Demo 使用 Runtime `run_id` 作为 Timeline 的 toolCallId。
