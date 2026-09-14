/**
 * V6.3 前端统一 Agent 事件定义
 *
 * 对应后端 V6.2：
 * wms_agent.events.event_types.AgentEventType
 *
 * 注意：
 * 这里的事件名称必须与后端完全一致。
 * 后端是小写，因此前端也使用小写。
 */
export type AgentEventType =
    | 'agent_start'
    | 'intent_start'
    | 'intent_result'
    | 'parameter_validation'
    | 'route'
    | 'tool_start'
    | 'tool_end'
    | 'workflow_start'
    | 'approval_required'
    | 'approval_result'
    | 'retry'
    | 'token'
    | 'business_failed'
    | 'system_failed'
    | 'done'


/**
 * 后端通过 SSE 返回的统一 AgentEvent。
 *
 * 可以把它理解成 Java 中的：
 *
 * class AgentEvent<T> {
 *     String eventId;
 *     String requestId;
 *     String conversationId;
 *     String workflowInstanceId;
 *     String eventType;
 *     String node;
 *     String status;
 *     Integer sequence;
 *     String timestamp;
 *     T data;
 * }
 */
export interface AgentEvent<T = unknown> {

  /**
   * 当前事件唯一 ID。
   *
   * 每产生一个 AgentEvent 都会生成新的 eventId。
   */
  eventId: string

  /**
   * 当前一次 HTTP / SSE 请求 ID。
   *
   * 一次发送消息：
   *
   * 查询 MAT001 库存
   *
   * 从 agent_start 到 done，
   * requestId 都应该保持一致。
   */
  requestId: string

  /**
   * Agent 会话 ID。
   *
   * 用来实现：
   * 多轮会话
   * LangGraph Main Graph Checkpoint
   *
   * 对应后端：
   *
   * config = {
   *   configurable: {
   *     thread_id: conversationId
   *   }
   * }
   */
  conversationId: string

  /**
   * 具体业务 Workflow 实例 ID。
   *
   * 普通库存查询可能没有这个值。
   *
   * 冻结库存流程会产生：
   *
   * workflowInstanceId
   *
   * 它和 conversationId 不是一个概念。
   */
  workflowInstanceId?: string | null

  /**
   * 当前事件类型。
   *
   * 例如：
   *
   * agent_start
   * intent_result
   * tool_start
   * approval_required
   */
  eventType: AgentEventType

  /**
   * 当前事件来自哪个 Graph Node。
   *
   * 例如：
   *
   * intent_recognition
   * query_stock
   * freeze_workflow
   */
  node?: string | null

  /**
   * 当前执行状态。
   *
   * 后端可能返回：
   *
   * RUNNING
   * SUCCESS
   * WAITING_APPROVAL
   * BUSINESS_FAILED
   * SYSTEM_FAILED
   */
  status?: string | null

  /**
   * 当前请求中的事件顺序。
   *
   * 例如：
   *
   * agent_start              sequence = 1
   * intent_start             sequence = 2
   * intent_result            sequence = 3
   * ...
   */
  sequence: number

  /**
   * 后端事件产生时间。
   */
  timestamp: string

  /**
   * 不同事件携带不同业务数据。
   *
   * 使用泛型 T，
   * 这样不同事件可以定义自己的 data 类型。
   */
  data: T
}


/* ============================================================
 * Agent 生命周期事件
 * ============================================================ */

/**
 * agent_start 的 data。
 */
export interface AgentStartEventData {

  /**
   * 用户本次输入内容。
   */
  message?: string
}


/* ============================================================
 * Intent 意图识别
 * ============================================================ */

/**
 * intent_start 目前通常不需要太多业务字段。
 *
 * 后续如果后端增加：
 * model
 * promptVersion
 * 等信息，也可以继续扩展。
 */
export interface IntentStartEventData {
  message?: string
}


/**
 * intent_result 的 data。
 */
export interface IntentResultEventData {

  /**
   * 识别出的业务意图。
   *
   * 例如：
   *
   * QUERY_STOCK
   * QUERY_LOCATION
   * FREEZE_INVENTORY
   * UNKNOWN
   */
  intent?: string

  /**
   * 识别出的物料编码。
   */
  materialCode?: string | null

  /**
   * 识别出的数量。
   */
  quantity?: number | null

  /**
   * 模型置信度。
   *
   * 当前后端如果没有返回，可以为空。
   */
  confidence?: number | null
}


/* ============================================================
 * 参数校验
 * ============================================================ */

/**
 * parameter_validation 的 data。
 */
export interface ParameterValidationEventData {

  /**
   * 当前参数是否完整。
   */
  valid?: boolean

  /**
   * 缺失参数。
   *
   * 例如：
   *
   * ["quantity"]
   */
  missingParameters?: string[]

  /**
   * 当前意图。
   */
  intent?: string

  materialCode?: string | null

  quantity?: number | null
}


/* ============================================================
 * Router
 * ============================================================ */

/**
 * route 的 data。
 */
export interface RouteEventData {

  /**
   * Router 最终选择的目标。
   *
   * 例如：
   *
   * query_stock
   * query_location
   * freeze_inventory
   * clarification
   * unknown
   */
  route?: string

  /**
   * 当前业务意图。
   */
  intent?: string
}


/* ============================================================
 * Tool Calling
 * ============================================================ */

/**
 * tool_start 的 data。
 */
export interface ToolStartEventData {

  /**
   * Tool 名称。
   *
   * 例如：
   *
   * query_stock
   * query_location
   */
  toolName?: string

  /**
   * Tool 调用参数。
   *
   * 例如：
   *
   * {
   *   materialCode: "MAT001"
   * }
   */
  args?: unknown
}


/**
 * tool_end 的 data。
 */
export interface ToolEndEventData {

  toolName?: string

  /**
   * Tool 是否成功。
   */
  success?: boolean

  /**
   * 调用耗时。
   */
  durationMs?: number

  /**
   * 返回结果摘要。
   */
  summary?: string

  /**
   * Tool 原始输出。
   *
   * 调试时比较有用。
   */
  output?: unknown

  /**
   * 以下字段用于库存查询时直接展示。
   *
   * 如果后端没有返回，
   * 这些字段可以为空。
   */
  materialCode?: string
  totalQty?: number
  reservedQty?: number
  frozenQty?: number
  availableQty?: number
}


/* ============================================================
 * Workflow
 * ============================================================ */

/**
 * workflow_start 的 data。
 */
export interface WorkflowStartEventData {

  /**
   * Workflow 类型。
   *
   * 例如：
   *
   * FREEZE_INVENTORY
   */
  workflowType?: string

  materialCode?: string | null

  quantity?: number | null
}


/**
 * approval_required 的 data。
 */
export interface ApprovalRequiredEventData {

  /**
   * 审批原因或说明。
   */
  message?: string

  materialCode?: string | null

  quantity?: number | null
}


/**
 * approval_result 的 data。
 */
export interface ApprovalResultEventData {

  approved?: boolean

  approver?: string

  comment?: string
}


/* ============================================================
 * Retry
 * V6.4 会真正使用
 * ============================================================ */

export interface RetryEventData {

  /**
   * 当前第几次重试。
   */
  attempt?: number

  /**
   * 最大重试次数。
   */
  maxAttempts?: number

  /**
   * 重试原因。
   */
  reason?: string

  /**
   * 下一次重试等待时间。
   */
  delayMs?: number
}


/* ============================================================
 * Token Streaming
 * ============================================================ */

export interface TokenEventData {

  /**
   * 当前一批 Token 内容。
   *
   * 你之前实现的 Token Batching，
   * 最终就会放到这里。
   */
  content: string
}


/* ============================================================
 * Failure
 * ============================================================ */

/**
 * business_failed：
 *
 * 业务失败，例如：
 *
 * 库存不足
 * 状态不允许
 *
 * 这类错误通常不应该自动重试。
 */
export interface BusinessFailedEventData {

  code?: string

  message: string
}


/**
 * system_failed：
 *
 * 系统失败，例如：
 *
 * Java WMS 服务连接失败
 * HTTP 超时
 * 数据库异常
 *
 * V6.4 会针对这种错误做重试。
 */
export interface SystemFailedEventData {

  code?: string

  message: string

  retryable?: boolean
}


/* ============================================================
 * Done
 * ============================================================ */

/**
 * done 是当前一次 Agent 请求的最终事件。
 */
export interface DoneEventData {

  /**
   * Agent 最终回答。
   *
   * 当前 V6.2 后端：
   *
   * data = {
   *   answer: "...",
   *   intent: "QUERY_STOCK"
   * }
   */
  answer?: string

  intent?: string

  /**
   * 整体执行耗时。
   *
   * 后端当前没有也没关系。
   */
  durationMs?: number
}