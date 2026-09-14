<template>
  <main class="page">
    <header><h1>WMS Agent Demo</h1><p>LangGraph + Runtime Event + SSE + Checkpoint</p></header>
    <section class="session-bar"><label>threadId</label><input v-model="threadId" /><button @click="newThread">新会话</button></section>
    <section class="messages">
      <article v-for="message in messages" :key="message.id" :class="['message', message.role]">
        <strong>{{ message.role === 'user' ? '用户' : 'WMS Agent' }}</strong>
        <AgentTimeline v-if="message.role === 'assistant' && message.executions" :items="message.executions" />
        <div v-if="message.status && message.streaming" class="status">{{ message.status }}</div>
        <pre class="answer">{{ message.content }}</pre>
      </article>
    </section>
    <section class="composer">
      <textarea v-model="input" placeholder="例如：查询 MAT001 的库存、库存明细和库位" @keydown.ctrl.enter.prevent="send" />
      <button :disabled="loading || !input.trim()" @click="send">{{ loading ? '执行中...' : '发送' }}</button>
    </section>
  </main>
</template>
<script setup lang="ts">
import { reactive, ref } from 'vue'
import AgentTimeline from './components/AgentTimeline.vue'
import { streamAgentChat } from './services/agent'
import type { AgentEvent, ErrorEventData, StatusEventData, TokenEventData } from './types/agent'
import type { ChatMessage } from './types/chat'
import { applyAgentEventToExecutions } from './utils/agentExecution'

const messages = ref<ChatMessage[]>([])
const input = ref('')
const loading = ref(false)
const threadId = ref('wms-demo-001')
const id = () => crypto.randomUUID()

function newThread() {
  threadId.value = `wms-${Date.now()}`
  messages.value = []
}

function handleAgentEvent(event: AgentEvent, assistant: ChatMessage) {
  if (assistant.executions) applyAgentEventToExecutions(event, assistant.executions)
  switch (event.event) {
    case 'STATUS': assistant.status = (event.data as StatusEventData).message; break
    case 'TOKEN': assistant.content += (event.data as TokenEventData).content ?? ''; break
    case 'DONE': assistant.streaming = false; assistant.status = '回答完成'; break
    case 'ERROR': assistant.streaming = false; assistant.status = (event.data as ErrorEventData).message; break
  }
}

async function send() {
  const question = input.value.trim()
  if (!question || loading.value) return
  const user: ChatMessage = { id: id(), role: 'user', content: question }
  const assistant = reactive<ChatMessage>({ id: id(), role: 'assistant', content: '', status: '正在连接 Agent', streaming: true, executions: [] })
  messages.value.push(user, assistant)
  input.value = ''
  loading.value = true
  try {
    await streamAgentChat({ message: question, threadId: threadId.value }, event => handleAgentEvent(event, assistant))
  } catch (error) {
    assistant.streaming = false
    assistant.status = error instanceof Error ? error.message : '请求失败'
  } finally {
    loading.value = false
  }
}
</script>
