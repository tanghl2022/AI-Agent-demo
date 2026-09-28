import { describe, expect, test } from 'vitest'
import { applyAgentEvent } from './agentExecution'
import type { AgentEvent } from '../types/agent'
import type { AgentExecutionItem } from '../types/execution'

const envelope = (eventType: AgentEvent['eventType'], sequence: number, data: unknown): AgentEvent => ({
  eventType, eventId: `e${sequence}`, conversationId: 'c1', requestId: 'r1', sequence,
  timestamp: '2026-09-25T00:00:00Z', data
})

describe('agentExecution projection', () => {
  test('TOOL_END 通过 toolCallId 更新原 TOOL_START', () => {
    const items: AgentExecutionItem[] = []
    applyAgentEvent(items, envelope('tool_start', 1, { toolCallId: 'run-1', toolName: 'query_stock' }))
    applyAgentEvent(items, envelope('tool_end', 2, { toolCallId: 'run-1', toolName: 'query_stock', success: true, durationMs: 57 }))
    expect(items).toHaveLength(1)
    expect(items[0].status).toBe('SUCCESS')
    expect(items[0].durationMs).toBe(57)
  })
  test('同名 MCP 工具乱序完成时按调用 ID 配对，并保留失败与查询结果', () => {
    const items: AgentExecutionItem[] = []
    applyAgentEvent(items, envelope('tool_start', 1, { toolCallId: 'a', toolName: 'wms_query_stock', args: { material_code: 'M001' } }))
    applyAgentEvent(items, envelope('tool_start', 2, { toolCallId: 'b', toolName: 'wms_query_stock', args: { material_code: 'M002' } }))
    applyAgentEvent(items, envelope('tool_end', 3, { toolCallId: 'a', toolName: 'wms_query_stock', success: false, summary: '查询超时', durationMs: 20 }))
    applyAgentEvent(items, envelope('tool_end', 4, { toolCallId: 'b', toolName: 'wms_query_stock', success: true, output: { data: { available_qty: 12 } } }))
    expect(items).toHaveLength(2)
    expect(items[0].id).not.toBe(items[1].id)
    expect(items[0].status).toBe('FAILED')
    expect(items[0].description).toBe('查询超时')
    expect(items[0].toolArgs).toEqual({ material_code: 'M001' })
    expect(items[1].status).toBe('SUCCESS')
    expect(items[1].toolResult).toEqual({ data: { available_qty: 12 } })
    expect(items[0].title).toBe('库存查询（MCP）')
  })
  test('证据不足不能显示为成功', () => {
    const items: AgentExecutionItem[] = []
    applyAgentEvent(items, { ...envelope('done', 1, { answer: '证据不足' }), status: 'INSUFFICIENT_EVIDENCE' })
    expect(items[0].status).toBe('WAITING')
  })
})
