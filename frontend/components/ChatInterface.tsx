'use client'

import { useState, useRef, useEffect } from 'react'
import { useAuthStore, useChatStore } from '@/lib/store'
import { chatAPI } from '@/lib/api'

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

export default function ChatInterface() {
  const { user, logout } = useAuthStore()
  const { sessionId, setSessionId } = useChatStore()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showSidebar, setShowSidebar] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

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
      const response = await chatAPI.sendMessage(input, sessionId)
      const data = response.data
      
      console.log('API Response:', data) // Debug log
      
      if (!sessionId && data.session_id) {
        setSessionId(data.session_id)
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

  const renderMessageWithCitations = (content: string, citations?: Citation[]) => {
    if (!citations || citations.length === 0) {
      return <div className="message-text">{content}</div>
    }

    // Add inline citation numbers after relevant sentences
    let textWithCitations = content
    const citationPositions: number[] = []
    
    // Simple heuristic: add citations at the end of sentences
    const sentences = content.split('. ')
    if (sentences.length > 1 && citations.length > 0) {
      const citationsPerSentence = Math.ceil(citations.length / Math.min(sentences.length - 1, citations.length))
      let citationIndex = 0
      
      textWithCitations = sentences.map((sentence, idx) => {
        if (idx < sentences.length - 1 && citationIndex < citations.length) {
          const citeNumbers = []
          for (let i = 0; i < citationsPerSentence && citationIndex < citations.length; i++) {
            citeNumbers.push(citationIndex + 1)
            citationIndex++
          }
          const citeStr = citeNumbers.map(n => `[${n}]`).join('')
          return sentence + '. ' + citeStr
        }
        return sentence
      }).join(' ')
    }

    return (
      <div className="message-text">
        {textWithCitations.split(/(\[\d+\])/).map((part, idx) => {
          const match = part.match(/\[(\d+)\]/)
          if (match) {
            const num = parseInt(match[1])
            return (
              <a
                key={idx}
                href={`#source-${num}`}
                className="citation-number"
                title={`Source ${num}`}
              >
                {num}
              </a>
            )
          }
          return <span key={idx}>{part}</span>
        })}
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
              }}
              className="w-full py-2 px-4 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              + New Chat
            </button>
          </div>
          
          <div className="p-4">
            <div className="text-xs font-semibold text-gray-500 uppercase mb-2">Recent</div>
            <div className="sidebar-item active">Current Chat</div>
          </div>

          <div className="absolute bottom-0 w-full p-4 border-t border-gray-200">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-sm font-semibold text-blue-700">
                {user?.email?.[0].toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-gray-900 truncate">{user?.email}</div>
              </div>
            </div>
            <button
              onClick={logout}
              className="w-full py-2 px-3 text-sm text-gray-700 hover:bg-gray-100 rounded-lg"
            >
              Log out
            </button>
          </div>
          </div>
        </>
      )}

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Clean Header */}
        <div className="header">
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
                <div key={message.id} className="message-container">
                  <div className="message-role">
                    {message.role === 'user' ? 'You' : 'Vision AI'}
                  </div>
                  
                  {renderMessageWithCitations(message.content, message.citations)}

                  {message.citations && message.citations.length > 0 && (
                    <div className="sources-container">
                      <div className="sources-header">Sources</div>
                      <div>
                        {message.citations.map((citation, idx) => (
                          <div key={idx} id={`source-${idx + 1}`} className="source-card">
                            <div className="flex items-start">
                              <span className="source-number">{idx + 1}</span>
                              <div className="flex-1">
                                <div className="source-title">{citation.title}</div>
                                <div className="source-meta">
                                  {citation.authors} · {citation.journal} · {citation.source_id}
                                </div>
                                <div className="source-excerpt">{citation.excerpt}</div>
                                {citation.url && (
                                  <a
                                    href={citation.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="source-link"
                                  >
                                    View source →
                                  </a>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}

              {isLoading && (
                <div className="message-container">
                  <div className="message-role">Vision AI</div>
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
