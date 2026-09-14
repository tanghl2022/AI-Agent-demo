/**
 * V6.3 Agent 执行轨迹类型定义
 *
 * 这里定义的不是后端协议，
 * 而是专门给页面展示使用的 ViewModel。
 *
 * 数据来源：
 *
 * AgentEvent
 *    ↓
 * agentExecution.ts
 *    ↓
 * AgentExecutionItem
 *    ↓
 * AgentTimeline.vue
 */


/**
 * 执行轨迹节点类型。
 *
 * 注意：
 * 这里和后端 eventType 不完全一样。
 *
 * 后端 eventType 是事件：
 *
 * tool_start
 * tool_end
 *
 * 前端这里表达的是：
 *
 * “这是一个 Tool 执行节点”
 *
 * 所以统一叫 TOOL。
 */
export type AgentExecutionType =
    | 'AGENT'
    | 'INTENT'
    | 'VALIDATION'
    | 'ROUTE'
    | 'TOOL'
    | 'WORKFLOW'
    | 'APPROVAL'
    | 'RETRY'
    | 'ERROR'
    | 'DONE'


/**
 * 页面展示状态。
 */
export type AgentExecutionStatus =
    | 'PENDING'
    | 'RUNNING'
    | 'SUCCESS'
    | 'WAITING'
    | 'FAILED'


/**
 * Agent 执行轨迹中的一个节点。
 *
 * 例如：
 *
 * Agent Start
 *
 * Intent Recognition
 *
 * Parameter Validation
 *
 * query_stock
 *
 * Human Approval
 */
export interface AgentExecutionItem {

  /**
   * 前端轨迹节点 ID。
   *
   * 用来：
   *
   * Vue v-for key
   * 查找并更新 tool_start → tool_end
   */
  id: string

  /**
   * 当前执行节点类型。
   */
  type: AgentExecutionType

  /**
   * 页面显示名称。
   *
   * 例如：
   *
   * Agent Start
   * 意图识别
   * 参数校验
   * 库存查询
   * 人工审批
   */
  title: string

  /**
   * 当前状态。
   */
  status: AgentExecutionStatus

  /**
   * 一句简短说明。
   *
   * 例如：
   *
   * 识别结果：QUERY_STOCK
   *
   * 正在查询 MAT001 库存
   */
  description?: string

  /**
   * Graph Node 名称。
   *
   * 例如：
   *
   * intent_recognition
   * query_stock
   */
  node?: string | null

  /**
   * 后端 Event sequence。
   *
   * 用于排序和调试。
   */
  sequence?: number

  /**
   * 开始时间。
   */
  startTime?: string

  /**
   * 结束时间。
   */
  endTime?: string

  /**
   * 执行耗时。
   */
  durationMs?: number

  /**
   * Tool 名称。
   */
  toolName?: string

  /**
   * Tool 输入参数。
   */
  toolArgs?: unknown

  /**
   * Tool 执行结果摘要。
   */
  toolResult?: unknown

  /**
   * 当前意图。
   */
  intent?: string

  /**
   * Router 结果。
   */
  route?: string

  /**
   * Workflow ID。
   */
  workflowInstanceId?: string | null

  /**
   * 错误信息。
   */
  errorMessage?: string

  /**
   * 保留原始数据。
   *
   * 后续 Debug 时非常方便。
   */
  rawData?: unknown
}