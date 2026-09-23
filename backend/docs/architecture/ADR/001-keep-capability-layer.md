# ADR-001：保留 Capability Layer

## 状态
Accepted

## 背景
WMS Agent 引入 Tool Calling 后，Tool 已经能够作为 LLM 的业务能力调用入口，因此需要决定 Tool 是否直接调用 Service，还是继续保留 Capability 层。

## 决策问题
是否采用 `Tool → Service → Java API` 的简化结构，删除 Capability；还是采用 `Tool → Capability → Service → Java API`？

## 可选方案

### 方案 A：Tool 直接调用 Service
优点：
- 调用链较短
- 初期代码量较少

缺点：
- AI Tool 与具体基础设施访问方式耦合
- Tool 容易逐渐承载业务逻辑
- 未来 HTTP、MCP 等访问方式切换时影响 Agent 层

### 方案 B：保留 Capability
优点：
- Tool 负责面向 LLM 暴露能力
- Capability 负责稳定的业务能力抽象
- Service 负责 HTTP/API 等基础设施访问
- 便于未来替换底层 Provider

缺点：
- 增加一层抽象
- 简单查询场景代码量略有增加

## 最终决策
采用方案 B，保留 Capability Layer。

当前标准调用链：

`Tool → Capability → Service → Java API → WMS`

## 决策原因
Tool、Capability、Service 属于不同职责边界。Tool 是 AI 接口，Capability 是业务能力抽象，Service 是外部系统访问实现。保留 Capability 可以避免 AI 层与具体通信协议耦合。

## 影响
后续新增 Tool 时，不应把复杂业务实现直接写入 Tool。未来接入 MCP 时优先在 Capability 下替换或增加 Provider，而不是直接改造所有 Agent。

## 重新评估条件
如果实践证明 Capability 长期只是无逻辑的纯转发层，且没有形成稳定业务抽象，应重新评估是否保留。
