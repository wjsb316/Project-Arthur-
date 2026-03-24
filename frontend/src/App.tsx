import React, { useState, useEffect, useRef, useCallback } from 'react';
import { API_HEADERS } from './api';
import type { AppView, ChatMessage, HistorySession, Memory, Agent, Guardrail, PipelineTiming } from './types';
import Sidebar, { MobileHeader } from './components/Sidebar';
import {
  AuthView,
  VoiceView,
  ChatView,
  HistoryView,
  MemoriesView,
  AgentsView,
  GuardrailsView,
  SettingsView,
} from './views';
import { useVoiceRecording } from './hooks/useVoiceRecording';
import './App.css';

function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [backendReady, setBackendReady] = useState(false);
  const [view, setView] = useState<AppView>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // Memories
  const [memories, setMemories] = useState<Memory[]>([]);
  const [newMemoryContent, setNewMemoryContent] = useState('');
  const [newMemoryKind, setNewMemoryKind] = useState('fact');
  const [isCreatingMemory, setIsCreatingMemory] = useState(false);
  const [memorySearch, setMemorySearch] = useState('');
  const [selectedMemories, setSelectedMemories] = useState<number[]>([]);
  const [nukeMemoriesProgress, setNukeMemoriesProgress] = useState(0);
  const nukeMemoriesTimerRef = useRef<number | null>(null);
  const [editingMemory, setEditingMemory] = useState<Memory | null>(null);
  const [editMemoryContent, setEditMemoryContent] = useState('');
  const [editMemoryKind, setEditMemoryKind] = useState('fact');

  // Agents
  const [agents, setAgents] = useState<Agent[]>([]);
  const [newAgentName, setNewAgentName] = useState('');
  const [newAgentPrompt, setNewAgentPrompt] = useState('');
  const [isCreatingAgent, setIsCreatingAgent] = useState(false);
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);
  const [editAgentName, setEditAgentName] = useState('');
  const [editAgentPrompt, setEditAgentPrompt] = useState('');

  // Guardrails
  const [guardrails, setGuardrails] = useState<Guardrail[]>([]);
  const [newGuardrailName, setNewGuardrailName] = useState('');
  const [newGuardrailPrompt, setNewGuardrailPrompt] = useState('');
  const [isCreatingGuardrail, setIsCreatingGuardrail] = useState(false);
  const [editingGuardrail, setEditingGuardrail] = useState<Guardrail | null>(null);
  const [editGuardrailName, setEditGuardrailName] = useState('');
  const [editGuardrailPrompt, setEditGuardrailPrompt] = useState('');

  // Chat
  const [chatInput, setChatInput] = useState('');
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [pipelineTiming, setPipelineTiming] = useState<PipelineTiming | null>(null);
  const handleTimingUpdate = useCallback((t: PipelineTiming) => setPipelineTiming(t), []);
  const [fullHistory, setFullHistory] = useState<HistorySession[]>([]);
  const [selectedSessions, setSelectedSessions] = useState<number[]>([]);
  const [historySearch, setHistorySearch] = useState('');
  const [nukeProgress, setNukeProgress] = useState(0);
  const nukeTimerRef = useRef<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isNewSession, setIsNewSession] = useState(true);
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Settings
  const [configLoading, setConfigLoading] = useState(false);
  const [similarityThreshold, setSimilarityThreshold] = useState(50);
  const [voiceCharactersUsed, setVoiceCharactersUsed] = useState<number>(0);

  const { isRecording, isVoiceProcessing, startRecording, stopRecording, interruptPlayback } = useVoiceRecording(
    token,
    currentSessionId,
    isNewSession,
    setCurrentSessionId,
    setIsNewSession,
    handleTimingUpdate
  );

  useEffect(() => {
    if (token) {
      setView('dashboard');
      fetch('/users/me', {
        headers: { Authorization: `Bearer ${token}`, ...API_HEADERS },
      })
        .then((res) => (res.ok ? res.json() : Promise.reject(new Error('Failed to fetch user info'))))
        .then((data) => {
          setUsername(data.username);
          if (typeof data.voice_characters_used === 'number') {
            setVoiceCharactersUsed(data.voice_characters_used);
          }
        })
        .catch(console.error);
    }
  }, [token]);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    const poll = async () => {
      try {
        const res = await fetch('/api/ready');
        if (res.ok) {
          const data = await res.json();
          if (data.ready) {
            setBackendReady(true);
            return;
          }
        }
      } catch { /* server not up yet */ }
      if (!cancelled) setTimeout(poll, 1500);
    };
    poll();
    return () => { cancelled = true; };
  }, [token]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  useEffect(() => {
    if (view === 'history' && token) fetchHistory();
    if (view === 'agents' && token) fetchAgents();
    if (view === 'guardrails' && token) fetchGuardrails();
    if (view === 'memories' && token) fetchMemories();
    if (view === 'settings' && token) {
      setConfigLoading(true);
      fetch('/api/config/', { headers: { Authorization: `Bearer ${token}`, ...API_HEADERS } })
        .then((res) => (res.ok ? res.json() : Promise.reject(new Error('Failed to load config'))))
        .then((data: { similarity_threshold: number }) => {
          setSimilarityThreshold(data.similarity_threshold ?? 50);
        })
        .catch(console.error)
        .finally(() => setConfigLoading(false));

      fetch('/users/me', { headers: { Authorization: `Bearer ${token}`, ...API_HEADERS } })
        .then((res) => (res.ok ? res.json() : Promise.reject(new Error('Failed to fetch user info'))))
        .then((data) => {
          if (typeof data.voice_characters_used === 'number') {
            setVoiceCharactersUsed(data.voice_characters_used);
          }
        })
        .catch(console.error);
    }
  }, [view, token]);

  // When opening chat (dashboard), sync with server only if we have a current session
  useEffect(() => {
    if (view !== 'dashboard' || !token || currentSessionId == null) return;
    fetch('/api/chat/history', { headers: { Authorization: `Bearer ${token}`, ...API_HEADERS } })
      .then((res) => res.ok ? res.json() : Promise.reject(new Error('Failed to load history')))
      .then((data: HistorySession[]) => {
        const session = data?.find((s) => s.id === currentSessionId);
        if (session) {
          setChatHistory(session.messages.map((msg) => ({ role: msg.role, content: msg.content })));
        }
      })
      .catch(console.error);
  }, [view, token, currentSessionId]);

  const fetchMemories = () => {
    fetch('/api/memories/', { headers: { Authorization: `Bearer ${token}`, ...API_HEADERS } })
      .then((res) => res.json())
      .then((data) => {
        setMemories(data);
        setSelectedMemories([]);
      })
      .catch(console.error);
  };

  const filteredMemories = memories.filter((m) => {
    if (!memorySearch.trim()) return true;
    const term = memorySearch.toLowerCase();
    return m.content.toLowerCase().includes(term) || m.kind.toLowerCase().includes(term);
  });

  const handleCreateMemory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMemoryContent.trim()) return;
    try {
      const res = await fetch('/api/memories/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...API_HEADERS },
        body: JSON.stringify({ content: newMemoryContent, kind: newMemoryKind }),
      });
      if (res.ok) {
        setNewMemoryContent('');
        setNewMemoryKind('fact');
        setIsCreatingMemory(false);
        fetchMemories();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const toggleMemory = (id: number) => {
    setSelectedMemories((prev) => (prev.includes(id) ? prev.filter((m) => m !== id) : [...prev, id]));
  };

  const handleDeleteSelectedMemories = async () => {
    if (selectedMemories.length === 0 || !confirm(`Forget ${selectedMemories.length} memories?`)) return;
    try {
      const res = await fetch('/api/memories/selected/bulk', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...API_HEADERS },
        body: JSON.stringify({ memory_ids: selectedMemories }),
      });
      if (res.ok) {
        setSelectedMemories([]);
        fetchMemories();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const startNukeMemories = () => {
    let progress = 0;
    if (nukeMemoriesTimerRef.current) clearInterval(nukeMemoriesTimerRef.current);
    nukeMemoriesTimerRef.current = window.setInterval(() => {
      progress += 4;
      setNukeMemoriesProgress(progress);
      if (progress >= 100) {
        if (nukeMemoriesTimerRef.current) clearInterval(nukeMemoriesTimerRef.current);
        handleNukeMemories();
        setNukeMemoriesProgress(0);
      }
    }, 40);
  };

  const cancelNukeMemories = () => {
    if (nukeMemoriesTimerRef.current) {
      clearInterval(nukeMemoriesTimerRef.current);
      nukeMemoriesTimerRef.current = null;
    }
    setNukeMemoriesProgress(0);
  };

  const handleNukeMemories = async () => {
    try {
      const res = await fetch('/api/memories/all/nuke', {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}`, ...API_HEADERS },
      });
      if (res.ok) {
        alert('MEMORIES NUKED');
        setSelectedMemories([]);
        fetchMemories();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleUpdateMemory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editMemoryContent.trim() || !editingMemory) return;
    try {
      const res = await fetch(`/api/memories/${editingMemory.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...API_HEADERS },
        body: JSON.stringify({ content: editMemoryContent, kind: editMemoryKind }),
      });
      if (res.ok) {
        setEditingMemory(null);
        setEditMemoryContent('');
        setEditMemoryKind('fact');
        fetchMemories();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchAgents = () => {
    fetch('/api/agents/', { headers: { Authorization: `Bearer ${token}`, ...API_HEADERS } })
      .then((res) => res.json())
      .then((data) => setAgents(data))
      .catch(console.error);
  };

  const handleCreateAgent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newAgentName.trim() || !newAgentPrompt.trim()) return;
    try {
      const res = await fetch('/api/agents/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...API_HEADERS },
        body: JSON.stringify({ name: newAgentName, prompt: newAgentPrompt }),
      });
      if (res.ok) {
        setNewAgentName('');
        setNewAgentPrompt('');
        setIsCreatingAgent(false);
        fetchAgents();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleDeleteAgent = async (id: number) => {
    if (!confirm('Delete this agent?')) return;
    try {
      const res = await fetch(`/api/agents/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}`, ...API_HEADERS },
      });
      if (res.ok) fetchAgents();
    } catch (e) {
      console.error(e);
    }
  };

  const handleUpdateAgent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editAgentName.trim() || !editAgentPrompt.trim() || !editingAgent) return;
    try {
      const res = await fetch(`/api/agents/${editingAgent.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...API_HEADERS },
        body: JSON.stringify({ name: editAgentName, prompt: editAgentPrompt }),
      });
      if (res.ok) {
        setEditingAgent(null);
        setEditAgentName('');
        setEditAgentPrompt('');
        fetchAgents();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleToggleAgent = async (id: number, enabled: boolean) => {
    try {
      const res = await fetch(`/api/agents/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...API_HEADERS },
        body: JSON.stringify({ enabled }),
      });
      if (res.ok) fetchAgents();
    } catch (e) {
      console.error(e);
    }
  };

  const fetchGuardrails = () => {
    fetch('/api/guardrails/', { headers: { Authorization: `Bearer ${token}`, ...API_HEADERS } })
      .then((res) => res.json())
      .then((data) => setGuardrails(data))
      .catch(console.error);
  };

  const handleCreateGuardrail = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newGuardrailName.trim() || !newGuardrailPrompt.trim()) return;
    try {
      const res = await fetch('/api/guardrails/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...API_HEADERS },
        body: JSON.stringify({ name: newGuardrailName, prompt: newGuardrailPrompt }),
      });
      if (res.ok) {
        setNewGuardrailName('');
        setNewGuardrailPrompt('');
        setIsCreatingGuardrail(false);
        fetchGuardrails();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleDeleteGuardrail = async (id: number) => {
    if (!confirm('Delete this guardrail?')) return;
    try {
      const res = await fetch(`/api/guardrails/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}`, ...API_HEADERS },
      });
      if (res.ok) fetchGuardrails();
    } catch (e) {
      console.error(e);
    }
  };

  const handleUpdateGuardrail = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editGuardrailName.trim() || !editGuardrailPrompt.trim() || !editingGuardrail) return;
    try {
      const res = await fetch(`/api/guardrails/${editingGuardrail.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...API_HEADERS },
        body: JSON.stringify({ name: editGuardrailName, prompt: editGuardrailPrompt }),
      });
      if (res.ok) {
        setEditingGuardrail(null);
        setEditGuardrailName('');
        setEditGuardrailPrompt('');
        fetchGuardrails();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchHistory = () => {
    fetch('/api/chat/history', { headers: { Authorization: `Bearer ${token}`, ...API_HEADERS } })
      .then((res) => res.json())
      .then((data) => {
        setFullHistory(data);
        setSelectedSessions([]);
      })
      .catch(console.error);
  };

  const filteredHistory = fullHistory.filter((session) => {
    if (!historySearch.trim()) return true;
    const term = historySearch.toLowerCase();
    if (session.id.toString().includes(term)) return true;
    return session.messages.some(
      (msg: { content: string; role: string }) =>
        msg.content.toLowerCase().includes(term) || msg.role.toLowerCase().includes(term)
    );
  });

  const toggleSession = (id: number) => {
    setSelectedSessions((prev) => (prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]));
  };

  const handleDeleteSelected = async () => {
    if (selectedSessions.length === 0 || !confirm(`Delete ${selectedSessions.length} sessions?`)) return;
    const deletingCurrent = currentSessionId !== null && selectedSessions.includes(currentSessionId);
    try {
      const res = await fetch('/api/chat/sessions', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...API_HEADERS },
        body: JSON.stringify({ session_ids: selectedSessions }),
      });
      if (res.ok) {
        fetchHistory();
        if (deletingCurrent) handleNewChat();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const startNuke = () => {
    let progress = 0;
    if (nukeTimerRef.current) clearInterval(nukeTimerRef.current);
    nukeTimerRef.current = window.setInterval(() => {
      progress += 4;
      setNukeProgress(progress);
      if (progress >= 100) {
        if (nukeTimerRef.current) clearInterval(nukeTimerRef.current);
        handleNukeHistory();
        setNukeProgress(0);
      }
    }, 40);
  };

  const cancelNuke = () => {
    if (nukeTimerRef.current) {
      clearInterval(nukeTimerRef.current);
      nukeTimerRef.current = null;
    }
    setNukeProgress(0);
  };

  const handleNukeHistory = async () => {
    try {
      const res = await fetch('/api/chat/history', {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}`, ...API_HEADERS },
      });
      if (res.ok) {
        alert('HISTORY NUKED');
        fetchHistory();
        handleNewChat();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleNewChat = () => {
    setChatHistory([]);
    setIsNewSession(true);
    setCurrentSessionId(null);
    if (view !== 'dashboard') setView('dashboard');
  };

  const loadSession = (session: HistorySession) => {
    setChatHistory(
      session.messages.map((msg) => ({ role: msg.role, content: msg.content }))
    );
    setCurrentSessionId(session.id);
    setIsNewSession(false);
    setView('dashboard');
  };

  const handleChatSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;
    const userMessage = { role: 'user', content: chatInput };
    setChatHistory((prev) => [...prev, userMessage]);
    setChatInput('');
    setIsLoading(true);
    try {
      const payload: { text: string; new_session: boolean; session_id?: number } = {
        text: userMessage.content,
        new_session: isNewSession,
      };
      if (currentSessionId && !isNewSession) payload.session_id = currentSessionId;
      if (isNewSession) setIsNewSession(false);
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...API_HEADERS },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.session_id && !currentSessionId) setCurrentSessionId(data.session_id);
        if (data.response) setChatHistory((prev) => [...prev, { role: 'Arthur', content: data.response.content }]);
        if (data.timing) setPipelineTiming(data.timing);
      } else {
        setChatHistory((prev) => [...prev, { role: 'Arthur', content: 'I am having trouble communicating with the model provider.' }]);
      }
    } catch (err) {
      console.error(err);
      setChatHistory((prev) => [...prev, { role: 'Arthur', content: 'I am having trouble communicating with the model provider.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    try {
      const res = await fetch('/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded', ...API_HEADERS },
        body: formData,
      });
      if (!res.ok) throw new Error('Login failed');
      const data = await res.json();
      localStorage.setItem('token', data.access_token);
      setToken(data.access_token);
      setView('dashboard');
      setError('');
    } catch (err) {
      setError('Invalid credentials');
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch('/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...API_HEADERS },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Registration failed');
      }
      alert('Account created! Please login.');
      setView('login');
      setError('');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Registration failed');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setView('login');
    setUsername('');
    setPassword('');
  };

  const handleDeleteAccount = async () => {
    if (!confirm('Are you sure? This cannot be undone.')) return;
    try {
      const res = await fetch('/users/me', {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}`, ...API_HEADERS },
      });
      if (res.ok) handleLogout();
      else alert('Failed to delete');
    } catch (e) {
      alert('Error deleting account');
    }
  };

  if (!token) {
    return (
      <AuthView
        view={view === 'register' ? 'register' : 'login'}
        username={username}
        setUsername={setUsername}
        password={password}
        setPassword={setPassword}
        error={error}
        onLogin={handleLogin}
        onRegister={handleRegister}
        onToggleAuth={() => {
          setView(view === 'login' ? 'register' : 'login');
          setError('');
        }}
      />
    );
  }

  const mainViews: AppView[] = ['dashboard', 'history', 'agents', 'guardrails', 'memories', 'settings', 'voice'];
  if (!mainViews.includes(view)) return null;

  return (
    <div className="app-layout">
      {!backendReady && (
        <div className="backend-loading-overlay">
          <div className="backend-loading-content">
            <div className="backend-loading-spinner" />
            <p>Loading...</p>
          </div>
        </div>
      )}
      <MobileHeader onMenuClick={() => setIsSidebarOpen(true)} />
      <Sidebar
        view={view}
        setView={setView}
        username={username}
        onLogout={handleLogout}
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
      />
      <main className="main-content">
        {view === 'voice' && (
          <VoiceView
            token={token}
            isVoiceProcessing={isVoiceProcessing}
            isRecording={isRecording}
            currentSessionId={currentSessionId}
            isNewSession={isNewSession}
            setCurrentSessionId={setCurrentSessionId}
            setIsNewSession={setIsNewSession}
            onStartRecording={startRecording}
            onStopRecording={stopRecording}
            onInterruptPlayback={interruptPlayback}
            onNewChat={handleNewChat}
            pipelineTiming={pipelineTiming}
            onTimingUpdate={handleTimingUpdate}
          />
        )}
        {view === 'dashboard' && (
          <ChatView
            chatHistory={chatHistory}
            chatInput={chatInput}
            setChatInput={setChatInput}
            isLoading={isLoading}
            messagesEndRef={messagesEndRef}
            onNewChat={handleNewChat}
            onSubmit={handleChatSubmit}
            pipelineTiming={pipelineTiming}
          />
        )}
        {view === 'history' && (
          <HistoryView
            filteredHistory={filteredHistory}
            historySearch={historySearch}
            setHistorySearch={setHistorySearch}
            selectedSessions={selectedSessions}
            toggleSession={toggleSession}
            nukeProgress={nukeProgress}
            onDeleteSelected={handleDeleteSelected}
            onLoadSession={loadSession}
            onNukeMouseDown={startNuke}
            onNukeMouseUp={cancelNuke}
            onNukeMouseLeave={cancelNuke}
            onNukeTouchStart={startNuke}
            onNukeTouchEnd={cancelNuke}
          />
        )}
        {view === 'memories' && (
          <MemoriesView
            filteredMemories={filteredMemories}
            memorySearch={memorySearch}
            setMemorySearch={setMemorySearch}
            selectedMemories={selectedMemories}
            toggleMemory={toggleMemory}
            isCreatingMemory={isCreatingMemory}
            setIsCreatingMemory={setIsCreatingMemory}
            newMemoryContent={newMemoryContent}
            setNewMemoryContent={setNewMemoryContent}
            newMemoryKind={newMemoryKind}
            setNewMemoryKind={setNewMemoryKind}
            editingMemory={editingMemory}
            setEditingMemory={setEditingMemory}
            editMemoryContent={editMemoryContent}
            setEditMemoryContent={setEditMemoryContent}
            editMemoryKind={editMemoryKind}
            setEditMemoryKind={setEditMemoryKind}
            onCreateMemory={handleCreateMemory}
            onUpdateMemory={handleUpdateMemory}
            onDeleteSelected={handleDeleteSelectedMemories}
            nukeProgress={nukeMemoriesProgress}
            onNukeMouseDown={startNukeMemories}
            onNukeMouseUp={cancelNukeMemories}
            onNukeMouseLeave={cancelNukeMemories}
            onNukeTouchStart={startNukeMemories}
            onNukeTouchEnd={cancelNukeMemories}
          />
        )}
        {view === 'agents' && (
          <AgentsView
            agents={agents}
            isCreatingAgent={isCreatingAgent}
            setIsCreatingAgent={setIsCreatingAgent}
            newAgentName={newAgentName}
            setNewAgentName={setNewAgentName}
            newAgentPrompt={newAgentPrompt}
            setNewAgentPrompt={setNewAgentPrompt}
            editingAgent={editingAgent}
            setEditingAgent={setEditingAgent}
            editAgentName={editAgentName}
            setEditAgentName={setEditAgentName}
            editAgentPrompt={editAgentPrompt}
            setEditAgentPrompt={setEditAgentPrompt}
            onCreateAgent={handleCreateAgent}
            onUpdateAgent={handleUpdateAgent}
            onDeleteAgent={handleDeleteAgent}
            onToggleAgent={handleToggleAgent}
          />
        )}
        {view === 'guardrails' && (
          <GuardrailsView
            guardrails={guardrails}
            isCreatingGuardrail={isCreatingGuardrail}
            setIsCreatingGuardrail={setIsCreatingGuardrail}
            newGuardrailName={newGuardrailName}
            setNewGuardrailName={setNewGuardrailName}
            newGuardrailPrompt={newGuardrailPrompt}
            setNewGuardrailPrompt={setNewGuardrailPrompt}
            editingGuardrail={editingGuardrail}
            setEditingGuardrail={setEditingGuardrail}
            editGuardrailName={editGuardrailName}
            setEditGuardrailName={setEditGuardrailName}
            editGuardrailPrompt={editGuardrailPrompt}
            setEditGuardrailPrompt={setEditGuardrailPrompt}
            onCreateGuardrail={handleCreateGuardrail}
            onUpdateGuardrail={handleUpdateGuardrail}
            onDeleteGuardrail={handleDeleteGuardrail}
          />
        )}
        {view === 'settings' && (
          <SettingsView
            similarityThreshold={similarityThreshold}
            setSimilarityThreshold={setSimilarityThreshold}
            configLoading={configLoading}
            token={token}
            voiceCharactersUsed={voiceCharactersUsed}
            onDeleteAccount={handleDeleteAccount}
          />
        )}
      </main>
    </div>
  );
}

export default App;
