# WMS Agent Architecture

## Overall Architecture

User
↓
Web / SSE
↓
Main Agent
↓
Intent Router
↓
Node
↓
Capability / SubAgent
↓
Tool Calling
↓
MCP Server
↓
Java WMS API
↓
MySQL / Redis / MQ


## Layer Responsibility

### Graph

负责流程编排和状态流转。

### Node

负责 LangGraph 执行节点。

### Capability

封装稳定业务能力边界。

### SubAgent

负责需要 LLM 推理、多 Tool 协作的复杂任务。

### MCP Server

负责将 WMS API 暴露为标准 AI Tool。

### Java WMS

负责所有确定性业务规则和数据一致性。


## Dependency Rule

允许：

Graph → Node

Node → Capability

SubAgent → Tool

Tool → MCP

MCP → WMS API


禁止：

Agent → Database

MCP → Database

LLM → Core Business Rule