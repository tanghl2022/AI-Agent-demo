# 后端业务模块迁移实施清单

目标：按已确认方案分离 apps/warehouse、integrations/wms 和 infrastructure，保留 wms_agent 启动入口及当前 HTTP 协议。

执行方式：当前工作区直接实施，保留用户已有修改，不创建提交、不恢复已删除的生产 Mock 实现。

## 依赖与职责

- application.py：应用工厂，接收 Settings 和可替换 runtime 工厂。
- bootstrap.py：通过异步上下文管理器装配技术资源、外部系统、仓储模块。
- infrastructure/container.py：模型、审计连接池、checkpoint，负责退出清理。
- integrations/wms：HTTP 客户端，通过仓储协议提供库存和库位能力。
- apps/warehouse：仓储模型、协议、查询和执行服务、审计、工作流、Agent、API。
- API 仅通过 dependencies.py 获取应用服务；业务服务不读取 app.state。

## 实施步骤

- [ ] 基线：运行现有测试，记录悬空导入；新增离线 runtime、资源失败清理、冻结暂停/恢复回归测试。
- [ ] 移动当前文件并同步所有测试导入，保留节点名称和状态字段。
- [ ] 定义 InventoryPort、LocationPort 和仓储结果模型，HTTP Client 注入共享 AsyncClient。
- [ ] 修复配置读取、连接池审计和 checkpoint 初始化；增加建表 SQL。
- [ ] 创建 FreezeWorkflowService，统一 API 和 Agent 的流程调用与失败结果。
- [ ] 完成子容器、WarehouseContainer、ApplicationRuntime 和 FastAPI 工厂。
- [ ] 更新 API 依赖、SSE 取消清理、checkpoint 查询和旧流式接口兼容。
- [ ] 运行完整离线测试、编译、模块导入和架构边界检查。
- [ ] 更新后端架构、环境配置和运行说明；明确真实数据库/WMS/LLM 未联调的边界。

## 验证命令

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q backend/wms_agent
```

## 验收场景

库存不足不进入审批；批准执行一次冻结；拒绝不调用冻结；不同实例不串状态；同一流程重试使用相同幂等键；启动中途失败关闭已创建资源；测试应用不访问真实基础设施；每个 API 路径只注册一次。
