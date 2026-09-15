/**
 * 聊天消息角色。
 */
export type ChatRole =
    | 'user'
    | 'assistant'


/**
 * 左侧聊天区域使用的消息模型。
 *
 * 注意：
 *
 * Agent 执行轨迹已经独立到右侧，
 * 所以这里不再保存 executions。
 */
export interface ChatMessage {

  /**
   * 前端消息唯一 ID。
   */
  id: string

  /**
   * 消息角色。
   */
  role: ChatRole

  /**
   * 消息正文。
   */
  content: string

  /**
   * Agent 当前执行状态说明。
   */
  status?: string

  /**
   * 是否还在流式处理中。
   */
  streaming?: boolean
}