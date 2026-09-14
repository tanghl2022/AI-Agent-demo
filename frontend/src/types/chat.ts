import type { AgentExecutionItem } from './execution'
export type ChatRole = 'user' | 'assistant'
export interface ChatMessage {
  id: string
  role: ChatRole
  content: string
  status?: string
  streaming?: boolean
  executions?: AgentExecutionItem[]
}
