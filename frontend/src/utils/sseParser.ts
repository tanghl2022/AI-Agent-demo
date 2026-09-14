import type { AgentEvent } from '../types/agent'


/**
 * SSE 数据解析器。
 *
 * 职责非常单一：
 *
 * HTTP Chunk
 *      ↓
 * 字符串 Buffer
 *      ↓
 * 找到完整 SSE Frame
 *      ↓
 * 提取 data:
 *      ↓
 * JSON.parse
 *      ↓
 * AgentEvent
 *
 * 注意：
 *
 * 这里不负责处理：
 *
 * agent_start
 * intent_result
 * tool_start
 * done
 *
 * 这些属于业务层逻辑，
 * 后续由 agentExecution.ts 处理。
 */
export class SseParser {

  /**
   * 保存尚未组成完整 SSE Frame 的字符串。
   *
   * 为什么需要 buffer？
   *
   * 因为一次 reader.read() 读取的是网络 Chunk，
   * 并不保证刚好对应一个完整 SSE Event。
   */
  private buffer = ''


  /**
   * 向 Parser 中追加一段网络数据。
   *
   * @param chunk reader.read() 后解码得到的字符串
   * @returns 当前已经能够解析出的完整 AgentEvent
   */
  push(chunk: string): AgentEvent[] {

    /**
     * SSE 在不同环境下可能出现：
     *
     * \r\n
     *
     * 或：
     *
     * \n
     *
     * 这里统一转换成 \n，
     * 后面的处理逻辑就简单很多。
     */
    const normalizedChunk = chunk.replace(/\r\n/g, '\n')

    /**
     * 新数据不能直接解析，
     * 必须先拼接到上一次剩余的数据后面。
     */
    this.buffer += normalizedChunk


    const events: AgentEvent[] = []


    /**
     * 标准 SSE：
     *
     * event: tool_start
     * data: {...}
     *
     * event: tool_end
     * data: {...}
     *
     * 两个 Event 之间使用空行分隔，
     * 所以这里寻找：
     *
     * \n\n
     */
    let separatorIndex = this.buffer.indexOf('\n\n')


    /**
     * buffer 中可能一次包含多个完整 SSE Event，
     * 所以这里使用 while，而不是 if。
     */
    while (separatorIndex >= 0) {

      /**
       * 取出一个完整 SSE Frame。
       *
       * 例如：
       *
       * event: tool_start
       * data: {"eventType":"tool_start", ...}
       */
      const frame = this.buffer.slice(
          0,
          separatorIndex
      )


      /**
       * 已经解析过的部分从 buffer 删除。
       *
       * +2 是为了跳过：
       *
       * \n\n
       */
      this.buffer = this.buffer.slice(
          separatorIndex + 2
      )


      /**
       * 单独解析当前 Frame。
       *
       * 一个 Frame：
       *
       * 有可能产生 AgentEvent，
       * 也有可能只是空数据、注释、心跳。
       */
      const event = this.parseFrame(frame)

      if (event) {
        events.push(event)
      }


      /**
       * 继续看看 buffer 中是否还有完整 Frame。
       */
      separatorIndex = this.buffer.indexOf('\n\n')
    }


    return events
  }


  /**
   * 解析一个完整 SSE Frame。
   *
   * 标准 SSE 可能是：
   *
   * event: tool_start
   * data: {"eventType":"tool_start"}
   *
   * 我们当前真正需要的是 data 字段。
   *
   * 因为后端已经把 eventType 放在 JSON 内部：
   *
   * {
   *   "eventType": "tool_start"
   * }
   *
   * 所以这里暂时不依赖外层：
   *
   * event: tool_start
   */
  private parseFrame(frame: string): AgentEvent | null {

    /**
     * SSE 允许 data 出现多行：
     *
     * data: line1
     * data: line2
     *
     * 因此不能只取第一行。
     */
    const dataLines = frame
        .split('\n')
        .filter(line => line.startsWith('data:'))


    /**
     * 例如 SSE 心跳可能是：
     *
     * : ping
     *
     * 没有 data，
     * 这种情况下直接忽略。
     */
    if (dataLines.length === 0) {
      return null
    }


    /**
     * 去掉：
     *
     * data:
     *
     * 把真正 JSON 内容重新拼起来。
     */
    const jsonText = dataLines
        .map(line => line.slice(5).trimStart())
        .join('\n')


    /**
     * 理论上空 data 没有业务意义。
     */
    if (!jsonText.trim()) {
      return null
    }


    try {

      /**
       * 后端发送的是 AgentEvent JSON：
       *
       * {
       *   "eventId": "...",
       *   "requestId": "...",
       *   "conversationId": "...",
       *   "eventType": "tool_start",
       *   ...
       * }
       */
      return JSON.parse(jsonText) as AgentEvent

    } catch (error) {

      /**
       * 当前阶段我们不希望：
       *
       * 一条坏 Event
       *
       * 导致：
       *
       * 整个 SSE 流立即中断。
       *
       * 所以先输出错误日志，然后忽略当前 Frame。
       *
       * 后续生产版本可以进一步接入：
       *
       * 日志平台
       * 前端监控
       * Sentry 等。
       */
      console.error(
          '[SseParser] AgentEvent JSON 解析失败',
          {
            frame,
            jsonText,
            error
          }
      )

      return null
    }
  }


  /**
   * 清空 Parser 内部状态。
   *
   * 当前一次请求一个 SseParser，
   * 正常情况下不一定需要手工调用。
   *
   * 但是提供 reset() 后，
   * Parser 本身的职责更加完整，
   * 后续如果做断线重连时也可以复用。
   */
  reset(): void {
    this.buffer = ''
  }
}