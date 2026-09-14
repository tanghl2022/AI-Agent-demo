<template>
  <!--
    没有执行轨迹时，不显示整个 Timeline。
  -->
  <div v-if="items.length" class="timeline">

    <!-- 标题区域 -->
    <div class="timeline-header">
      <div>
        <div class="timeline-title">
          Agent 执行过程
        </div>

        <div class="timeline-subtitle">
          实时展示意图识别、路由、Tool 与 Workflow 执行状态
        </div>
      </div>

      <!--
        这里显示当前已经产生多少个“页面执行节点”。

        注意：
        这个数量不一定等于 SSE Event 数量。

        例如：
        intent_start + intent_result
        最终只对应一个 INTENT 节点。
      -->
      <div class="timeline-count">
        {{ items.length }} 个节点
      </div>
    </div>


    <!-- 执行轨迹 -->
    <div class="timeline-list">

      <div
          v-for="(item, index) in items"
          :key="item.id"
          class="timeline-item"
      >

        <!-- 左边：时间线图标 -->
        <div class="timeline-marker">

          <span
              class="timeline-icon"
              :class="statusClass(item.status)"
          >
            {{ statusIcon(item.status) }}
          </span>

          <!--
            最后一个节点之后不再画连接线。
          -->
          <span
              v-if="index < items.length - 1"
              class="timeline-line"
          />
        </div>


        <!-- 右边：具体节点内容 -->
        <div
            class="timeline-content"
            :class="statusClass(item.status)"
        >

          <!-- 第一行：标题 + 状态 -->
          <div class="timeline-row">

            <div class="timeline-title-area">

              <!-- 节点类型标签 -->
              <span class="type-tag">
                {{ typeLabel(item.type) }}
              </span>

              <!-- 节点名称 -->
              <span class="item-title">
                {{ item.title }}
              </span>

            </div>


            <!-- 状态标签 -->
            <span
                class="status-tag"
                :class="statusClass(item.status)"
            >
              {{ statusLabel(item.status) }}
            </span>

          </div>


          <!-- 简要说明 -->
          <div
              v-if="item.description"
              class="description"
          >
            {{ item.description }}
          </div>


          <!-- =================================================
               Agent / Graph 基础信息
               ================================================= -->

          <div
              v-if="
              item.node ||
              item.sequence !== undefined ||
              item.durationMs !== undefined
            "
              class="meta-row"
          >

            <span v-if="item.node">
              Node:
              <strong>{{ item.node }}</strong>
            </span>

            <span v-if="item.sequence !== undefined">
              Sequence:
              <strong>{{ item.sequence }}</strong>
            </span>

            <span v-if="item.durationMs !== undefined">
              耗时:
              <strong>{{ item.durationMs }} ms</strong>
            </span>

          </div>


          <!-- =================================================
               Intent
               ================================================= -->

          <div
              v-if="item.intent"
              class="detail-box"
          >
            <div class="detail-label">
              Intent
            </div>

            <div class="detail-value code">
              {{ item.intent }}
            </div>
          </div>


          <!-- =================================================
               Router
               ================================================= -->

          <div
              v-if="item.route"
              class="detail-box"
          >
            <div class="detail-label">
              Route
            </div>

            <div class="detail-value code">
              {{ item.route }}
            </div>
          </div>


          <!-- =================================================
               Tool
               ================================================= -->

          <div
              v-if="item.toolName"
              class="detail-group"
          >

            <div class="detail-box">
              <div class="detail-label">
                Tool
              </div>

              <div class="detail-value code">
                {{ item.toolName }}
              </div>
            </div>


            <!-- Tool 参数 -->
            <details
                v-if="item.toolArgs !== undefined"
                class="details-panel"
            >
              <summary>
                查看 Tool 参数
              </summary>

              <pre>{{ formatJson(item.toolArgs) }}</pre>
            </details>


            <!-- Tool 返回结果 -->
            <details
                v-if="item.toolResult !== undefined"
                class="details-panel"
            >
              <summary>
                查看 Tool 返回结果
              </summary>

              <pre>{{ formatJson(item.toolResult) }}</pre>
            </details>

          </div>


          <!-- =================================================
               Workflow
               ================================================= -->

          <div
              v-if="item.workflowInstanceId"
              class="detail-box workflow-box"
          >
            <div class="detail-label">
              Workflow Instance ID
            </div>

            <div class="detail-value code break-all">
              {{ item.workflowInstanceId }}
            </div>
          </div>


          <!-- =================================================
               Error
               ================================================= -->

          <div
              v-if="item.errorMessage"
              class="error-box"
          >
            {{ item.errorMessage }}
          </div>


          <!-- =================================================
               原始数据
               调试使用
               ================================================= -->

          <details
              v-if="item.rawData !== undefined"
              class="details-panel raw-panel"
          >
            <summary>
              原始事件数据
            </summary>

            <pre>{{ formatJson(item.rawData) }}</pre>
          </details>


          <!-- RUNNING 动画 -->
          <div
              v-if="item.status === 'RUNNING'"
              class="running-tip"
          >
            <span class="loading-dot" />
            正在执行...
          </div>


          <!-- WAITING -->
          <div
              v-if="item.status === 'WAITING'"
              class="waiting-tip"
          >
            当前流程已暂停，等待后续输入或人工处理
          </div>

        </div>

      </div>

    </div>

  </div>
</template>


<script setup lang="ts">

import type {
  AgentExecutionItem,
  AgentExecutionStatus,
  AgentExecutionType
} from '../types/execution'


/**
 * 父组件传入：
 *
 * <AgentTimeline :items="message.executions" />
 *
 * Vue3 <script setup> 中：
 *
 * defineProps
 *
 * 可以理解成声明这个组件接收哪些参数。
 */
defineProps<{
  items: AgentExecutionItem[]
}>()


/**
 * 根据执行状态返回图标。
 */
function statusIcon(
    status: AgentExecutionStatus
): string {

  switch (status) {

    case 'RUNNING':
      return '●'

    case 'SUCCESS':
      return '✓'

    case 'WAITING':
      return '…'

    case 'FAILED':
      return '×'

    case 'PENDING':
    default:
      return '○'
  }
}


/**
 * 页面展示状态文字。
 */
function statusLabel(
    status: AgentExecutionStatus
): string {

  switch (status) {

    case 'RUNNING':
      return '执行中'

    case 'SUCCESS':
      return '成功'

    case 'WAITING':
      return '等待中'

    case 'FAILED':
      return '失败'

    case 'PENDING':
    default:
      return '等待执行'
  }
}


/**
 * 返回 CSS class。
 *
 * 例如：
 *
 * RUNNING
 *
 * 转换成：
 *
 * status-running
 */
function statusClass(
    status: AgentExecutionStatus
): string {

  return `status-${status.toLowerCase()}`
}


/**
 * 把技术类型转换成更容易阅读的标签。
 */
function typeLabel(
    type: AgentExecutionType
): string {

  switch (type) {

    case 'AGENT':
      return 'AGENT'

    case 'INTENT':
      return 'INTENT'

    case 'VALIDATION':
      return 'VALIDATION'

    case 'ROUTE':
      return 'ROUTER'

    case 'TOOL':
      return 'TOOL'

    case 'WORKFLOW':
      return 'WORKFLOW'

    case 'APPROVAL':
      return 'APPROVAL'

    case 'RETRY':
      return 'RETRY'

    case 'ERROR':
      return 'ERROR'

    case 'DONE':
      return 'DONE'

    default:
      return type
  }
}


/**
 * 格式化对象。
 *
 * JSON.stringify(
 *   数据,
 *   null,
 *   2
 * )
 *
 * 中的 2 表示使用两个空格缩进。
 */
function formatJson(
    value: unknown
): string {

  if (value === undefined) {
    return ''
  }

  try {

    return JSON.stringify(
        value,
        null,
        2
    )

  } catch {

    return String(value)
  }
}

</script>


<style scoped>

.timeline {
  margin-top: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #ffffff;
  padding: 16px;
}


/* ============================================================
   Header
   ============================================================ */

.timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 18px;
}

.timeline-title {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}

.timeline-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: #6b7280;
}

.timeline-count {
  flex-shrink: 0;
  padding: 4px 8px;
  border-radius: 999px;
  background: #f3f4f6;
  color: #6b7280;
  font-size: 12px;
}


/* ============================================================
   Timeline
   ============================================================ */

.timeline-list {
  display: flex;
  flex-direction: column;
}

.timeline-item {
  display: grid;
  grid-template-columns: 30px 1fr;
  gap: 10px;
  min-width: 0;
}

.timeline-marker {
  position: relative;
  display: flex;
  justify-content: center;
}

.timeline-icon {
  z-index: 1;
  width: 24px;
  height: 24px;
  border-radius: 50%;

  display: inline-flex;
  align-items: center;
  justify-content: center;

  background: #f3f4f6;
  border: 1px solid #d1d5db;

  font-size: 13px;
  font-weight: 700;
}

.timeline-line {
  position: absolute;
  top: 24px;
  bottom: -12px;
  width: 2px;
  background: #e5e7eb;
}


/* ============================================================
   Content
   ============================================================ */

.timeline-content {
  min-width: 0;
  margin-bottom: 14px;
  padding: 12px 14px;

  border-radius: 10px;
  border: 1px solid #e5e7eb;

  background: #fafafa;
}

.timeline-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.timeline-title-area {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.item-title {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}

.type-tag {
  padding: 2px 6px;
  border-radius: 4px;
  background: #eef2ff;
  color: #4338ca;

  font-size: 10px;
  font-weight: 700;
}

.status-tag {
  flex-shrink: 0;

  padding: 3px 8px;
  border-radius: 999px;

  font-size: 11px;
  font-weight: 600;
}


/* ============================================================
   Description / Meta
   ============================================================ */

.description {
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.6;
  color: #4b5563;
}

.meta-row {
  margin-top: 10px;

  display: flex;
  flex-wrap: wrap;
  gap: 12px;

  font-size: 11px;
  color: #6b7280;
}


/* ============================================================
   Detail
   ============================================================ */

.detail-group {
  margin-top: 10px;
}

.detail-box {
  margin-top: 10px;
  padding: 8px 10px;

  border-radius: 8px;
  background: #f3f4f6;
}

.detail-label {
  margin-bottom: 4px;

  font-size: 10px;
  color: #6b7280;
  text-transform: uppercase;
}

.detail-value {
  font-size: 12px;
  color: #111827;
}

.code {
  font-family:
      Consolas,
      Monaco,
      monospace;
}

.break-all {
  word-break: break-all;
}


/* ============================================================
   Details
   ============================================================ */

.details-panel {
  margin-top: 8px;

  border-radius: 8px;
  border: 1px solid #e5e7eb;

  background: #ffffff;
}

.details-panel summary {
  cursor: pointer;
  padding: 8px 10px;

  font-size: 12px;
  color: #374151;

  user-select: none;
}

.details-panel pre {
  margin: 0;
  padding: 10px;

  max-height: 240px;
  overflow: auto;

  border-top: 1px solid #e5e7eb;

  background: #111827;
  color: #e5e7eb;

  font-size: 11px;
  line-height: 1.5;

  white-space: pre-wrap;
  word-break: break-word;
}

.raw-panel {
  opacity: 0.85;
}


/* ============================================================
   Status
   ============================================================ */

.status-running {
  border-color: #93c5fd;
}

.timeline-icon.status-running {
  color: #2563eb;
  background: #eff6ff;
}

.status-tag.status-running {
  color: #1d4ed8;
  background: #dbeafe;
}


.status-success {
  border-color: #86efac;
}

.timeline-icon.status-success {
  color: #16a34a;
  background: #f0fdf4;
}

.status-tag.status-success {
  color: #15803d;
  background: #dcfce7;
}


.status-waiting {
  border-color: #fde68a;
}

.timeline-icon.status-waiting {
  color: #ca8a04;
  background: #fefce8;
}

.status-tag.status-waiting {
  color: #a16207;
  background: #fef3c7;
}


.status-failed {
  border-color: #fca5a5;
}

.timeline-icon.status-failed {
  color: #dc2626;
  background: #fef2f2;
}

.status-tag.status-failed {
  color: #b91c1c;
  background: #fee2e2;
}


.status-pending {
  border-color: #d1d5db;
}

.timeline-icon.status-pending {
  color: #6b7280;
}

.status-tag.status-pending {
  color: #4b5563;
  background: #f3f4f6;
}


/* ============================================================
   Running / Waiting / Error
   ============================================================ */

.running-tip {
  margin-top: 10px;

  display: flex;
  align-items: center;
  gap: 7px;

  font-size: 12px;
  color: #2563eb;
}

.loading-dot {
  width: 7px;
  height: 7px;

  border-radius: 50%;
  background: #2563eb;

  animation: pulse 1s infinite;
}

.waiting-tip {
  margin-top: 10px;
  padding: 8px 10px;

  border-radius: 8px;

  background: #fffbeb;
  color: #92400e;

  font-size: 12px;
}

.error-box {
  margin-top: 10px;
  padding: 8px 10px;

  border-radius: 8px;

  background: #fef2f2;
  color: #b91c1c;

  font-size: 12px;
}

.workflow-box {
  background: #f5f3ff;
}


@keyframes pulse {

  0% {
    opacity: 0.35;
  }

  50% {
    opacity: 1;
  }

  100% {
    opacity: 0.35;
  }
}

</style>