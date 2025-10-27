'use client'

import { useState, useRef, useEffect } from 'react'
import { useAuthStore, useChatStore } from '@/lib/store'
import { chatAPI } from '@/lib/api'
import ReactMarkdown from 'react-markdown'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  timestamp: Date
}

interface Citation {
  source_type: string
  source_id: string
  title: string
  authors: string
  journal: string
  url: string
  excerpt: string
  relevance_score: number
}

interface Session {
  id: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
}

export default function ChatInterface() {
  const { user, logout } = useAuthStore()
  const { sessionId, setSessionId } = useChatStore()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showSidebar, setShowSidebar] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('showSidebar') === 'true'
    }
    return false
  })
  const [sessions, setSessions] = useState<Session[]>([])
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null)
  const [editedContent, setEditedContent] = useState('')
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Persist sidebar state
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('showSidebar', showSidebar.toString())
    }
  }, [showSidebar])

  // Load sessions on mount
  useEffect(() => {
    loadSessions()
  }, [])

  // Load history when sessionId changes
  useEffect(() => {
    if (sessionId) {
      loadSessionHistory(sessionId)
    } else {
      setMessages([])
    }
  }, [sessionId])

  const loadSessions = async () => {
    try {
      const response = await chatAPI.getSessions()
      setSessions(response.data)
    } catch (error) {
      console.error('Error loading sessions:', error)
    }
  }

  const loadSessionHistory = async (id: string) => {
    try {
      const response = await chatAPI.getHistory(id)
      const historyMessages: Message[] = response.data.map((msg: any) => ({
        id: msg.id,
        role: msg.role,
        content: msg.content,
        citations: msg.citations || [],
        timestamp: new Date(msg.created_at)
      }))
      setMessages(historyMessages)
    } catch (error) {
      console.error('Error loading history:', error)
    }
  }

  const handleSendMessage = async () => {
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const response = await chatAPI.sendMessage(input, sessionId ?? undefined)
      const data = response.data
      
      console.log('API Response:', data) // Debug log
      
      if (!sessionId && data.session_id) {
        setSessionId(data.session_id)
        // Reload sessions to show the new one
        loadSessions()
      }

      const assistantMessage: Message = {
        id: data.message_id || Date.now().toString(),
        role: 'assistant',
        content: data.response || 'No response',
        citations: data.citations || [],
        timestamp: new Date(),
      }

      console.log('Assistant message:', assistantMessage) // Debug log
      setMessages((prev) => [...prev, assistantMessage])
    } catch (error) {
      console.error('Error sending message:', error)
      const errorMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleCopyMessage = async (messageId: string, content: string) => {
    try {
      await navigator.clipboard.writeText(content)
      setCopiedMessageId(messageId)
      setTimeout(() => setCopiedMessageId(null), 2000)
    } catch (error) {
      console.error('Failed to copy:', error)
    }
  }

  const handleEditMessage = (messageId: string, content: string) => {
    setEditingMessageId(messageId)
    setEditedContent(content)
  }

  const handleSaveEdit = async (messageId: string) => {
    if (!editedContent.trim() || isLoading) return

    // Find the message index
    const messageIndex = messages.findIndex(m => m.id === messageId)
    if (messageIndex === -1) return

    // Remove all messages after this one (including assistant responses)
    const newMessages = messages.slice(0, messageIndex)
    setMessages(newMessages)
    
    const editedText = editedContent
    setEditingMessageId(null)
    setEditedContent('')
    setIsLoading(true)

    // Create new user message with edited content
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: editedText,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])

    try {
      const response = await chatAPI.sendMessage(editedText, sessionId ?? undefined)
      const data = response.data
      
      if (!sessionId && data.session_id) {
        setSessionId(data.session_id)
        loadSessions()
      }

      const assistantMessage: Message = {
        id: data.message_id || Date.now().toString(),
        role: 'assistant',
        content: data.response || 'No response',
        citations: data.citations || [],
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch (error) {
      console.error('Error sending message:', error)
      const errorMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleCancelEdit = () => {
    setEditingMessageId(null)
    setEditedContent('')
  }

  const renderMessageWithCitations = (content: string, citations?: Citation[], isUser: boolean = false) => {
    // For user messages, render larger text without markdown
    if (isUser) {
      return <div className="user-query-text">{content}</div>
    }
    
    // For assistant messages, render markdown
    return (
      <div className="assistant-response-text">
        <ReactMarkdown
          components={{
            p: ({ children }) => <p className="mb-4 last:mb-0">{children}</p>,
            strong: ({ children }) => <strong className="font-semibold text-gray-900">{children}</strong>,
            em: ({ children }) => <em className="italic">{children}</em>,
            ol: ({ children }) => <ol className="list-decimal list-inside mb-4 space-y-2">{children}</ol>,
            ul: ({ children }) => <ul className="list-disc list-inside mb-4 space-y-2">{children}</ul>,
            li: ({ children }) => <li className="ml-4">{children}</li>,
            h1: ({ children }) => <h1 className="text-2xl font-bold mb-4 mt-6">{children}</h1>,
            h2: ({ children }) => <h2 className="text-xl font-bold mb-3 mt-5">{children}</h2>,
            h3: ({ children }) => <h3 className="text-lg font-semibold mb-2 mt-4">{children}</h3>,
            code: ({ children }) => <code className="bg-gray-100 px-1.5 py-0.5 rounded text-sm font-mono">{children}</code>,
            pre: ({ children }) => <pre className="bg-gray-100 p-3 rounded-lg overflow-x-auto mb-4">{children}</pre>,
            blockquote: ({ children }) => <blockquote className="border-l-4 border-gray-300 pl-4 italic my-4">{children}</blockquote>,
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-white overflow-hidden">
      {/* Minimal Sidebar */}
      {showSidebar && (
        <>
          {/* Mobile overlay */}
          <div 
            className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden"
            onClick={() => setShowSidebar(false)}
          />
          <div className="sidebar z-50">
          <div className="p-4 border-b border-gray-200">
            <button
              onClick={() => {
                setMessages([])
                setSessionId(null)
                setShowSidebar(false)
              }}
              className="w-full py-2 px-4 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              + New Chat
            </button>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4">
            <div className="text-xs font-semibold text-gray-500 uppercase mb-2">Chat History</div>
            {sessions.length === 0 ? (
              <div className="text-sm text-gray-500 text-center py-4">No previous chats</div>
            ) : (
              sessions.map((session) => (
                <div
                  key={session.id}
                  onClick={() => {
                    setSessionId(session.id)
                    setShowSidebar(false)
                  }}
                  className={`sidebar-item ${sessionId === session.id ? 'active' : ''}`}
                >
                  <div className="truncate font-medium">{session.title}</div>
                  <div className="text-xs text-gray-500 mt-1">
                    {new Date(session.updated_at).toLocaleDateString()}
                  </div>
                </div>
              ))
            )}
          </div>
          </div>
        </>
      )}

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Clean Header */}
        <div className="header">
          <div className="flex items-center">
            <button
              onClick={() => setShowSidebar(!showSidebar)}
              className="p-2 hover:bg-gray-100 rounded-lg mr-2 md:mr-3 transition-colors"
              aria-label="Toggle sidebar"
            >
              <svg className="w-5 h-5 md:w-6 md:h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <div className="logo">
              <span className="text-sm md:text-base">Vision Research AI</span>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="hidden md:flex items-center gap-2 text-sm text-gray-600">
              <div className="w-7 h-7 rounded-full bg-blue-100 flex items-center justify-center text-xs font-semibold text-blue-700">
                {user?.email?.[0].toUpperCase()}
              </div>
              <span className="hidden lg:inline">{user?.email}</span>
            </div>
            <button
              onClick={logout}
              className="py-1.5 px-3 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            >
              Logout
            </button>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            <div className="welcome-container">
              <div className="welcome-title">What can I help you with?</div>
              <div className="welcome-subtitle">Ask anything about vision research, eye biology, or ophthalmology</div>
              
              <div className="mt-8">
                <div
                  className="suggestion-pill"
                  onClick={() => setInput('Tell me about single-cell RNA sequencing in retina research')}
                >
                  Single-cell transcriptomics in retina
                </div>
                <div
                  className="suggestion-pill"
                  onClick={() => setInput('What are the latest advances in glaucoma treatment?')}
                >
                  Latest glaucoma treatments
                </div>
                <div
                  className="suggestion-pill"
                  onClick={() => setInput('Explain AMD genetics and risk factors')}
                >
                  AMD genetics and risk factors
                </div>
                <div
                  className="suggestion-pill"
                  onClick={() => setInput('How does CRISPR gene editing work for retinal diseases?')}
                >
                  CRISPR for retinal diseases
                </div>
              </div>
            </div>
          ) : (
            <div>
              {messages.map((message) => (
                <div key={message.id} className="message-container group">
                  {/* Action buttons - floating on hover */}
                  <div className="flex items-center justify-end mb-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    {message.role === 'user' && !editingMessageId && (
                      <button
                        onClick={() => handleEditMessage(message.id, message.content)}
                        className="p-1.5 hover:bg-gray-100 rounded-md transition-colors"
                        title="Edit message"
                      >
                        <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                    )}
                    
                    <button
                      onClick={() => handleCopyMessage(message.id, message.content)}
                      className="p-1.5 hover:bg-gray-100 rounded-md transition-colors"
                      title="Copy message"
                    >
                      {copiedMessageId === message.id ? (
                        <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      ) : (
                        <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                      )}
                    </button>
                  </div>
                  
                  {/* Perplexity-style: Compact sources at the TOP for assistant messages */}
                  {message.role === 'assistant' && message.citations && message.citations.length > 0 && (
                    <div className="sources-top">
                      {message.citations.map((citation, idx) => (
                        <a
                          key={idx}
                          href={citation.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="source-pill"
                          title={citation.title}
                        >
                          <span className="source-pill-number">{idx + 1}</span>
                          <div className="source-pill-content">
                            <div className="source-pill-title">{citation.title}</div>
                            <div className="source-pill-meta">{citation.journal}</div>
                          </div>
                          <svg className="source-pill-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                          </svg>
                        </a>
                      ))}
                    </div>
                  )}
                  
                  {/* Editable message for user messages */}
                  {editingMessageId === message.id ? (
                    <div className="space-y-2">
                      <textarea
                        value={editedContent}
                        onChange={(e) => setEditedContent(e.target.value)}
                        className="w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none text-lg"
                        rows={3}
                        autoFocus
                      />
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleSaveEdit(message.id)}
                          className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
                        >
                          Save & Resubmit
                        </button>
                        <button
                          onClick={handleCancelEdit}
                          className="px-3 py-1.5 bg-gray-200 text-gray-700 text-sm rounded-lg hover:bg-gray-300 transition-colors"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    renderMessageWithCitations(message.content, message.citations, message.role === 'user')
                  )}
                </div>
              ))}

              {isLoading && (
                <div className="message-container">
                  <div className="loading-dots">
                    <div className="loading-dot"></div>
                    <div className="loading-dot"></div>
                    <div className="loading-dot"></div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Clean Input Area */}
        <div className="input-container">
          <div className="input-wrapper">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything..."
              className="input-field"
              rows={1}
              disabled={isLoading}
            />
            <button
              onClick={handleSendMessage}
              disabled={!input.trim() || isLoading}
              className="send-button"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
