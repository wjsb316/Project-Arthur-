import React, { useState, useEffect, useRef } from 'react';
import { Send, Mic, Pencil } from 'lucide-react';
import './App.css';
import Antigravity from './Antigravity';
import ReactMarkdown from 'react-markdown';

const API_HEADERS = {
    'X-Arthur-Client': 'Arthur-Prime-V1'
};

// Icons
const IconMenu = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="3" y1="12" x2="21" y2="12"></line>
    <line x1="3" y1="6" x2="21" y2="6"></line>
    <line x1="3" y1="18" x2="21" y2="18"></line>
  </svg>
);

const IconDashboard = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="7" height="7"></rect>
    <rect x="14" y="3" width="7" height="7"></rect>
    <rect x="14" y="14" width="7" height="7"></rect>
    <rect x="3" y="14" width="7" height="7"></rect>
  </svg>
);

const IconHistory = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"></circle>
    <polyline points="12 6 12 12 16 14"></polyline>
  </svg>
);

const IconAgents = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
    <circle cx="9" cy="7" r="4"></circle>
    <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
    <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
  </svg>
);

const IconGuardrails = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
  </svg>
);

const IconBrain = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2Z"></path>
    <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2Z"></path>
  </svg>
);

const IconSettings = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="3"></circle>
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
  </svg>
);

const IconNewChat = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
     <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
     <line x1="12" y1="7" x2="12" y2="13"></line>
     <line x1="9" y1="10" x2="15" y2="10"></line>
  </svg>
);

const IconVoice = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
    <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
    <line x1="12" y1="19" x2="12" y2="23"></line>
    <line x1="8" y1="23" x2="16" y2="23"></line>
  </svg>
);

const IconCat = () => (
    <svg width="40" height="40" viewBox="0 0 24 24" fill="black" stroke="none">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-5-9h2v2H7v-2zm8 0h2v2h-2v-2zm-4 4h4v2h-4v-2z"/>
    </svg>
);

const TypingIndicator = () => (
    <div className="typing-indicator">
        <span className="typing-dot"></span>
        <span className="typing-dot"></span>
        <span className="typing-dot"></span>
    </div>
);


function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [view, setView] = useState<'login' | 'register' | 'dashboard' | 'history' | 'agents' | 'guardrails' | 'memories' | 'settings' | 'voice'>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // Memories State
  const [memories, setMemories] = useState<Array<{id: number, content: string, kind: string, created_at: string}>>([]);
  const [newMemoryContent, setNewMemoryContent] = useState('');
  const [newMemoryKind, setNewMemoryKind] = useState('fact');
  const [isCreatingMemory, setIsCreatingMemory] = useState(false);
  const [memorySearch, setMemorySearch] = useState('');
  const [selectedMemories, setSelectedMemories] = useState<number[]>([]);
  const [nukeMemoriesProgress, setNukeMemoriesProgress] = useState(0);
  const nukeMemoriesTimerRef = useRef<number | null>(null);

  const [editingMemory, setEditingMemory] = useState<{id: number, content: string, kind: string, created_at: string} | null>(null);
  const [editMemoryContent, setEditMemoryContent] = useState('');
  const [editMemoryKind, setEditMemoryKind] = useState('fact');

  // Agents State
  const [agents, setAgents] = useState<Array<{id: number, name: string, prompt: string, created_at?: string}>>([]);
  const [newAgentName, setNewAgentName] = useState('');
  const [newAgentPrompt, setNewAgentPrompt] = useState('');
  const [isCreatingAgent, setIsCreatingAgent] = useState(false);

  const [editingAgent, setEditingAgent] = useState<{id: number, name: string, prompt: string, created_at?: string} | null>(null);
  const [editAgentName, setEditAgentName] = useState('');
  const [editAgentPrompt, setEditAgentPrompt] = useState('');

  // Guardrails State
  const [guardrails, setGuardrails] = useState<Array<{id: number, name: string, prompt: string, created_at?: string}>>([]);
  const [newGuardrailName, setNewGuardrailName] = useState('');
  const [newGuardrailPrompt, setNewGuardrailPrompt] = useState('');
  const [isCreatingGuardrail, setIsCreatingGuardrail] = useState(false);

  const [editingGuardrail, setEditingGuardrail] = useState<{id: number, name: string, prompt: string, created_at?: string} | null>(null);
  const [editGuardrailName, setEditGuardrailName] = useState('');
  const [editGuardrailPrompt, setEditGuardrailPrompt] = useState('');

  // Voice State
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const [isVoiceProcessing, setIsVoiceProcessing] = useState(false);

  // Check valid token on load (optional: verify with backend)
  useEffect(() => {
    if (token) {
        setView('dashboard');
        fetch('/users/me', {
            headers: {
                'Authorization': `Bearer ${token}`,
                ...API_HEADERS
            }
        })
        .then(res => {
            if (res.ok) return res.json();
            // If token is invalid, we might want to logout, but for now just log error
            throw new Error('Failed to fetch user info');
        })
        .then(data => {
            setUsername(data.username);
        })
        .catch(console.error);
    }
  }, [token]);

  const [chatInput, setChatInput] = useState('');
  const [chatHistory, setChatHistory] = useState<Array<{role: string, content: string}>>([]);
  const [fullHistory, setFullHistory] = useState<Array<any>>([]);
  const [selectedSessions, setSelectedSessions] = useState<number[]>([]);
  const [historySearch, setHistorySearch] = useState('');
  const [nukeProgress, setNukeProgress] = useState(0);
  const nukeTimerRef = useRef<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  
  const [isNewSession, setIsNewSession] = useState(true);
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
      scrollToBottom();
  }, [chatHistory]);

  useEffect(() => {
    if (view === 'history' && token) {
        fetchHistory();
    }
    if (view === 'agents' && token) {
        fetchAgents();
    }
    if (view === 'guardrails' && token) {
        fetchGuardrails();
    }
    if (view === 'memories' && token) {
        fetchMemories();
    }
  }, [view, token]);

  const fetchMemories = () => {
    fetch('/api/memories/', {
        headers: {
            'Authorization': `Bearer ${token}`,
            ...API_HEADERS
        }
    })
    .then(res => res.json())
    .then(data => {
        setMemories(data);
        setSelectedMemories([]);
    })
    .catch(console.error);
  };
  
  // Client-side filtering for memories (like chat history)
  const filteredMemories = memories.filter((memory: any) => {
    if (!memorySearch.trim()) return true;
    const term = memorySearch.toLowerCase();
    return memory.content.toLowerCase().includes(term) || 
           memory.kind.toLowerCase().includes(term);
  });

  const handleCreateMemory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMemoryContent.trim()) return;

    try {
        const res = await fetch('/api/memories/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
                ...API_HEADERS
            },
            body: JSON.stringify({ content: newMemoryContent, kind: newMemoryKind })
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
      setSelectedMemories(prev => 
        prev.includes(id) ? prev.filter(m => m !== id) : [...prev, id]
      );
  };

  const handleDeleteSelectedMemories = async () => {
      if (selectedMemories.length === 0) return;
      if (!confirm(`Forget ${selectedMemories.length} memories?`)) return;

      try {
          const res = await fetch('/api/memories/selected/bulk', {
              method: 'DELETE',
              headers: {
                  'Content-Type': 'application/json',
                  'Authorization': `Bearer ${token}`,
                  ...API_HEADERS
              },
              body: JSON.stringify({ memory_ids: selectedMemories })
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
        progress += 4; // 25 steps * 40ms = 1000ms
        setNukeMemoriesProgress(progress);
        if (progress >= 100) {
            if(nukeMemoriesTimerRef.current) clearInterval(nukeMemoriesTimerRef.current);
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
              headers: {
                  'Authorization': `Bearer ${token}`,
                  ...API_HEADERS
              }
          });
          if (res.ok) {
              alert("MEMORIES NUKED");
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
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
                ...API_HEADERS
            },
            body: JSON.stringify({ content: editMemoryContent, kind: editMemoryKind })
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
    // The router prefix is /api/agents
    fetch('/api/agents/', { 
        headers: {
            'Authorization': `Bearer ${token}`,
            ...API_HEADERS
        }
    })
    .then(res => res.json())
    .then(data => setAgents(data))
    .catch(console.error);
  };

  const handleCreateAgent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newAgentName.trim() || !newAgentPrompt.trim()) return;

    try {
        const res = await fetch('/api/agents/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
                ...API_HEADERS
            },
            body: JSON.stringify({ name: newAgentName, prompt: newAgentPrompt })
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
      if(!confirm("Delete this agent?")) return;
      try {
          const res = await fetch(`/api/agents/${id}`, {
              method: 'DELETE',
              headers: {
                  'Authorization': `Bearer ${token}`,
                  ...API_HEADERS
              }
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
              headers: {
                  'Content-Type': 'application/json',
                  'Authorization': `Bearer ${token}`,
                  ...API_HEADERS
              },
              body: JSON.stringify({ name: editAgentName, prompt: editAgentPrompt })
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

  const fetchGuardrails = () => {
    fetch('/api/guardrails/', { 
        headers: {
            'Authorization': `Bearer ${token}`,
            ...API_HEADERS
        }
    })
    .then(res => res.json())
    .then(data => setGuardrails(data))
    .catch(console.error);
  };

  const handleCreateGuardrail = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newGuardrailName.trim() || !newGuardrailPrompt.trim()) return;

    try {
        const res = await fetch('/api/guardrails/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
                ...API_HEADERS
            },
            body: JSON.stringify({ name: newGuardrailName, prompt: newGuardrailPrompt })
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
      if(!confirm("Delete this guardrail?")) return;
      try {
          const res = await fetch(`/api/guardrails/${id}`, {
              method: 'DELETE',
              headers: {
                  'Authorization': `Bearer ${token}`,
                  ...API_HEADERS
              }
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
              headers: {
                  'Content-Type': 'application/json',
                  'Authorization': `Bearer ${token}`,
                  ...API_HEADERS
              },
              body: JSON.stringify({ name: editGuardrailName, prompt: editGuardrailPrompt })
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
      fetch('/api/chat/history', {
            headers: {
                'Authorization': `Bearer ${token}`,
                ...API_HEADERS
            }
        })
        .then(res => res.json())
        .then(data => {
            setFullHistory(data);
            setSelectedSessions([]);
        })
        .catch(console.error);
  }
  
  const filteredHistory = fullHistory.filter((session: any) => {
    if (!historySearch.trim()) return true;
    const term = historySearch.toLowerCase();
    
    // Check session ID
    if (session.id.toString().includes(term)) return true;
    
    // Check messages
    return session.messages.some((msg: any) => 
        msg.content.toLowerCase().includes(term) || 
        msg.role.toLowerCase().includes(term)
    );
  });

  const toggleSession = (id: number) => {
      setSelectedSessions(prev => 
        prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]
      );
  };

  const handleDeleteSelected = async () => {
      if (selectedSessions.length === 0) return;
      if (!confirm(`Delete ${selectedSessions.length} sessions?`)) return;

      try {
          const res = await fetch('/api/chat/sessions', {
              method: 'DELETE',
              headers: {
                  'Content-Type': 'application/json',
                  'Authorization': `Bearer ${token}`,
                  ...API_HEADERS
              },
              body: JSON.stringify({ session_ids: selectedSessions })
          });
          if (res.ok) {
              fetchHistory();
          }
      } catch (e) {
          console.error(e);
      }
  };

  const startNuke = () => {
    let progress = 0;
    if (nukeTimerRef.current) clearInterval(nukeTimerRef.current);
    
    nukeTimerRef.current = window.setInterval(() => {
        progress += 4; // 25 steps * 40ms = 1000ms
        setNukeProgress(progress);
        if (progress >= 100) {
            if(nukeTimerRef.current) clearInterval(nukeTimerRef.current);
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
              headers: {
                  'Authorization': `Bearer ${token}`,
                  ...API_HEADERS
              }
          });
          if (res.ok) {
              alert("HISTORY NUKED");
              fetchHistory();
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

  const loadSession = (session: any) => {
      // Load the session's messages into the chat window
      const messages = session.messages.map((msg: any) => ({
          role: msg.role,
          content: msg.content
      }));
      setChatHistory(messages);
      setCurrentSessionId(session.id);
      setIsNewSession(false);  // We're continuing an existing session
      setView('dashboard');
  };

  const handleChatSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;
    
    const userMessage = { role: 'user', content: chatInput };
    setChatHistory(prev => [...prev, userMessage]);
    setChatInput('');
    setIsLoading(true);

    try {
        const payload: { text: string; new_session: boolean; session_id?: number } = { 
            text: userMessage.content,
            new_session: isNewSession
        };
        
        // If we're continuing a specific session, include the session_id
        if (currentSessionId && !isNewSession) {
            payload.session_id = currentSessionId;
        }
        
        // Reset the flag immediately so subsequent messages in this session aren't treated as new
        if (isNewSession) setIsNewSession(false);

        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
                ...API_HEADERS
            },
            body: JSON.stringify(payload),
        });
        
        if (res.ok) {
            const data = await res.json();
            // Capture the session_id so subsequent messages go to the same session
            if (data.session_id && !currentSessionId) {
                setCurrentSessionId(data.session_id);
            }
            if (data.response) {
                setChatHistory(prev => [...prev, { role: 'Arthur', content: data.response.content }]);
            }
        } else {
            console.error("Failed to send chat message");
            setChatHistory(prev => [...prev, { role: 'Arthur', content: 'I am having trouble communicating with the model provider.' }]);
        }
    } catch (err) {
        console.error(err);
        setChatHistory(prev => [...prev, { role: 'Arthur', content: 'I am having trouble communicating with the model provider.' }]);
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
        headers: { 
            'Content-Type': 'application/x-www-form-urlencoded',
            ...API_HEADERS
        },
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
        headers: { 
            'Content-Type': 'application/json',
            ...API_HEADERS
        },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || 'Registration failed');
      }
      alert('Account created! Please login.');
      setView('login');
      setError('');
    } catch (err: any) {
      setError(err.message);
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
      if(!confirm("Are you sure? This cannot be undone.")) return;
      try {
          const res = await fetch('/users/me', {
              method: 'DELETE',
              headers: { 
                  'Authorization': `Bearer ${token}`,
                  ...API_HEADERS
              }
          });
          if(res.ok) handleLogout();
          else alert("Failed to delete");
      } catch(e) {
          alert("Error deleting account");
      }
  }

  // Voice recording functions
  const startRecording = async () => {
      // Check for secure context (required for getUserMedia on non-localhost)
      if (!window.isSecureContext && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
          alert("Microphone access blocked: You are accessing this site via an insecure connection (HTTP). Browsers require HTTPS for microphone access on mobile devices. Please use HTTPS or localhost.");
          return;
      }

      try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          const mediaRecorder = new MediaRecorder(stream);
          mediaRecorderRef.current = mediaRecorder;
          chunksRef.current = [];

          mediaRecorder.ondataavailable = (e) => {
              if (e.data.size > 0) {
                  chunksRef.current.push(e.data);
              }
          };

          mediaRecorder.start();
          setIsRecording(true);
      } catch (err) {
          console.error("Error accessing microphone:", err);
          let msg = "Could not access microphone.";
          if (!window.isSecureContext) {
             msg += " This may be due to using HTTP instead of HTTPS.";
          }
          alert(msg + " Please check permissions and connection security.");
      }
  };

//   const stopRecording = async () => {
//       if (!mediaRecorderRef.current) return;

//       mediaRecorderRef.current.onstop = async () => {
//           const audioBlob = new Blob(chunksRef.current, { type: 'audio/wav' });
//           setIsRecording(false);
          
//           // Send to backend
//           const formData = new FormData();
//           formData.append('file', audioBlob, 'recording.wav');

//           try {
//               // Use non-streaming endpoint (much faster with GPU - 87x speedup!)
//               const res = await fetch('/api/chat/voice', {
//                   method: 'POST',
//                   headers: {
//                       'Authorization': `Bearer ${token}`,
//                   },
//                   body: formData
//               });

//               if (res.ok) {
//                   const data = await res.json();
                  
//                   // Update session state
//                   if (data.session_id) {
//                       setCurrentSessionId(data.session_id);
//                       setIsNewSession(false);
//                   }

//                   console.log("Transcribed:", data.response?.content);

//                   // Play audio if available
//                   if (data.audio_base64) {
//                       // Decode base64 to binary
//                       const binaryString = atob(data.audio_base64);
//                       const bytes = new Uint8Array(binaryString.length);
//                       for (let i = 0; i < binaryString.length; i++) {
//                           bytes[i] = binaryString.charCodeAt(i);
//                       }
                      
//                       // Create blob and play
//                       const audioBlob = new Blob([bytes], { type: 'audio/wav' });
//                       const audioUrl = URL.createObjectURL(audioBlob);
//                       const audio = new Audio(audioUrl);
                      
//                       audio.play().catch(e => console.error("Error playing audio:", e));
                      
//                       // Cleanup when done
//                       audio.onended = () => URL.revokeObjectURL(audioUrl);
//                   }
                  
//                   console.log("Voice processed successfully");
//               } else {
//                   console.error("Voice processing failed:", res.status, res.statusText);
//               }
//           } catch (e) {
//               console.error("Voice processing error:", e);
//           }
          
//           // Stop all tracks
//           mediaRecorderRef.current?.stream.getTracks().forEach(track => track.stop());
//       };

//       mediaRecorderRef.current.stop();
//   };

const stopRecording = async () => {
    if (!mediaRecorderRef.current) return;

    mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(chunksRef.current, { type: 'audio/wav' });
        setIsRecording(false);
        setIsVoiceProcessing(true);
        
        // Send to backend
        const formData = new FormData();
        formData.append('file', audioBlob, 'recording.wav');

        try {
            // Use streaming endpoint for lower latency
            const res = await fetch('/api/chat/voice/stream', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    // Don't include Content-Type - let browser set it for FormData
                },
                body: formData
            });

            if (res.ok) {
                // Extract metadata from headers
                const sessionId = res.headers.get('X-Session-ID');
                const transcribedText = res.headers.get('X-Transcribed-Text');
                
                if (sessionId) {
                    setCurrentSessionId(parseInt(sessionId));
                    setIsNewSession(false);
                }

                console.log("Transcribed:", transcribedText);

                // Stream audio response - play chunks as they arrive
                // Backend sends length-prefixed chunks: 4 bytes (uint32 LE) + N bytes PCM
                if (res.body) {
                    try {
                        const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
                        const sampleRate = 24000; // From backend
                        const reader = res.body.getReader();
                        
                        let nextStartTime = 0;
                        let chunkCount = 0;
                        let playbackStarted = false;
                        const bufferChunks = 1; // Buffer 2 chunks before starting for smoother playback
                        const bufferedAudioBuffers: AudioBuffer[] = [];
                        
                        // Buffer for accumulating incoming bytes (HTTP may split/combine chunks)
                        let pendingBytes = new Uint8Array(0);
                        
                        console.log("Starting audio stream playback with length-prefixed framing...");
                        
                        const createAudioBuffer = (pcmData: Uint8Array): AudioBuffer | null => {
                            // Ensure the byte length is a multiple of 2 (int16 size)
                            if (pcmData.length % 2 !== 0) {
                                console.warn(`PCM data has invalid length: ${pcmData.length} bytes (not multiple of 2)`);
                                return null;
                            }
                            
                            // Convert int16 PCM to float32 for Web Audio API
                            // Need to create a properly aligned view
                            const alignedBuffer = new ArrayBuffer(pcmData.length);
                            new Uint8Array(alignedBuffer).set(pcmData);
                            const int16Array = new Int16Array(alignedBuffer);
                            const float32Array = new Float32Array(int16Array.length);
                            
                            // Convert int16 [-32768, 32767] to float32 [-1.0, 1.0]
                            for (let i = 0; i < int16Array.length; i++) {
                                float32Array[i] = int16Array[i] / 32768.0;
                            }
                            
                            // Create AudioBuffer from the float32 samples
                            const audioBuffer = audioContext.createBuffer(1, float32Array.length, sampleRate);
                            audioBuffer.getChannelData(0).set(float32Array);
                            return audioBuffer;
                        };
                        
                        const scheduleAudioBuffer = (audioBuffer: AudioBuffer) => {
                            const source = audioContext.createBufferSource();
                            source.buffer = audioBuffer;
                            source.connect(audioContext.destination);
                            
                            const now = audioContext.currentTime;
                            const startTime = Math.max(now + 0.01, nextStartTime);
                            
                            source.start(startTime);
                            nextStartTime = startTime + audioBuffer.duration;
                            
                            chunkCount++;
                            if (chunkCount <= 5 || chunkCount % 10 === 0) {
                                console.log(`Chunk ${chunkCount}: ${audioBuffer.length} samples, duration ${audioBuffer.duration.toFixed(3)}s`);
                            }
                        };
                        
                        // Extract complete audio chunks from the buffer using length prefixes
                        const processBuffer = () => {
                            const chunks: Uint8Array[] = [];
                            
                            while (pendingBytes.length >= 4) {
                                // Read length prefix (uint32 little-endian)
                                const dataView = new DataView(pendingBytes.buffer, pendingBytes.byteOffset, 4);
                                const chunkLength = dataView.getUint32(0, true); // little-endian
                                
                                // Check if we have the complete chunk
                                if (pendingBytes.length < 4 + chunkLength) {
                                    break; // Wait for more data
                                }
                                
                                // Extract the PCM data (skip 4-byte length prefix)
                                const pcmData = pendingBytes.slice(4, 4 + chunkLength);
                                chunks.push(pcmData);
                                
                                // Remove processed bytes from buffer
                                pendingBytes = pendingBytes.slice(4 + chunkLength);
                            }
                            
                            return chunks;
                        };
                        
                        // Read and play chunks as they arrive
                        while (true) {
                            const { done, value } = await reader.read();
                            
                            if (done) {
                                // Process any remaining data
                                const finalChunks = processBuffer();
                                for (const pcmData of finalChunks) {
                                    const audioBuffer = createAudioBuffer(pcmData);
                                    if (audioBuffer) {
                                        scheduleAudioBuffer(audioBuffer);
                                    }
                                }
                                console.log(`Streaming complete. Played ${chunkCount} chunks.`);
                                setIsVoiceProcessing(false);
                                break;
                            }
                            
                            if (value && value.length > 0) {
                                // Append new data to pending buffer
                                const newBuffer = new Uint8Array(pendingBytes.length + value.length);
                                newBuffer.set(pendingBytes);
                                newBuffer.set(value, pendingBytes.length);
                                pendingBytes = newBuffer;
                                
                                // Extract and play complete chunks
                                const completeChunks = processBuffer();
                                
                                for (const pcmData of completeChunks) {
                                    const audioBuffer = createAudioBuffer(pcmData);
                                    if (!audioBuffer) continue;
                                    
                                    if (!playbackStarted) {
                                        // Buffer initial chunks for smoother start
                                        bufferedAudioBuffers.push(audioBuffer);
                                        console.log(`Buffering chunk ${bufferedAudioBuffers.length}/${bufferChunks}...`);
                                        
                                        if (bufferedAudioBuffers.length >= bufferChunks) {
                                            // Start playback - schedule all buffered chunks
                                            playbackStarted = true;
                                            nextStartTime = audioContext.currentTime + 0.05;
                                            console.log(`Starting playback at ${nextStartTime.toFixed(3)}s`);
                                            
                                            for (const buf of bufferedAudioBuffers) {
                                                scheduleAudioBuffer(buf);
                                            }
                                            bufferedAudioBuffers.length = 0;
                                        }
                                    } else {
                                        // Playback already started, schedule immediately
                                        scheduleAudioBuffer(audioBuffer);
                                    }
                                }
                            }
                        }
                        
                    } catch (e) {
                        console.error("Error processing streaming audio:", e);
                        setIsVoiceProcessing(false);
                    }
                }

                console.log("Voice processed successfully");
                
            } else {
                console.error("Voice processing failed:", res.status, res.statusText);
                setIsVoiceProcessing(false);
            }
        } catch (e) {
            console.error("Voice processing error:", e);
            setIsVoiceProcessing(false);
        }
        
        // Stop all tracks
        mediaRecorderRef.current?.stream.getTracks().forEach(track => track.stop());
    };

    mediaRecorderRef.current.stop();
};

  if (['dashboard', 'history', 'agents', 'guardrails', 'memories', 'settings', 'voice'].includes(view)) {
    return (
      <div className="app-layout">
        <header className="mobile-header">
            <button className="menu-btn" onClick={() => setIsSidebarOpen(true)}>
                <IconMenu />
            </button>
            <span className="mobile-brand">Arthur Prime</span>
        </header>
        
        {isSidebarOpen && <div className="sidebar-overlay" onClick={() => setIsSidebarOpen(false)} />}

        <aside className={`sidebar ${isSidebarOpen ? 'open' : ''}`}>
            <div className="sidebar-header">
                <IconCat />
                <div className="brand-text">
                    <strong>Arthur Prime</strong><br/>
                </div>
            </div>

            <nav className="sidebar-nav">
                <button 
                    className={`nav-item ${view === 'voice' ? 'active' : ''}`}
                    onClick={() => {
                        setView('voice');
                        setIsSidebarOpen(false);
                    }}
                >
                    <IconVoice />
                    <span>Voice</span>
                </button>
                <button 
                    className={`nav-item ${view === 'dashboard' ? 'active' : ''}`}
                    onClick={() => {
                        setView('dashboard');
                        setIsSidebarOpen(false);
                    }}
                >
                    <IconDashboard />
                    <span>Chat</span>
                </button>
                <button 
                    className={`nav-item ${view === 'history' ? 'active' : ''}`}
                    onClick={() => {
                        setView('history');
                        setIsSidebarOpen(false);
                    }}
                >
                    <IconHistory />
                    <span>Chat History</span>
                </button>
                <button 
                    className={`nav-item ${view === 'memories' ? 'active' : ''}`}
                    onClick={() => {
                        setView('memories');
                        setIsSidebarOpen(false);
                    }}
                >
                    <IconBrain />
                    <span>Memories</span>
                </button>
                <button 
                    className={`nav-item ${view === 'agents' ? 'active' : ''}`}
                    onClick={() => {
                        setView('agents');
                        setIsSidebarOpen(false);
                    }}
                >
                    <IconAgents />
                    <span>Agents</span>
                </button>
                <button 
                    className={`nav-item ${view === 'guardrails' ? 'active' : ''}`}
                    onClick={() => {
                        setView('guardrails');
                        setIsSidebarOpen(false);
                    }}
                >
                    <IconGuardrails />
                    <span>Guardrails</span>
                </button>
                <button 
                    className={`nav-item ${view === 'settings' ? 'active' : ''}`}
                    onClick={() => {
                        setView('settings');
                        setIsSidebarOpen(false);
                    }}
                >
                    <IconSettings />
                    <span>Settings</span>
                </button>
            </nav>

            <div className="sidebar-footer">
                <div className="user-profile">
                    <div className="avatar">{(username?.[0] || 'U').toUpperCase()}</div>
                    <div className="user-info">
                        <span className="user-name">{username}</span>
                        <button className="logout-btn" onClick={handleLogout} title="Logout">Log out</button>
                    </div>
                </div>
            </div>
        </aside>

        <main className="main-content">
            {view === 'voice' && (
                <div className="voice-interface" style={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%', position: 'relative' }}>
                    <div style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0, zIndex: 1 }}>
                        <Antigravity
                            count={1000}
                            magnetRadius={21}
                            ringRadius={5}
                            waveSpeed={5}
                            waveAmplitude={5}
                            particleSize={1.3}
                            lerpSpeed={0.02}
                            color="#616375"
                            autoAnimate={false}
                            particleVariance={0.5}
                            rotationSpeed={0.1}
                            depthFactor={1}
                            pulseSpeed={10}
                            particleShape="sphere"
                            fieldStrength={10}
                            isProcessing={isVoiceProcessing}
                        />
                    </div>
                    
                    <div style={{ 
                        position: 'absolute', 
                        bottom: '40px', 
                        left: '50%', 
                        transform: 'translateX(-50%)', 
                        zIndex: 10,
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        gap: '1rem'
                    }}>
                        <button
                            onMouseDown={startRecording}
                            onMouseUp={stopRecording}
                            onMouseLeave={stopRecording}
                            onTouchStart={startRecording}
                            onTouchEnd={stopRecording}
                            style={{
                                width: '80px',
                                height: '80px',
                                borderRadius: '50%',
                                border: 'none',
                                background: isRecording ? '#ef4444' : 'white',
                                color: isRecording ? 'white' : '#333',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                cursor: 'pointer',
                                boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
                                transition: 'all 0.2s ease',
                                transform: isRecording ? 'scale(1.1)' : 'scale(1)'
                            }}
                        >
                            <Mic size={32} />
                        </button>
                        <span style={{ 
                            color: 'white', 
                            textShadow: '0 1px 2px rgba(0,0,0,0.5)',
                            fontWeight: 500
                        }}>
                            {isRecording ? 'Listening...' : 'Hold to Speak'}
                        </span>
                    </div>
                </div>
            )}

            {view === 'dashboard' && (
                <div className="chat-interface">
                    <header className="chat-header">
                        <div>
                            <h1>Arthur Prime</h1>
                        </div>
                        <button 
                            onClick={handleNewChat}
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
                                gap: '0.5rem'
                            }}
                        >
                            <IconNewChat />
                            <span style={{ fontSize: '0.9rem', fontWeight: 500 }}>New Chat</span>
                        </button>
                    </header>

                    <div className="chat-area">
                        {chatHistory.length === 0 && (
                            <div className="chat-message assistant">
                                <div className="message-icon"><IconCat /></div>
                                <div className="message-content">Arthur Prime at your service! (Markdown supported)</div>
                            </div>
                        )}
                        {chatHistory.map((msg, i) => (
                            <div key={i} className={`chat-message ${msg.role}`}>
                                {(msg.role === 'assistant' || msg.role === 'Arthur') && <div className="message-icon"><IconCat /></div>}
                                <div className="message-content"><ReactMarkdown>{msg.content}</ReactMarkdown></div>
                            </div>
                        ))}
                        {isLoading && (
                            <div className="chat-message assistant">
                                <div className="message-icon"><IconCat /></div>
                                <TypingIndicator />
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    <div className="input-area">
                        <form onSubmit={handleChatSubmit} className="chat-input-wrapper">
                            <textarea 
                                value={chatInput} 
                                onChange={(e) => {
                                    setChatInput(e.target.value);
                                    // Auto-resize textarea
                                    e.target.style.height = 'auto';
                                    e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px';
                                }} 
                                onKeyDown={(e) => {
                                    // Submit on Enter, new line on Shift+Enter
                                    if (e.key === 'Enter' && !e.shiftKey) {
                                        e.preventDefault();
                                        handleChatSubmit(e);
                                    }
                                }}
                                placeholder="Type your message..." 
                                rows={1}
                            />
                            {/* <button type="submit" className="send-btn"> */}
                                <Send color="#000000" strokeWidth={1} className="send-btn"/>
                            {/* </button> */}
                        </form>
                    </div>
                </div>
            )}
            
            {view === 'history' && (
                <div className="history-view" style={{ padding: '2rem', overflowY: 'auto', display: 'flex', flexDirection: 'column', height: '100%', boxSizing: 'border-box' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                        <h2>Chat History</h2>
                        <button 
                            onClick={handleDeleteSelected}
                            disabled={selectedSessions.length === 0}
                            style={{
                                backgroundColor: selectedSessions.length > 0 ? '#ef4444' : '#e2e8f0',
                                color: selectedSessions.length > 0 ? 'white' : '#94a3b8',
                                border: 'none',
                                padding: '0.5rem 1rem',
                                borderRadius: '4px',
                                cursor: selectedSessions.length > 0 ? 'pointer' : 'not-allowed',
                                fontWeight: '600'
                            }}
                        >
                            Delete Selected ({selectedSessions.length})
                        </button>
                    </div>

                    <div style={{ marginBottom: '2rem' }}>
                        <input 
                            type="text" 
                            value={historySearch}
                            onChange={(e) => setHistorySearch(e.target.value)}
                            placeholder="Search history..."
                            style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid #cbd5e1' }}
                        />
                    </div>

                    <div className="history-list" style={{ flex: 1, overflowY: 'auto' }}>
                        {filteredHistory.map((session: any) => (
                            <div key={session.id} style={{ display: 'flex', gap: '1rem', marginBottom: '2rem', alignItems: 'flex-start' }}>
                                <input 
                                    type="checkbox" 
                                    checked={selectedSessions.includes(session.id)}
                                    onChange={() => toggleSession(session.id)}
                                    style={{ marginTop: '1rem', width: '20px', height: '20px' }}
                                />
                                <div style={{ flex: 1, border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1rem', background: 'white' }}>
                                    <div style={{ borderBottom: '1px solid #eee', paddingBottom: '0.5rem', marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                        <span style={{ color: '#64748b', fontSize: '0.9rem' }}>
                                            Session {session.id} • {session.created_at}
                                        </span>
                                        <button
                                            onClick={() => loadSession(session)}
                                            style={{
                                                background: '#3b82f6',
                                                color: 'white',
                                                border: 'none',
                                                padding: '0.25rem 0.75rem',
                                                borderRadius: '4px',
                                                fontSize: '0.8rem',
                                                fontWeight: '500',
                                                cursor: 'pointer'
                                            }}
                                        >
                                            Continue
                                        </button>
                                    </div>
                                    {session.messages.map((msg: any, i: number) => (
                                        <div key={i} style={{ marginBottom: '0.5rem', fontFamily: 'monospace', fontSize: '0.9rem' }}>
                                            <div style={{ color: '#94a3b8', fontSize: '0.8rem' }}>{msg.created_at}</div>
                                            <div><strong>{msg.role}:</strong> <ReactMarkdown components={{ p: ({ children }) => <span>{children}</span> }}>{msg.content}</ReactMarkdown></div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>

                    <div style={{ marginTop: '2rem', textAlign: 'center' }}>
                        <button
                            onMouseDown={startNuke}
                            onMouseUp={cancelNuke}
                            onMouseLeave={cancelNuke}
                            onTouchStart={startNuke}
                            onTouchEnd={cancelNuke}
                            style={{
                                background: `linear-gradient(to right, #dc2626 ${nukeProgress}%, #ef4444 ${nukeProgress}%)`,
                                color: 'white',
                                border: 'none',
                                padding: '.5rem',
                                width: '100%',
                                maxWidth: '200px',
                                borderRadius: '4px',
                                fontSize: '1.2rem',
                                fontWeight: 'bold',
                                cursor: 'pointer',
                                transition: 'background 0.1s linear',
                                userSelect: 'none'
                            }}
                        >
                            {nukeProgress > 0 ? `HOLD TO NUKE... ${nukeProgress}%` : 'NUKE HISTORY'}
                        </button>
                        <p style={{ color: '#64748b', fontSize: '0.8rem', marginTop: '0.5rem' }}>Press and hold to delete all history</p>
                    </div>
                </div>
            )}

            {view === 'memories' && (
                <div className="memories-view" style={{ padding: '2rem', overflowY: 'auto', display: 'flex', flexDirection: 'column', height: '100%', boxSizing: 'border-box' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                        <h2>Memories</h2>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <button 
                                onClick={handleDeleteSelectedMemories}
                                disabled={selectedMemories.length === 0}
                                style={{
                                    backgroundColor: selectedMemories.length > 0 ? '#ef4444' : '#e2e8f0',
                                    color: selectedMemories.length > 0 ? 'white' : '#94a3b8',
                                    border: 'none',
                                    padding: '0.5rem 1rem',
                                    borderRadius: '4px',
                                    cursor: selectedMemories.length > 0 ? 'pointer' : 'not-allowed',
                                    fontWeight: '600'
                                }}
                            >
                                Delete Selected ({selectedMemories.length})
                            </button>
                            <button 
                                onClick={() => setIsCreatingMemory(!isCreatingMemory)}
                                className="primary-btn"
                                style={{ 
                                  width: 'auto',
                                  padding: '.5rem'
                                 }}
                            >
                                {isCreatingMemory ? 'Cancel' : 'Add Memory'}
                            </button>
                        </div>
                    </div>

                    <div style={{ marginBottom: '2rem' }}>
                        <input 
                            type="text" 
                            value={memorySearch}
                            onChange={(e) => setMemorySearch(e.target.value)}
                            placeholder="Search memories..."
                            style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid #cbd5e1' }}
                        />
                    </div>

                    {isCreatingMemory && (
                        <div style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', border: '1px solid #e2e8f0', marginBottom: '2rem' }}>
                            <h3>New Memory</h3>
                            <form onSubmit={handleCreateMemory}>
                                <div className="form-group">
                                    <label style={{ color: '#1e293b' }}>Type</label>
                                    <select
                                        value={newMemoryKind}
                                        onChange={e => setNewMemoryKind(e.target.value)}
                                        style={{
                                            width: '100%',
                                            padding: '0.5rem',
                                            borderRadius: '4px',
                                            border: '1px solid #cbd5e1',
                                            background: 'white',
                                            color: '#1e293b',
                                            marginBottom: '1rem'
                                        }}
                                    >
                                        <option value="fact">Fact</option>
                                        <option value="episode">Episode</option>
                                        <option value="open_loop">Open Loop</option>
                                    </select>
                                </div>
                                <div className="form-group">
                                    <label style={{ color: '#1e293b' }}>Content</label>
                                    <textarea 
                                        value={newMemoryContent} 
                                        onChange={e => setNewMemoryContent(e.target.value)} 
                                        placeholder="I like coffee with oat milk..."
                                        style={{ 
                                            width: '100%', 
                                            padding: '0.5rem', 
                                            borderRadius: '4px', 
                                            border: '1px solid #cbd5e1', 
                                            minHeight: '100px',
                                            fontFamily: 'inherit'
                                        }}
                                        required
                                    />
                                </div>
                                <button type="submit" className="primary-btn">Save Memory</button>
                            </form>
                        </div>
                    )}

{editingMemory && (
                        <div style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', border: '1px solid #e2e8f0', marginBottom: '2rem' }}>
                            <h3>Edit Memory</h3>
                            <form onSubmit={handleUpdateMemory}>
                                <div className="form-group">
                                    <label style={{ color: '#1e293b' }}>Type</label>
                                    <select
                                        value={editMemoryKind}
                                        onChange={e => setEditMemoryKind(e.target.value)}
                                        style={{
                                            width: '100%',
                                            padding: '0.5rem',
                                            borderRadius: '4px',
                                            border: '1px solid #cbd5e1',
                                            background: 'white',
                                            color: '#1e293b',
                                            marginBottom: '1rem'
                                        }}
                                    >
                                        <option value="fact">Fact</option>
                                        <option value="episode">Episode</option>
                                        <option value="open_loop">Open Loop</option>
                                    </select>
                                </div>
                                <div className="form-group">
                                    <label style={{ color: '#1e293b' }}>Content</label>
                                    <textarea 
                                        value={editMemoryContent} 
                                        onChange={e => setEditMemoryContent(e.target.value)} 
                                        style={{ 
                                            width: '100%', 
                                            padding: '0.5rem', 
                                            borderRadius: '4px', 
                                            border: '1px solid #cbd5e1', 
                                            minHeight: '100px',
                                            fontFamily: 'inherit'
                                        }}
                                        required
                                    />
                                </div>
                                <button type="submit" className="primary-btn">Update Memory</button>
                            </form>
                        </div>
                    )}

                    <div className="memories-list" style={{ flex: 1, overflowY: 'auto' }}>
                        {filteredMemories.map((memory: any) => (
                            <div key={memory.id} style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', alignItems: 'flex-start' }}>
                                <input 
                                    type="checkbox" 
                                    checked={selectedMemories.includes(memory.id)}
                                    onChange={() => toggleMemory(memory.id)}
                                    style={{ marginTop: '1.5rem', width: '20px', height: '20px', flexShrink: 0 }}
                                />
                                <div style={{ flex: 1, background: 'white', padding: '1.5rem', borderRadius: '8px', border: '1px solid #e2e8f0', position: 'relative' }}>
                                <button 
                                        onClick={() => {
                                            setEditingMemory(memory);
                                            setEditMemoryContent(memory.content);
                                            setEditMemoryKind(memory.kind);
                                        }}
                                        style={{ position: 'absolute', top: '0.5rem', right: '0.5rem', background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8' }}
                                        title="Edit Memory"
                                    >
                                        <Pencil size={16} />
                                    </button>
                                    <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.5rem' }}>
                                        {new Date(memory.created_at).toLocaleDateString()} • {memory.kind}
                                    </div>
                                    <div style={{ fontSize: '0.9rem', color: '#64748b', whiteSpace: 'pre-wrap', maxHeight: '150px', overflowY: 'auto' }}>
                                        {memory.content}
                                    </div>
                                </div>
                            </div>
                        ))}
                        {filteredMemories.length === 0 && !isCreatingMemory && (
                            <div style={{ textAlign: 'center', color: '#94a3b8', padding: '2rem' }}>
                                No memories found.
                            </div>
                        )}
                    </div>

                    <div style={{ marginTop: '2rem', textAlign: 'center' }}>
                        <button
                            onMouseDown={startNukeMemories}
                            onMouseUp={cancelNukeMemories}
                            onMouseLeave={cancelNukeMemories}
                            onTouchStart={startNukeMemories}
                            onTouchEnd={cancelNukeMemories}
                            style={{
                                background: `linear-gradient(to right, #dc2626 ${nukeMemoriesProgress}%, #ef4444 ${nukeMemoriesProgress}%)`,
                                color: 'white',
                                border: 'none',
                                padding: '.5rem',
                                width: '100%',
                                maxWidth: '200px',
                                borderRadius: '4px',
                                fontSize: '1.2rem',
                                fontWeight: 'bold',
                                cursor: 'pointer',
                                transition: 'background 0.1s linear',
                                userSelect: 'none'
                            }}
                        >
                            {nukeMemoriesProgress > 0 ? `HOLD TO NUKE... ${nukeMemoriesProgress}%` : 'NUKE MEMORIES'}
                        </button>
                        <p style={{ color: '#64748b', fontSize: '0.8rem', marginTop: '0.5rem' }}>Press and hold to delete all memories</p>
                    </div>
                </div>
            )}

            {view === 'agents' && (
                <div className="agents-view" style={{ padding: '2rem', overflowY: 'auto', height: '100%', boxSizing: 'border-box' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                        <h2>Agents</h2>
                        <button 
                            onClick={() => setIsCreatingAgent(!isCreatingAgent)}
                            className="primary-btn"
                            style={{ 
                              width: 'auto',
                              padding: '.5rem'
                             }}
                        >
                            {isCreatingAgent ? 'Cancel' : 'Create Agent'}
                        </button>
                    </div>

                    {isCreatingAgent && (
                        <div style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', border: '1px solid #e2e8f0', marginBottom: '2rem' }}>
                            <h3>New Agent</h3>
                            <form onSubmit={handleCreateAgent}>
                                <div className="form-group">
                                    <label style={{ color: '#1e293b' }}>Name</label>
                                    <input 
                                        value={newAgentName} 
                                        onChange={e => setNewAgentName(e.target.value)} 
                                        placeholder="e.g. Creative Writer"
                                        style={{ background: 'white', color: '#1e293b', border: '1px solid #cbd5e1' }}
                                        required
                                    />
                                </div>
                                <div className="form-group">
                                    <label style={{ color: '#1e293b' }}>Prompt</label>
                                    <textarea 
                                        value={newAgentPrompt} 
                                        onChange={e => setNewAgentPrompt(e.target.value)} 
                                        placeholder="You are a helpful creative writer..."
                                        style={{ 
                                            width: '100%', 
                                            padding: '0.5rem', 
                                            borderRadius: '4px', 
                                            border: '1px solid #cbd5e1', 
                                            minHeight: '100px',
                                            fontFamily: 'inherit'
                                        }}
                                        required
                                    />
                                </div>
                                <button type="submit" className="primary-btn">Save Agent</button>
                            </form>
                        </div>
                    )}

{editingAgent && (
                        <div style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', border: '1px solid #e2e8f0', marginBottom: '2rem' }}>
                            <h3>Edit Agent</h3>
                            <form onSubmit={handleUpdateAgent}>
                                <div className="form-group">
                                    <label style={{ color: '#1e293b' }}>Name</label>
                                    <input 
                                        value={editAgentName} 
                                        onChange={e => setEditAgentName(e.target.value)} 
                                        style={{ background: 'white', color: '#1e293b', border: '1px solid #cbd5e1' }}
                                        required
                                    />
                                </div>
                                <div className="form-group">
                                    <label style={{ color: '#1e293b' }}>Prompt</label>
                                    <textarea 
                                        value={editAgentPrompt} 
                                        onChange={e => setEditAgentPrompt(e.target.value)} 
                                        style={{ 
                                            width: '100%', 
                                            padding: '0.5rem', 
                                            borderRadius: '4px', 
                                            border: '1px solid #cbd5e1', 
                                            minHeight: '100px',
                                            fontFamily: 'inherit'
                                        }}
                                        required
                                    />
                                </div>
                                <button type="submit" className="primary-btn">Update Agent</button>
                            </form>
                        </div>
                    )}

                    <div className="agents-list" style={{ display: 'grid', gap: '1rem', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))' }}>
                        {agents.map(agent => (
                            <div key={agent.id} style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', border: '1px solid #e2e8f0', position: 'relative' }}>
                                <button 
                                    onClick={() => handleDeleteAgent(agent.id)}
                                    style={{ position: 'absolute', top: '1rem', right: '1rem', background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8' }}
                                    title="Delete Agent"
                                >
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                                </button>
                                <button 
                                    onClick={() => {
                                        setEditingAgent(agent);
                                        setEditAgentName(agent.name);
                                        setEditAgentPrompt(agent.prompt);
                                    }}
                                    style={{ position: 'absolute', top: '1rem', right: '3rem', background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8' }}
                                    title="Edit Agent"
                                >
                                    <Pencil size={16} />
                                </button>
                                <h3 style={{ margin: '0 0 0.5rem 0' }}>{agent.name}</h3>
                                <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.5rem' }}>
                                    Created: {new Date(agent.created_at || Date.now()).toLocaleDateString()}
                                </div>
                                <div style={{ fontSize: '0.9rem', color: '#64748b', whiteSpace: 'pre-wrap', maxHeight: '150px', overflowY: 'auto' }}>
                                    {agent.prompt}
                                </div>
                            </div>
                        ))}
                        {agents.length === 0 && !isCreatingAgent && (
                            <div style={{ gridColumn: '1/-1', textAlign: 'center', color: '#94a3b8', padding: '2rem' }}>
                                No agents found. Create one to get started.
                            </div>
                        )}
                    </div>
                </div>
            )}

            {view === 'guardrails' && (
                <div className="guardrails-view" style={{ padding: '2rem', overflowY: 'auto', height: '100%', boxSizing: 'border-box' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                        <h2>Guardrails</h2>
                        <button 
                            onClick={() => setIsCreatingGuardrail(!isCreatingGuardrail)}
                            className="primary-btn"
                            style={{ 
                              width: 'auto',
                              padding: '.5rem'
                             }}
                        >
                            {isCreatingGuardrail ? 'Cancel' : 'Create Guardrail'}
                        </button>
                    </div>

                    {isCreatingGuardrail && (
                        <div style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', border: '1px solid #e2e8f0', marginBottom: '2rem' }}>
                            <h3>New Guardrail</h3>
                            <form onSubmit={handleCreateGuardrail}>
                                <div className="form-group">
                                    <label style={{ color: '#1e293b' }}>Name</label>
                                    <input 
                                        value={newGuardrailName} 
                                        onChange={e => setNewGuardrailName(e.target.value)} 
                                        placeholder="e.g. Safety Filter"
                                        style={{ background: 'white', color: '#1e293b', border: '1px solid #cbd5e1' }}
                                        required
                                    />
                                </div>
                                <div className="form-group">
                                    <label style={{ color: '#1e293b' }}>Rule/Prompt</label>
                                    <textarea 
                                        value={newGuardrailPrompt} 
                                        onChange={e => setNewGuardrailPrompt(e.target.value)} 
                                        placeholder="Never provide harmful, illegal, or unethical advice..."
                                        style={{ 
                                            width: '100%', 
                                            padding: '0.5rem', 
                                            borderRadius: '4px', 
                                            border: '1px solid #cbd5e1', 
                                            minHeight: '100px',
                                            fontFamily: 'inherit'
                                        }}
                                        required
                                    />
                                </div>
                                <button type="submit" className="primary-btn">Save Guardrail</button>
                            </form>
                        </div>
                    )}

{editingGuardrail && (
                        <div style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', border: '1px solid #e2e8f0', marginBottom: '2rem' }}>
                            <h3>Edit Guardrail</h3>
                            <form onSubmit={handleUpdateGuardrail}>
                                <div className="form-group">
                                    <label style={{ color: '#1e293b' }}>Name</label>
                                    <input 
                                        value={editGuardrailName} 
                                        onChange={e => setEditGuardrailName(e.target.value)} 
                                        style={{ background: 'white', color: '#1e293b', border: '1px solid #cbd5e1' }}
                                        required
                                    />
                                </div>
                                <div className="form-group">
                                    <label style={{ color: '#1e293b' }}>Rule/Prompt</label>
                                    <textarea 
                                        value={editGuardrailPrompt} 
                                        onChange={e => setEditGuardrailPrompt(e.target.value)} 
                                        style={{ 
                                            width: '100%', 
                                            padding: '0.5rem', 
                                            borderRadius: '4px', 
                                            border: '1px solid #cbd5e1', 
                                            minHeight: '100px',
                                            fontFamily: 'inherit'
                                        }}
                                        required
                                    />
                                </div>
                                <button type="submit" className="primary-btn">Update Guardrail</button>
                            </form>
                        </div>
                    )}

                    <div className="guardrails-list" style={{ display: 'grid', gap: '1rem', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))' }}>
                        {guardrails.map(guardrail => (
                            <div key={guardrail.id} style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', border: '1px solid #e2e8f0', position: 'relative' }}>
                                <button 
                                    onClick={() => handleDeleteGuardrail(guardrail.id)}
                                    style={{ position: 'absolute', top: '1rem', right: '1rem', background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8' }}
                                    title="Delete Guardrail"
                                >
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                                </button>
                                <button 
                                    onClick={() => {
                                        setEditingGuardrail(guardrail);
                                        setEditGuardrailName(guardrail.name);
                                        setEditGuardrailPrompt(guardrail.prompt);
                                    }}
                                    style={{ position: 'absolute', top: '1rem', right: '3rem', background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8' }}
                                    title="Edit Guardrail"
                                >
                                    <Pencil size={16} />
                                </button>
                                <h3 style={{ margin: '0 0 0.5rem 0' }}>{guardrail.name}</h3>
                                <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.5rem' }}>
                                    Created: {new Date(guardrail.created_at || Date.now()).toLocaleDateString()}
                                </div>
                                <div style={{ fontSize: '0.9rem', color: '#64748b', whiteSpace: 'pre-wrap', maxHeight: '150px', overflowY: 'auto' }}>
                                    {guardrail.prompt}
                                </div>
                            </div>
                        ))}
                        {guardrails.length === 0 && !isCreatingGuardrail && (
                            <div style={{ gridColumn: '1/-1', textAlign: 'center', color: '#94a3b8', padding: '2rem' }}>
                                No guardrails found. Create one to get started.
                            </div>
                        )}
                    </div>
                </div>
            )}
            
            {view !== 'dashboard' && view !== 'history' && view !== 'agents' && view !== 'guardrails' && view !== 'memories' && view !== 'voice' && (
                <div className="content-placeholder">
                    <h2>{view.charAt(0).toUpperCase() + view.slice(1)}</h2>
                    {view === 'settings' && (
                         <button onClick={handleDeleteAccount} className="danger-btn">Delete Account</button>
                    )}
                </div>
            )}
        </main>
      </div>
    );
  }

  return (
    <div className="App auth-container">
      <h1>Arthur Prime</h1>
      <div className="card auth-card">
        <h2>{view === 'login' ? 'Login' : 'Create Account'}</h2>
        {error && <p className="error">{error}</p>}
        <form onSubmit={view === 'login' ? handleLogin : handleRegister}>
            <div className="form-group">
            <label>Username</label>
            <input value={username} onChange={e => setUsername(e.target.value)} required />
            </div>
            <div className="form-group">
            <label>Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} required />
            </div>
            <button type="submit" className="primary-btn">
                {view === 'login' ? 'Sign In' : 'Sign Up'}
            </button>
        </form>
        <p className="toggle-auth">
            {view === 'login' ? "New user? " : "Existing user? "}
            <button className="link-btn" onClick={() => {
                setView(view === 'login' ? 'register' : 'login');
                setError('');
            }}>
            {view === 'login' ? 'Create an account' : 'Log in'}
            </button>
        </p>
      </div>
    </div>
  );
}

export default App;
