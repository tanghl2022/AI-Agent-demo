# WMS Agent Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deployable study project containing the WMS Agent backend, Vue visualization frontend, tests, checkpoint demo, and Docker Compose.

**Architecture:** A FastAPI/LangGraph backend exposes REST and SSE endpoints. The graph uses read-only WMS tools and InMemorySaver; AgentService converts runtime events into a stable AgentEvent protocol. Vue consumes only the unified SSE endpoint and renders streamed answer content plus Tool Timeline.

**Tech Stack:** Python 3.11, FastAPI, LangGraph, LangChain OpenAI-compatible client, Pydantic v2, Vue 3, TypeScript, Vite, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-08-26-wms-agent-demo-design.md`

## Global Constraints

- Backend-first learning project.
- WMS tools are read-only.
- Default WMS integration is mock and self-contained.
- InMemory checkpoint only; no PostgreSQL/RAG/HITL in this version.
- Unified event names are uppercase.
- Tool timing uses runtime `run_id` and `on_tool_start/on_tool_end`.

---

### Task 1: Backend foundations

**Files:** model, config, event factory, token buffer, tracker, tests.

- [x] Add failing unit tests for event sequencing, token buffering and per-run tool timing.
- [x] Implement the minimal utility classes.
- [x] Run pytest and confirm green.

### Task 2: WMS tools and graph

**Files:** mock client/service, tool definitions, graph state/builder.

- [x] Add deterministic read-only WMS tool data.
- [x] Bind tools to ChatOpenAI-compatible model.
- [x] Build `agent -> tools -> agent` graph with `InMemorySaver`.
- [x] Add graph/checkpoint tests that do not require a network model where practical.

### Task 3: Agent runtime and API

**Files:** AgentService, controller, application.

- [x] Implement regular chat execution with thread_id config.
- [x] Implement unified `astream_events()` conversion to AgentEvent.
- [x] Add SSE endpoint `/api/agent/chat/unified-stream`.
- [x] Add health endpoint and API tests.

### Task 4: Vue visualization

**Files:** Agent types, SSE parser, API service, timeline projection, components, App.vue.

- [x] Parse SSE safely across network chunks.
- [x] Keep assistant message reactive for streamed token updates.
- [x] Map TOOL_START/TOOL_END by toolCallId/run_id into a single timeline item.
- [x] Render status, tool duration and streamed answer.
- [ ] Build frontend successfully. *(sandbox npm install timed out; core TypeScript files were checked with global tsc)*

### Task 5: Deployment and learning docs

**Files:** Dockerfiles, docker-compose.yml, README and study docs.

- [x] Add backend/frontend containers.
- [x] Document local and Docker startup.
- [x] Document sample questions and checkpoint thread tests.
- [x] Add learning notes for streaming/SSE/runtime events/checkpoint.
- [x] Run final tests and package ZIP.
