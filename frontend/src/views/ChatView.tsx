import React from 'react';
import { Send } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { IconCat, IconNewChat } from '../components/Icons';
import TypingIndicator from '../components/TypingIndicator';
import PipelineTimingDisplay from '../components/PipelineTimingDisplay';
import type { ChatMessage, PipelineTiming } from '../types';

interface ChatViewProps {
  chatHistory: ChatMessage[];
  chatInput: string;
  setChatInput: (s: string) => void;
  isLoading: boolean;
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
  onNewChat: () => void;
  onSubmit: (e: React.FormEvent) => void;
  pipelineTiming?: PipelineTiming | null;
}

export default function ChatView({
  chatHistory,
  chatInput,
  setChatInput,
  isLoading,
  messagesEndRef,
  onNewChat,
  onSubmit,
  pipelineTiming,
}: ChatViewProps) {
  return (
    <div className="chat-interface">
      <header className="chat-header">
        <div>
          <h1>Arthur Prime</h1>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.4rem' }}>
          <button
            onClick={onNewChat}
            title="Start New Chat"
            style={{
              background: 'transparent',
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              padding: '0.5rem',
              cursor: 'pointer',
              color: '#64748b',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            <IconNewChat />
            <span style={{ fontSize: '0.9rem', fontWeight: 500 }}>New Chat</span>
          </button>
          <PipelineTimingDisplay timing={pipelineTiming ?? null} dark={false} />
        </div>
      </header>
      <div className="chat-area">
        {chatHistory.length === 0 && (
          <div className="chat-message assistant">
            <div className="message-icon">
              <IconCat />
            </div>
            <div className="message-content">Arthur Prime at your service! (Markdown supported)</div>
          </div>
        )}
        {chatHistory.map((msg, i) => (
          <div key={i} className={`chat-message ${msg.role}`}>
            {(msg.role === 'assistant' || msg.role === 'Arthur') && (
              <div className="message-icon">
                <IconCat />
              </div>
            )}
            <div className="message-content">
              <ReactMarkdown>{msg.content}</ReactMarkdown>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="chat-message assistant">
            <div className="message-icon">
              <IconCat />
            </div>
            <TypingIndicator />
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <div className="input-area">
        <form onSubmit={onSubmit} className="chat-input-wrapper">
          <textarea
            value={chatInput}
            onChange={(e) => {
              setChatInput(e.target.value);
              e.target.style.height = 'auto';
              e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px';
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                onSubmit(e);
              }
            }}
            placeholder="Type your message..."
            rows={1}
          />
          <button type="submit" className="send-btn" disabled={isLoading || !chatInput.trim()}>
            <Send color="#000000" strokeWidth={1} />
          </button>
        </form>
      </div>
    </div>
  );
}
