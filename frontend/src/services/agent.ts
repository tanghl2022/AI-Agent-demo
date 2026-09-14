import type { AgentEvent } from '../types/agent'
import { SseParser } from '../utils/sseParser'

export interface ChatStreamRequest { message: string; threadId: string }

export async function streamAgentChat(request: ChatStreamRequest, onEvent: (event: AgentEvent) => void): Promise<void> {
  const response = await fetch('/api/agent/chat/unified-stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  })
  if (!response.ok || !response.body) throw new Error(`Agent 请求失败: ${response.status}`)
  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  const parser = new SseParser()
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    const text = decoder.decode(value, { stream: true })
    parser.push(text).forEach(onEvent)
  }
  const tail = decoder.decode()
  if (tail) parser.push(tail).forEach(onEvent)
}
