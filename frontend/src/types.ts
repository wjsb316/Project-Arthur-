export interface Memory {
  id: number;
  content: string;
  kind: string;
  created_at: string;
}

export interface Agent {
  id: number;
  name: string;
  prompt: string;
  created_at?: string;
}

export interface Guardrail {
  id: number;
  name: string;
  prompt: string;
  created_at?: string;
}

export interface ChatMessage {
  role: string;
  content: string;
}

export interface HistoryMessage {
  role: string;
  content: string;
  created_at?: string;
}

export interface HistorySession {
  id: number;
  created_at: string;
  messages: HistoryMessage[];
}

export type AppView =
  | 'login'
  | 'register'
  | 'dashboard'
  | 'history'
  | 'agents'
  | 'guardrails'
  | 'memories'
  | 'settings'
  | 'voice';
