<template>
  <main class="app-page">

    <!-- ======================================================
         顶部标题
         ====================================================== -->
    <header class="app-header">

      <div>
        <h1>WMS Agent Console</h1>

        <p>
          LangGraph + SSE + Tool Calling + Workflow + Checkpoint
        </p>
      </div>


      <!-- 当前会话信息 -->
      <div class="conversation-panel">

        <div class="conversation-label">
          Conversation ID
        </div>

        <div class="conversation-row">

          <input
              v-model="conversationId"
              class="conversation-input"
          />

          <button
              class="secondary-button"
              :disabled="loading"
              @click="newConversation"
          >
            新会话
          </button>

        </div>

      </div>

    </header>


    <!-- ======================================================
         主体区域
         ====================================================== -->
    <section class="workspace">

      <!-- ====================================================
           左侧：聊天
           ==================================================== -->
      <section class="chat-panel">

        <div class="panel-header">

          <div>
            <div class="panel-title">
              WMS 智能助手
            </div>

            <div class="panel-subtitle">
              使用自然语言查询库存、库位或发起业务工作流
            </div>
          </div>

          <span class="connection-status">
            SSE
          </span>

        </div>


        <!-- 消息区域 -->
        <div class="messages">

          <!-- 空状态 -->
          <div
              v-if="messages.length === 0"
              class="empty-chat"
          >

            <div class="empty-title">
              开始一个 WMS Agent 会话
            </div>

            <div class="empty-description">
              你可以尝试：
            </div>

            <button
                class="example-button"
                @click="fillExample('查询 MAT001 的库存')"
            >
              查询 MAT001 的库存
            </button>

            <button
                class="example-button"
                @click="fillExample('查询 MAT001 的库位')"
            >
              查询 MAT001 的库位
            </button>

            <button
                class="example-button"
                @click="fillExample('帮我冻结 MAT001')"
            >
              帮我冻结 MAT001
            </button>

          </div>


          <!-- 对话记录 -->
          <article
              v-for="message in messages"
              :key="message.id"
              :class="[
              'message',
              message.role
            ]"
          >

            <div class="message-role">
              {{ message.role === 'user'
                ? '用户'
                : 'WMS Agent'
              }}
            </div>


            <div class="message-body">

              <!-- Agent 状态 -->
              <div
                  v-if="
                  message.role === 'assistant' &&
                  message.status
                "
                  class="message-status"
              >
                {{ message.status }}
              </div>


              <!-- Agent / 用户内容 -->
              <div
                  v-if="message.content"
                  class="message-content"
              >
                {{ message.content }}
              </div>


              <!-- Agent 还没产生 answer 时 -->
              <div
                  v-else-if="
                  message.role === 'assistant' &&
                  message.streaming
                "
                  class="generating"
              >
                <span class="loading-dot" />
                Agent 正在处理...
              </div>

            </div>

          </article>

        </div>


        <!-- ==================================================
             输入区域
             ================================================== -->
        <div class="composer">

          <textarea
              v-model="input"
              class="composer-input"
              placeholder="例如：查询 MAT001 的库存"
              rows="4"
              @keydown.ctrl.enter.prevent="send"
          />


          <div class="composer-footer">

            <div class="composer-tip">
              Ctrl + Enter 发送
            </div>

            <button
                class="primary-button"
                :disabled="
                loading ||
                !input.trim()
              "
                @click="send"
            >
              {{ loading
                ? 'Agent 执行中...'
                : '发送'
              }}
            </button>

          </div>

        </div>

      </section>


      <!-- ====================================================
           右侧：执行轨迹
           ==================================================== -->
      <section class="execution-panel">

        <div class="panel-header">
          <div>
            <div class="panel-title">
              Agent 执行轨迹
            </div>
            <div class="panel-subtitle">
              观察 Intent、Router、Tool、Workflow 与 Approval
            </div>
          </div>
          <button
              class="clear-button"
              :disabled="executionItems.length === 0"
              @click="clearExecution"
          >
            清空
          </button>

        </div>

        <!-- 没有轨迹 -->
        <div
            v-if="executionItems.length === 0"
            class="execution-empty"
        >
          发送一条消息后，这里会实时显示 Agent 执行过程。
        </div>


        <!-- Timeline -->
        <AgentTimeline
            v-else
            :items="executionItems"
        />

      </section>

    </section>


    <!-- ======================================================
         底部运行信息
         ====================================================== -->
    <footer class="runtime-footer">

      <span>
        Conversation:
        <strong>{{ conversationId }}</strong>
      </span>

      <span v-if="currentRequestId">
        Request:
        <strong>{{ currentRequestId }}</strong>
      </span>

      <span v-if="currentWorkflowInstanceId">
        Workflow:
        <strong>{{ currentWorkflowInstanceId }}</strong>
      </span>

    </footer>

  </main>
</template>


<script setup lang="ts">

import {
  ref
} from 'vue'

import AgentTimeline from './components/AgentTimeline.vue'

import {
  streamAgentChat
} from './services/agent'

import type {
  AgentEvent,
  BusinessFailedEventData,
  DoneEventData,
  SystemFailedEventData,
  TokenEventData
} from './types/agent'

import type {
  ChatMessage
} from './types/chat'

import type {
  AgentExecutionItem
} from './types/execution'

import {
  applyAgentEvent
} from './utils/agentExecution'


/* ============================================================
 * 页面状态
 * ============================================================ */


/**
 * 对话消息。
 */
const messages = ref<ChatMessage[]>([])


/**
 * 输入框。
 */
const input = ref('')


/**
 * 当前是否正在执行 Agent。
 *
 * 当前 Demo：
 *
 * 同一个页面同一时间只允许一个 Agent 请求。
 *
 * 后面如果实现多任务并行，
 * 可以进一步改成 request 级状态。
 */
const loading = ref(false)


/**
 * Main Agent 会话 ID。
 *
 * 对应：
 *
 * LangGraph Main Graph
 *
 * config = {
 *   configurable: {
 *     thread_id: conversationId
 *   }
 * }
 */
const conversationId = ref(
    createConversationId()
)


/**
 * 当前右侧显示的执行轨迹。
 *
 * 当前设计：
 *
 * 只显示“最近一次 Agent 请求”的执行过程。
 *
 * 这样右侧不会因为多轮对话无限堆积。
 */
const executionItems =
    ref<AgentExecutionItem[]>([])


/**
 * 当前一次 SSE Request ID。
 *
 * 用于调试。
 */
const currentRequestId =
    ref<string | null>(null)


/**
 * 当前业务 Workflow 实例 ID。
 *
 * 普通查询一般为空。
 *
 * 冻结库存时会存在。
 */
const currentWorkflowInstanceId =
    ref<string | null>(null)



/* ============================================================
 * ID
 * ============================================================ */


/**
 * 创建前端消息 ID。
 */
function createMessageId(): string {

  return crypto.randomUUID()
}


/**
 * 创建一个新的 conversationId。
 */
function createConversationId(): string {

  return `wms-${Date.now()}-${crypto.randomUUID().slice(0, 8)}`
}



/* ============================================================
 * 会话控制
 * ============================================================ */


/**
 * 开启一个全新的 Agent 会话。
 *
 * 注意：
 *
 * 新 conversationId
 *
 * =
 *
 * 后端不会继续恢复之前 Main Graph Checkpoint。
 */
function newConversation(): void {

  if (loading.value) {
    return
  }


  conversationId.value =
      createConversationId()


  messages.value = []

  executionItems.value = []

  currentRequestId.value = null

  currentWorkflowInstanceId.value = null

  input.value = ''
}


/**
 * 清空右侧执行轨迹。
 *
 * 注意：
 *
 * 这里只清前端展示，
 * 不会删除 LangGraph Checkpoint。
 */
function clearExecution(): void {

  executionItems.value = []

  currentRequestId.value = null

  currentWorkflowInstanceId.value = null
}


/**
 * 示例问题快速填充。
 */
function fillExample(
    example: string
): void {

  input.value = example
}



/* ============================================================
 * AgentEvent 处理
 * ============================================================ */


/**
 * 每收到一个 SSE AgentEvent，
 * 都会进入这里一次。
 *
 * 这是 App.vue 中非常重要的方法。
 *
 * 可以把它理解成：
 *
 * SSE Event Dispatcher
 */
function handleAgentEvent(
    event: AgentEvent,
    assistant: ChatMessage
): void {

  /**
   * 保存当前请求 ID。
   *
   * 同一次请求中的所有 Event：
   *
   * requestId 应保持一致。
   */
  currentRequestId.value =
      event.requestId


  /**
   * 如果产生 Workflow，
   * 保存 workflowInstanceId。
   */
  if (event.workflowInstanceId) {

    currentWorkflowInstanceId.value =
        event.workflowInstanceId
  }


  /**
   * 第一件事：
   *
   * 所有可观察事件统一交给：
   *
   * AgentEvent
   *      ↓
   * applyAgentEvent()
   *      ↓
   * AgentExecutionItem[]
   *
   * 然后右侧 Timeline 自动刷新。
   */
  applyAgentEvent(
      executionItems.value,
      event
  )


  /**
   * 第二件事：
   *
   * 部分 Event 还需要影响左侧聊天区域。
   */
  switch (event.eventType) {


      /* --------------------------------------------------------
       * Agent 开始
       * -------------------------------------------------------- */

    case 'agent_start':

      assistant.status =
          'Agent 已开始执行'

      break


      /* --------------------------------------------------------
       * 意图识别
       * -------------------------------------------------------- */

    case 'intent_start':

      assistant.status =
          '正在识别业务意图...'

      break


    case 'intent_result':

      assistant.status =
          '意图识别完成'

      break


      /* --------------------------------------------------------
       * 参数校验
       * -------------------------------------------------------- */

    case 'parameter_validation':

      assistant.status =
          '正在校验业务参数'

      break


      /* --------------------------------------------------------
       * Router
       * -------------------------------------------------------- */

    case 'route':

      assistant.status =
          'Agent 已完成业务路由'

      break


      /* --------------------------------------------------------
       * Tool
       * -------------------------------------------------------- */

    case 'tool_start':

      assistant.status =
          '正在调用 WMS Tool...'

      break


    case 'tool_end':

      assistant.status =
          'WMS Tool 调用完成'

      break


      /* --------------------------------------------------------
       * Workflow
       * -------------------------------------------------------- */

    case 'workflow_start':

      assistant.status =
          '业务工作流已启动'

      break


    case 'approval_required':

      assistant.status =
          '工作流等待人工审批'

      break


    case 'approval_result':

      assistant.status =
          '人工审批已处理'

      break


      /* --------------------------------------------------------
       * Retry
       * -------------------------------------------------------- */

    case 'retry':

      assistant.status =
          '系统异常，正在重试...'

      break


      /* --------------------------------------------------------
       * Token
       * -------------------------------------------------------- */

    case 'token': {

      const data =
          event.data as TokenEventData


      /**
       * Token 不进入 Timeline。
       *
       * 它应该追加到左侧回答。
       */
      assistant.content +=
          data.content ?? ''

      assistant.status =
          'Agent 正在生成回答...'

      break
    }


      /* --------------------------------------------------------
       * Business Failed
       * -------------------------------------------------------- */

    case 'business_failed': {

      const data =
          event.data as BusinessFailedEventData


      assistant.streaming = false

      assistant.status =
          '业务执行失败'

      assistant.content =
          data.message ||
          '业务执行失败'

      break
    }


      /* --------------------------------------------------------
       * System Failed
       * -------------------------------------------------------- */

    case 'system_failed': {

      const data =
          event.data as SystemFailedEventData


      assistant.streaming = false

      assistant.status =
          '系统执行异常'

      assistant.content =
          data.message ||
          '系统执行异常'

      break
    }


      /* --------------------------------------------------------
       * Done
       * -------------------------------------------------------- */

    case 'done': {

      const data =
          event.data as DoneEventData


      assistant.streaming = false

      assistant.status =
          getDoneStatusText(
              event.status
          )


      /**
       * 当前如果后端没有发送 token，
       * 最终答案通常放在：
       *
       * done.data.answer
       *
       * 因此：
       *
       * 如果前面已经通过 token 生成内容，
       * 就不要重复覆盖；
       *
       * 如果没有 token，
       * 就使用最终 answer。
       */
      if (
          !assistant.content &&
          data.answer
      ) {

        assistant.content =
            data.answer
      }

      break
    }


    default:
      break
  }
}



/* ============================================================
 * Done 状态文字
 * ============================================================ */

function getDoneStatusText(
    status?: string | null
): string {

  switch (status) {

    case 'WAITING_APPROVAL':

      return '等待人工审批'


    case 'CLARIFICATION_REQUIRED':

      return '需要补充信息'


    case 'BUSINESS_FAILED':

      return '业务执行失败'


    case 'SYSTEM_FAILED':

      return '系统执行异常'


    case 'SUCCESS':

      return '执行完成'


    default:

      return 'Agent 执行结束'
  }
}



/* ============================================================
 * 发送消息
 * ============================================================ */

async function send(): Promise<void> {

  /**
   * trim：
   *
   * 去掉输入内容两端空格。
   */
  const question =
      input.value.trim()


  /**
   * 空消息不发送。
   */
  if (!question) {
    return
  }


  /**
   * 当前已有 Agent 在执行，
   * 暂时不允许重复发送。
   */
  if (loading.value) {
    return
  }


  /**
   * 创建用户消息。
   */
  const userMessage: ChatMessage = {

    id: createMessageId(),

    role: 'user',

    content: question
  }


  /**
   * 创建 Agent 消息占位。
   *
   * 请求刚发出去时：
   *
   * content 为空
   * streaming = true
   *
   * 页面会显示：
   *
   * Agent 正在处理...
   */
  const assistantMessage: ChatMessage = {

    id: createMessageId(),

    role: 'assistant',

    content: '',

    status: '正在连接 Agent...',

    streaming: true
  }


  /**
   * 添加到聊天记录。
   */
  messages.value.push(
      userMessage,
      assistantMessage
  )


  /**
   * 清空输入框。
   */
  input.value = ''


  /**
   * 每一次新的用户请求，
   * 右侧只显示本次执行链。
   */
  executionItems.value = []

  currentRequestId.value = null

  currentWorkflowInstanceId.value = null


  loading.value = true


  try {

    /**
     * 调用 SSE Agent API。
     */
    await streamAgentChat(
        {
        conversationId:
        conversationId.value,
          message: question},


        /**
         * 每收到一个 AgentEvent，
         * callback 就执行一次。
         */
        event => {

          handleAgentEvent(
              event,
              assistantMessage
          )
        }
    )


  } catch (error) {

    assistantMessage.streaming =
        false

    assistantMessage.status =
        '请求失败'


    assistantMessage.content =
        error instanceof Error
            ? error.message
            : 'Agent 请求发生未知异常'

  } finally {

    loading.value = false
  }
}

</script>


<style scoped>

/* ============================================================
   页面
   ============================================================ */

.app-page {
  min-height: 100vh;

  display: flex;
  flex-direction: column;

  background: #f3f4f6;

  color: #111827;
}


/* ============================================================
   Header
   ============================================================ */

.app-header {
  padding: 18px 24px;

  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;

  border-bottom: 1px solid #e5e7eb;

  background: #ffffff;
}

.app-header h1 {
  margin: 0;

  font-size: 22px;
}

.app-header p {
  margin: 4px 0 0;

  font-size: 12px;
  color: #6b7280;
}


.conversation-panel {
  min-width: 360px;
}

.conversation-label {
  margin-bottom: 5px;

  font-size: 11px;
  color: #6b7280;
}

.conversation-row {
  display: flex;
  gap: 8px;
}

.conversation-input {
  flex: 1;

  min-width: 0;

  padding: 8px 10px;

  border: 1px solid #d1d5db;
  border-radius: 8px;

  font-family:
      Consolas,
      Monaco,
      monospace;

  font-size: 12px;
}


/* ============================================================
   Workspace
   ============================================================ */

.workspace {
  flex: 1;

  min-height: 0;

  display: grid;

  grid-template-columns:
    minmax(0, 1fr)
    minmax(420px, 0.9fr);

  gap: 16px;

  padding: 16px 20px;
}


/* ============================================================
   Panel
   ============================================================ */

.chat-panel,
.execution-panel {
  min-height: 0;

  display: flex;
  flex-direction: column;

  overflow: hidden;

  border: 1px solid #e5e7eb;
  border-radius: 14px;

  background: #ffffff;
}

.panel-header {
  padding: 14px 16px;

  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;

  border-bottom: 1px solid #e5e7eb;
}

.panel-title {
  font-size: 15px;
  font-weight: 700;
}

.panel-subtitle {
  margin-top: 3px;

  font-size: 11px;
  color: #6b7280;
}

.connection-status {
  padding: 3px 8px;

  border-radius: 999px;

  background: #dcfce7;
  color: #15803d;

  font-size: 10px;
  font-weight: 700;
}


/* ============================================================
   Messages
   ============================================================ */

.messages {
  flex: 1;

  min-height: 0;

  overflow-y: auto;

  padding: 18px;
}

.message {
  margin-bottom: 18px;
}

.message-role {
  margin-bottom: 6px;

  font-size: 11px;
  font-weight: 600;

  color: #6b7280;
}

.message-body {
  max-width: 82%;

  padding: 12px 14px;

  border-radius: 12px;

  font-size: 14px;
  line-height: 1.7;
}

.message.user {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.message.user .message-body {
  background: #2563eb;
  color: #ffffff;
}

.message.assistant .message-body {
  background: #f3f4f6;
  color: #111827;
}

.message-status {
  margin-bottom: 6px;

  font-size: 11px;

  opacity: 0.7;
}

.message-content {
  white-space: pre-wrap;
  word-break: break-word;
}


/* ============================================================
   Empty chat
   ============================================================ */

.empty-chat {
  height: 100%;

  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;

  gap: 10px;

  color: #6b7280;
}

.empty-title {
  font-size: 18px;
  font-weight: 700;
  color: #111827;
}

.empty-description {
  font-size: 12px;
}

.example-button {
  min-width: 240px;

  padding: 8px 12px;

  border: 1px solid #d1d5db;
  border-radius: 8px;

  background: #ffffff;

  cursor: pointer;
}

.example-button:hover {
  background: #f9fafb;
}


/* ============================================================
   Generating
   ============================================================ */

.generating {
  display: flex;
  align-items: center;

  gap: 8px;

  color: #6b7280;
}

.loading-dot {
  width: 8px;
  height: 8px;

  border-radius: 50%;

  background: #2563eb;

  animation: pulse 1s infinite;
}


/* ============================================================
   Composer
   ============================================================ */

.composer {
  padding: 14px;

  border-top: 1px solid #e5e7eb;
}

.composer-input {
  width: 100%;

  box-sizing: border-box;

  resize: vertical;

  padding: 10px 12px;

  border: 1px solid #d1d5db;
  border-radius: 10px;

  font-family: inherit;
  font-size: 14px;

  outline: none;
}

.composer-input:focus {
  border-color: #2563eb;
}

.composer-footer {
  margin-top: 8px;

  display: flex;
  justify-content: space-between;
  align-items: center;
}

.composer-tip {
  font-size: 11px;
  color: #9ca3af;
}


/* ============================================================
   Execution
   ============================================================ */

.execution-panel {
  overflow-y: auto;
}

.execution-panel :deep(.timeline) {
  margin: 14px;
}

.execution-empty {
  flex: 1;

  display: flex;
  align-items: center;
  justify-content: center;

  padding: 32px;

  color: #9ca3af;

  font-size: 13px;
  text-align: center;
}


/* ============================================================
   Buttons
   ============================================================ */

.primary-button,
.secondary-button,
.clear-button {
  border: 0;
  border-radius: 8px;

  cursor: pointer;

  font-weight: 600;
}

.primary-button {
  padding: 9px 18px;

  background: #2563eb;
  color: #ffffff;
}

.secondary-button {
  padding: 8px 12px;

  border: 1px solid #d1d5db;

  background: #ffffff;
  color: #374151;
}

.clear-button {
  padding: 5px 9px;

  background: #f3f4f6;
  color: #6b7280;

  font-size: 11px;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}


/* ============================================================
   Runtime
   ============================================================ */

.runtime-footer {
  padding: 8px 20px;

  display: flex;
  flex-wrap: wrap;

  gap: 20px;

  border-top: 1px solid #e5e7eb;

  background: #ffffff;

  font-size: 10px;
  color: #6b7280;
}

.runtime-footer strong {
  font-family:
      Consolas,
      Monaco,
      monospace;

  color: #374151;
}


/* ============================================================
   Animation
   ============================================================ */

@keyframes pulse {

  0% {
    opacity: 0.3;
  }

  50% {
    opacity: 1;
  }

  100% {
    opacity: 0.3;
  }
}


/* ============================================================
   小屏幕
   ============================================================ */

@media (
max-width: 1100px
) {

  .app-header {
    align-items: stretch;
    flex-direction: column;
  }

  .conversation-panel {
    min-width: 0;
  }

  .workspace {
    grid-template-columns: 1fr;
  }

  .execution-panel {
    min-height: 500px;
  }
}

</style>