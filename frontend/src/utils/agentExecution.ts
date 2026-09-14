import type {
  AgentEvent,
  ApprovalRequiredEventData,
  BusinessFailedEventData,
  DoneEventData,
  IntentResultEventData,
  ParameterValidationEventData,
  RetryEventData,
  RouteEventData,
  SystemFailedEventData,
  ToolEndEventData,
  ToolStartEventData,
  WorkflowStartEventData
} from '../types/agent'

import type {
  AgentExecutionItem,
  AgentExecutionStatus
} from '../types/execution'


/**
 * 根据后端 AgentEvent，
 * 更新前端执行轨迹。
 *
 * 注意：
 *
 * 这里会直接修改 items 数组。
 *
 * 因为在 Vue 中 items 通常是 reactive/ref 管理的数据，
 * 修改后页面会自动刷新。
 */
export function applyAgentEvent(
    items: AgentExecutionItem[],
    event: AgentEvent
): void {

  switch (event.eventType) {

    case 'agent_start':
      handleAgentStart(items, event)
      break

    case 'intent_start':
      handleIntentStart(items, event)
      break

    case 'intent_result':
      handleIntentResult(items, event)
      break

    case 'parameter_validation':
      handleParameterValidation(items, event)
      break

    case 'route':
      handleRoute(items, event)
      break

    case 'tool_start':
      handleToolStart(items, event)
      break

    case 'tool_end':
      handleToolEnd(items, event)
      break

    case 'workflow_start':
      handleWorkflowStart(items, event)
      break

    case 'approval_required':
      handleApprovalRequired(items, event)
      break

    case 'approval_result':
      handleApprovalResult(items, event)
      break

    case 'retry':
      handleRetry(items, event)
      break

    case 'business_failed':
      handleBusinessFailed(items, event)
      break

    case 'system_failed':
      handleSystemFailed(items, event)
      break

    case 'done':
      handleDone(items, event)
      break

      /**
       * token 暂时不进入执行轨迹。
       *
       * token 后面用于左侧聊天内容流式输出。
       *
       * 如果每一个 token 都放进右侧 Timeline，
       * 页面会产生大量无意义节点。
       */
    case 'token':
      break

    default:
      console.warn(
          '[agentExecution] 未处理的 AgentEvent',
          event
      )
  }
}


/**
 * Agent 启动。
 */
function handleAgentStart(
    items: AgentExecutionItem[],
    event: AgentEvent
): void {

  items.push({
    id: buildEventItemId(event),
    type: 'AGENT',
    title: 'Agent 开始执行',
    status: 'RUNNING',
    description: '开始处理当前用户请求',
    node: event.node,
    sequence: event.sequence,
    startTime: event.timestamp,
    rawData: event.data
  })
}


/**
 * 意图识别开始。
 */
function handleIntentStart(
    items: AgentExecutionItem[],
    event: AgentEvent
): void {

  items.push({
    id: buildEventItemId(event),
    type: 'INTENT',
    title: '意图识别',
    status: 'RUNNING',
    description: '正在分析用户请求的业务意图',
    node: event.node,
    sequence: event.sequence,
    startTime: event.timestamp,
    rawData: event.data
  })
}


/**
 * 意图识别完成。
 *
 * 这里不是新增节点，
 * 而是找到之前：
 *
 * intent_start
 *
 * 创建的 INTENT 节点，然后更新它。
 */
function handleIntentResult(
    items: AgentExecutionItem[],
    event: AgentEvent
): void {

  const data = event.data as IntentResultEventData

  const item = findLatestRunningItem(
      items,
      'INTENT'
  )

  if (!item) {

    /**
     * 如果因为网络、刷新等原因没有收到 intent_start，
     * 仍然允许创建一个完整节点。
     */
    items.push({
      id: buildEventItemId(event),
      type: 'INTENT',
      title: '意图识别',
      status: 'SUCCESS',
      description: buildIntentDescription(data),
      node: event.node,
      sequence: event.sequence,
      endTime: event.timestamp,
      intent: data.intent,
      rawData: event.data
    })

    return
  }


  item.status = 'SUCCESS'
  item.endTime = event.timestamp
  item.intent = data.intent
  item.description = buildIntentDescription(data)
  item.rawData = event.data

  updateDuration(item)
}


/**
 * 参数校验。
 *
 * 当前后端通常只有一个：
 *
 * parameter_validation
 *
 * 没有：
 *
 * parameter_validation_start
 * parameter_validation_end
 *
 * 所以前端直接作为一个完成事件展示。
 */
function handleParameterValidation(
    items: AgentExecutionItem[],
    event: AgentEvent
): void {

  const data = event.data as ParameterValidationEventData

  const valid = data.valid !== false

  items.push({
    id: buildEventItemId(event),
    type: 'VALIDATION',
    title: '参数校验',
    status: valid ? 'SUCCESS' : 'WAITING',
    description: buildValidationDescription(data),
    node: event.node,
    sequence: event.sequence,
    startTime: event.timestamp,
    endTime: event.timestamp,
    rawData: event.data
  })
}


/**
 * Router。
 */
function handleRoute(
    items: AgentExecutionItem[],
    event: AgentEvent
): void {

  const data = event.data as RouteEventData

  items.push({
    id: buildEventItemId(event),
    type: 'ROUTE',
    title: 'Agent 路由',
    status: 'SUCCESS',
    description: data.route
        ? `路由到：${data.route}`
        : '路由完成',
    node: event.node,
    sequence: event.sequence,
    startTime: event.timestamp,
    endTime: event.timestamp,
    route: data.route,
    intent: data.intent,
    rawData: event.data
  })
}


/**
 * Tool 开始执行。
 */
function handleToolStart(
    items: AgentExecutionItem[],
    event: AgentEvent
): void {

  const data = event.data as ToolStartEventData

  items.push({
    /**
     * Tool 使用特殊 ID。
     *
     * 后面的 tool_end 必须能找到这个节点。
     */
    id: buildToolItemId(
        event,
        data.toolName
    ),

    type: 'TOOL',

    title: getToolTitle(data.toolName),

    status: 'RUNNING',

    description: buildToolStartDescription(data),

    node: event.node,

    sequence: event.sequence,

    startTime: event.timestamp,

    toolName: data.toolName,

    toolArgs: data.args,

    rawData: event.data
  })
}


/**
 * Tool 执行完成。
 */
function handleToolEnd(
    items: AgentExecutionItem[],
    event: AgentEvent
): void {

  const data = event.data as ToolEndEventData


  /**
   * 优先通过 toolName 找到最近运行中的 Tool。
   */
  const item = findRunningTool(
      items,
      data.toolName
  )


  /**
   * 如果没有收到对应 tool_start，
   * 也不能把 tool_end 丢掉。
   */
  if (!item) {

    items.push({
      id: buildToolItemId(
          event,
          data.toolName
      ),

      type: 'TOOL',

      title: getToolTitle(data.toolName),

      status:
          data.success === false
              ? 'FAILED'
              : 'SUCCESS',

      description:
          data.summary ||
          'Tool 执行完成',

      node: event.node,

      sequence: event.sequence,

      endTime: event.timestamp,

      durationMs: data.durationMs,

      toolName: data.toolName,

      toolResult: getToolResult(data),

      rawData: event.data
    })

    return
  }


  item.status =
      data.success === false
          ? 'FAILED'
          : 'SUCCESS'

  item.endTime = event.timestamp

  item.durationMs =
      data.durationMs ??
      calculateDuration(
          item.startTime,
          event.timestamp
      )

  item.toolResult = getToolResult(data)

  item.description =
      data.summary ||
      buildToolEndDescription(data)

  item.rawData = event.data
}


/**
 * Workflow 开始。
 */
function handleWorkflowStart(
    items: AgentExecutionItem[],
    event: AgentEvent
): void {

  const data = event.data as WorkflowStartEventData

  items.push({
    id: buildEventItemId(event),
    type: 'WORKFLOW',
    title: '业务工作流',
    status: 'RUNNING',
    description: data.workflowType
        ? `启动工作流：${data.workflowType}`
        : '业务工作流开始执行',
    node: event.node,
    sequence: event.sequence,
    startTime: event.timestamp,
    workflowInstanceId:
    event.workflowInstanceId,
    rawData: event.data
  })
}


/**
 * 需要人工审批。
 */
function handleApprovalRequired(
    items: AgentExecutionItem[],
    event: AgentEvent
): void {

  const data =
      event.data as ApprovalRequiredEventData


  /**
   * Workflow 到人工审批时，
   * 它不是失败，
   * 而是正常暂停。
   */
  const workflow =
      findLatestRunningItem(
          items,
          'WORKFLOW'
      )


  if (workflow) {
    workflow.status = 'WAITING'
    workflow.description = '工作流等待人工审批'
  }


  items.push({
    id: buildEventItemId(event),
    type: 'APPROVAL',
    title: '人工审批',
    status: 'WAITING',
    description:
        data.message ||
        '等待有权限的业务人员审批',
    node: event.node,
    sequence: event.sequence,
    startTime: event.timestamp,
    workflowInstanceId:
    event.workflowInstanceId,
    rawData: event.data
  })
}


/**
 * 人工审批结果。
 */
function handleApprovalResult(
    items: AgentExecutionItem[],
    event: AgentEvent
): void {

  const data = event.data as {
    approved?: boolean
    approver?: string
    comment?: string
  }


  const approval =
      findLatestWaitingItem(
          items,
          'APPROVAL'
      )


  if (!approval) {
    return
  }


  approval.status =
      data.approved
          ? 'SUCCESS'
          : 'FAILED'

  approval.endTime =
      event.timestamp

  approval.description =
      data.approved
          ? `审批通过${data.approver ? `：${data.approver}` : ''}`
          : `审批拒绝${data.comment ? `：${data.comment}` : ''}`

  updateDuration(approval)
}


/**
 * V6.4 Retry。
 *
 * V6.3 先做好前端模型兼容，
 * 后端真正产生 retry 事件后可以直接展示。
 */
function handleRetry(
    items: AgentExecutionItem[],
    event: AgentEvent
): void {

  const data = event.data as RetryEventData

  items.push({
    id: buildEventItemId(event),
    type: 'RETRY',
    title: '系统重试',
    status: 'RUNNING',
    description:
        `第 ${data.attempt ?? '?'} 次重试` +
        `${data.reason ? `：${data.reason}` : ''}`,
    node: event.node,
    sequence: event.sequence,
    startTime: event.timestamp,
    rawData: event.data
  })
}


/**
 * 业务失败。
 *
 * 注意：
 *
 * BUSINESS_FAILED
 *
 * 和：
 *
 * SYSTEM_FAILED
 *
 * 必须区分。
 */
function handleBusinessFailed(
    items: AgentExecutionItem[],
    event: AgentEvent
): void {

  const data =
      event.data as BusinessFailedEventData

  items.push({
    id: buildEventItemId(event),
    type: 'ERROR',
    title: '业务执行失败',
    status: 'FAILED',
    description: data.message,
    node: event.node,
    sequence: event.sequence,
    startTime: event.timestamp,
    endTime: event.timestamp,
    errorMessage: data.message,
    rawData: event.data
  })
}


/**
 * 系统异常。
 */
function handleSystemFailed(
    items: AgentExecutionItem[],
    event: AgentEvent
): void {

  const data =
      event.data as SystemFailedEventData

  items.push({
    id: buildEventItemId(event),
    type: 'ERROR',
    title: '系统执行异常',
    status: 'FAILED',
    description: data.message,
    node: event.node,
    sequence: event.sequence,
    startTime: event.timestamp,
    endTime: event.timestamp,
    errorMessage: data.message,
    rawData: event.data
  })
}


/**
 * 当前一次 Agent 请求结束。
 */
function handleDone(
    items: AgentExecutionItem[],
    event: AgentEvent
): void {

  const data = event.data as DoneEventData


  /**
   * Agent Start 节点收尾。
   */
  const agentItem =
      findLatestRunningItem(
          items,
          'AGENT'
      )


  if (agentItem) {

    agentItem.status =
        normalizeDoneStatus(event.status)

    agentItem.endTime =
        event.timestamp

    agentItem.description =
        data.answer ||
        'Agent 请求处理完成'

    updateDuration(agentItem)
  }


  /**
   * 再添加最终完成节点。
   *
   * 这样 Timeline 最后一项非常直观。
   */
  items.push({
    id: buildEventItemId(event),
    type: 'DONE',
    title: '执行结束',
    status:
        normalizeDoneStatus(event.status),
    description:
        data.answer ||
        '本次请求处理完成',
    node: event.node,
    sequence: event.sequence,
    startTime: event.timestamp,
    endTime: event.timestamp,
    intent: data.intent,
    workflowInstanceId:
    event.workflowInstanceId,
    rawData: event.data
  })
}


/* ============================================================
 * 查询函数
 * ============================================================ */


/**
 * 找最近一个指定类型、
 * 并且还处于 RUNNING 状态的节点。
 */
function findLatestRunningItem(
    items: AgentExecutionItem[],
    type: AgentExecutionItem['type']
): AgentExecutionItem | undefined {

  return [...items]
      .reverse()
      .find(
          item =>
              item.type === type &&
              item.status === 'RUNNING'
      )
}


/**
 * 找 WAITING 状态节点。
 */
function findLatestWaitingItem(
    items: AgentExecutionItem[],
    type: AgentExecutionItem['type']
): AgentExecutionItem | undefined {

  return [...items]
      .reverse()
      .find(
          item =>
              item.type === type &&
              item.status === 'WAITING'
      )
}


/**
 * 找运行中的 Tool。
 */
function findRunningTool(
    items: AgentExecutionItem[],
    toolName?: string
): AgentExecutionItem | undefined {

  return [...items]
      .reverse()
      .find(item => {

        if (
            item.type !== 'TOOL' ||
            item.status !== 'RUNNING'
        ) {
          return false
        }

        /**
         * 如果后端没有 toolName，
         * 就取最近运行中的 Tool。
         */
        if (!toolName) {
          return true
        }

        return item.toolName === toolName
      })
}


/* ============================================================
 * 文本构造函数
 * ============================================================ */


function buildIntentDescription(
    data: IntentResultEventData
): string {

  if (!data.intent) {
    return '意图识别完成'
  }

  let text =
      `识别结果：${data.intent}`

  if (data.materialCode) {
    text += `，物料：${data.materialCode}`
  }

  if (data.quantity !== null &&
      data.quantity !== undefined) {

    text += `，数量：${data.quantity}`
  }

  return text
}


function buildValidationDescription(
    data: ParameterValidationEventData
): string {

  if (
      data.missingParameters &&
      data.missingParameters.length > 0
  ) {

    return (
        '缺少参数：' +
        data.missingParameters.join(', ')
    )
  }


  return '业务参数校验通过'
}


function buildToolStartDescription(
    data: ToolStartEventData
): string {

  if (data.toolName === 'query_stock') {

    const args =
        data.args as
            | { materialCode?: string }
            | undefined

    if (args?.materialCode) {
      return `正在查询 ${args.materialCode} 库存`
    }
  }


  return data.toolName
      ? `正在调用 Tool：${data.toolName}`
      : '正在调用业务 Tool'
}


function buildToolEndDescription(
    data: ToolEndEventData
): string {

  if (data.availableQty !== undefined) {

    return (
        `库存查询完成，可用库存：` +
        `${data.availableQty}`
    )
  }


  return 'Tool 执行完成'
}


/**
 * 把查询结果整理成一个对象，
 * 方便 Timeline 后面展开显示。
 */
function getToolResult(
    data: ToolEndEventData
): unknown {

  if (
      data.materialCode !== undefined ||
      data.totalQty !== undefined ||
      data.availableQty !== undefined
  ) {

    return {
      materialCode: data.materialCode,
      totalQty: data.totalQty,
      reservedQty: data.reservedQty,
      frozenQty: data.frozenQty,
      availableQty: data.availableQty
    }
  }


  return data.output
}


/**
 * 把技术 Tool Name 转成用户更容易看的名称。
 */
function getToolTitle(
    toolName?: string
): string {

  switch (toolName) {

    case 'query_stock':
      return '库存查询'

    case 'query_location':
      return '库位查询'

    default:
      return toolName
          ? `Tool：${toolName}`
          : 'Tool 调用'
  }
}


/* ============================================================
 * 状态 / ID / 时间工具函数
 * ============================================================ */


function normalizeDoneStatus(
    status?: string | null
): AgentExecutionStatus {

  switch (status) {

    case 'SUCCESS':
      return 'SUCCESS'

    case 'WAITING_APPROVAL':
    case 'CLARIFICATION_REQUIRED':
      return 'WAITING'

    case 'BUSINESS_FAILED':
    case 'SYSTEM_FAILED':
    case 'FAILED':
      return 'FAILED'

    default:
      return 'SUCCESS'
  }
}


/**
 * 普通 Event Item ID。
 */
function buildEventItemId(
    event: AgentEvent
): string {

  return (
      `${event.requestId}-` +
      `${event.sequence}-` +
      `${event.eventType}`
  )
}


/**
 * Tool Item ID。
 *
 * Tool Start / End 不要求 ID 完全相同，
 * 因为 tool_end 是通过 findRunningTool() 找节点更新。
 */
function buildToolItemId(
    event: AgentEvent,
    toolName?: string
): string {

  return (
      `${event.requestId}-tool-` +
      `${toolName ?? event.sequence}`
  )
}


/**
 * 如果后端没有返回 durationMs，
 * 前端可以使用时间戳简单计算。
 */
function calculateDuration(
    startTime?: string,
    endTime?: string
): number | undefined {

  if (!startTime || !endTime) {
    return undefined
  }

  const start =
      new Date(startTime).getTime()

  const end =
      new Date(endTime).getTime()

  if (
      Number.isNaN(start) ||
      Number.isNaN(end)
  ) {
    return undefined
  }

  return Math.max(
      0,
      end - start
  )
}


/**
 * 更新一个节点的 durationMs。
 */
function updateDuration(
    item: AgentExecutionItem
): void {

  item.durationMs =
      calculateDuration(
          item.startTime,
          item.endTime
      )
}