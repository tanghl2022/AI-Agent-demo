import { describe, expect, test } from 'vitest'
import { applyAgentEventToExecutions } from './agentExecution'
import type { AgentEvent } from '../types/agent'
import type { AgentExecutionItem } from '../types/execution'

const envelope = (event: AgentEvent['event'], sequence: number, data: unknown): AgentEvent => ({ event, requestId: 'r1', sequence, timestamp: 't', data })

describe('agentExecution projection', () => {
  test('TOOL_END 通过 toolCallId 更新原 TOOL_START', () => {
    const items: AgentExecutionItem[] = []
    applyAgentEventToExecutions(envelope('TOOL_START', 1, { toolCallId: 'run-1', toolName: 'query_stock' }), items)
    applyAgentEventToExecutions(envelope('TOOL_END', 2, { toolCallId: 'run-1', toolName: 'query_stock', success: true, durationMs: 57 }), items)
    expect(items).toHaveLength(1)
    expect(items[0].status).toBe('success')
    expect(items[0].durationMs).toBe(57)
  })
})
