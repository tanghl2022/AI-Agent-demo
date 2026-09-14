import { describe, expect, test } from 'vitest'
import { SseParser } from './sseParser'

describe('SseParser', () => {
  test('支持一个 SSE Event 被拆成多个网络 chunk', () => {
    const parser = new SseParser()
    expect(parser.push('event: TOKEN\ndata: {"event":"TOKEN",')).toHaveLength(0)
    const events = parser.push('"requestId":"r1","sequence":1,"timestamp":"t","data":{"content":"库存"}}\n\n')
    expect(events).toHaveLength(1)
    expect(events[0].data).toEqual({ content: '库存' })
  })
})
