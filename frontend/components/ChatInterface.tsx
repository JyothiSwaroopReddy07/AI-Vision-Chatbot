'use client'

import { useState, useRef, useEffect } from 'react'
import { useAuthStore, useChatStore, useMSigDBStore } from '@/lib/store'
import { chatAPI } from '@/lib/api'
import ReactMarkdown from 'react-markdown'
import StarButton from './StarButton'
import EnhancedSidebar from './EnhancedSidebar'
import AddToFolderModal from './AddToFolderModal'
import SourcesModal from './SourcesModal'
import SearchTypeToggle from './SearchTypeToggle'
import MsigDBResultsPanel from './MsigDBResultsPanel'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  timestamp: Date
  msigdb_results?: any  // Store MSigDB results with each message
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
  const { searchType, setResults, setShowResultsPanel, setLoading, currentResults, showResultsPanel, numResults } = useMSigDBStore()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showSidebar, setShowSidebar] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('showSidebar') === 'true'
    }
    return false
  })
  const [sidebarRefreshKey, setSidebarRefreshKey] = useState(0)
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null)
  const [editedContent, setEditedContent] = useState('')
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null)
  const [showAddToFolderModal, setShowAddToFolderModal] = useState(false)
  const [currentSessionTitle, setCurrentSessionTitle] = useState('Untitled Conversation')
  const [showSourcesModal, setShowSourcesModal] = useState(false)
  const [selectedSourcesCitations, setSelectedSourcesCitations] = useState<Citation[]>([])
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

  // Load history when sessionId changes
  useEffect(() => {
    if (sessionId) {
      loadSessionHistory(sessionId)
    } else {
      setMessages([])
    }
  }, [sessionId])

  const loadSessionHistory = async (id: string) => {
    try {
      const response = await chatAPI.getHistory(id)
      const historyMessages: Message[] = response.data.map((msg: any) => ({
        id: msg.id,
        role: msg.role,
        content: msg.content,
        citations: msg.citations || [],
        timestamp: new Date(msg.created_at),
        msigdb_results: msg.msigdb_results || undefined  // Include MSigDB results from database
      }))
      setMessages(historyMessages)
      
      // Get session details to update title
      const sessionResponse = await chatAPI.getSession(id)
      if (sessionResponse.data) {
        setCurrentSessionTitle(sessionResponse.data.title || 'Untitled Conversation')
      }
    } catch (error) {
      console.error('Error loading history:', error)
    }
  }

  const handleSendMessage = async () => {
    if (!input.trim() || isLoading) return

    const tempUserId = 'temp-' + Date.now()
    const userMessage: Message = {
      id: tempUserId,
      role: 'user',
      content: input,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setIsLoading(true)
    
    // Set MSigDB loading state and open panel if MSigDB search
    if (searchType === 'msigdb') {
      setLoading(true)
      setShowResultsPanel(true)
    }

    try {
      const response = await chatAPI.sendMessage(input, sessionId ?? undefined, searchType)
      const data = response.data
      
      console.log('API Response:', data) // Debug log
      
      if (!sessionId && data.session_id) {
        setSessionId(data.session_id)
        // Trigger sidebar refresh to show the new session
        setSidebarRefreshKey(prev => prev + 1)
      }

      // Handle MSigDB results if present
      if (data.msigdb_results) {
        setResults(
          data.msigdb_results.results || [],
          data.msigdb_results.genes || [],
          data.msigdb_results.species || 'auto',
          data.msigdb_results.num_results || 0
        )
      }

      // Update user message with real ID from backend
      const updatedUserMessage: Message = {
        id: data.user_message_id || tempUserId,
        role: 'user',
        content: input,
        timestamp: new Date(),
      }

      const assistantMessage: Message = {
        id: data.assistant_message_id || data.message_id || Date.now().toString(),
        role: 'assistant',
        content: data.response || 'No response',
        citations: data.citations || [],
        timestamp: new Date(),
        msigdb_results: data.msigdb_results || undefined,
      }

      console.log('Assistant message:', assistantMessage) // Debug log
      
      // Replace the temp user message with the real one
      setMessages((prev) => {
        const filtered = prev.filter(m => m.id !== tempUserId)
        return [...filtered, updatedUserMessage, assistantMessage]
      })
      
      // Update session title if this is the first message
      if (messages.length === 0) {
        const title = input.length > 50 ? input.substring(0, 47) + '...' : input
        setCurrentSessionTitle(title)
      }
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
    
    // Set MSigDB loading state and open panel if MSigDB search
    if (searchType === 'msigdb') {
      setLoading(true)
      setShowResultsPanel(true)
    }

    // Create new user message with edited content (temp ID)
    const tempUserId = 'temp-' + Date.now()
    const userMessage: Message = {
      id: tempUserId,
      role: 'user',
      content: editedText,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])

    try {
      const response = await chatAPI.sendMessage(editedText, sessionId ?? undefined, searchType)
      const data = response.data
      
      if (!sessionId && data.session_id) {
        setSessionId(data.session_id)
        // Trigger sidebar refresh to show the new session
        setSidebarRefreshKey(prev => prev + 1)
      }

      // Handle MSigDB results if present
      if (data.msigdb_results) {
        setResults(
          data.msigdb_results.results || [],
          data.msigdb_results.genes || [],
          data.msigdb_results.species || 'auto',
          data.msigdb_results.num_results || 0
        )
      }

      // Update user message with real ID from backend
      const updatedUserMessage: Message = {
        id: data.user_message_id || tempUserId,
        role: 'user',
        content: editedText,
        timestamp: new Date(),
      }

      const assistantMessage: Message = {
        id: data.assistant_message_id || data.message_id || Date.now().toString(),
        role: 'assistant',
        content: data.response || 'No response',
        citations: data.citations || [],
        timestamp: new Date(),
        msigdb_results: data.msigdb_results || undefined,
      }

      // Replace the temp user message with the real one
      setMessages((prev) => {
        const filtered = prev.filter(m => m.id !== tempUserId)
        return [...filtered, updatedUserMessage, assistantMessage]
      })
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
            p: ({ children }) => <p className="mb-4 last:mb-0 leading-relaxed">{children}</p>,
            strong: ({ children }) => <strong className="font-semibold text-gray-900">{children}</strong>,
            em: ({ children }) => <em className="italic">{children}</em>,
            ol: ({ children }) => <ol className="list-decimal ml-6 mb-4 space-y-2 leading-relaxed">{children}</ol>,
            ul: ({ children }) => <ul className="list-disc ml-6 mb-4 space-y-2 leading-relaxed">{children}</ul>,
            li: ({ children }) => <li className="pl-2 leading-relaxed">{children}</li>,
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
      {/* Enhanced Sidebar */}
      {showSidebar && (
        <>
          {/* Mobile overlay */}
          <div 
            className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden"
            onClick={() => setShowSidebar(false)}
          />
          <div className="fixed md:relative inset-y-0 left-0 z-50 md:z-auto">
            <EnhancedSidebar
              key={sidebarRefreshKey}
              onClose={() => setShowSidebar(false)}
              onSelectSession={(id) => {
                setSessionId(id)
                setShowSidebar(false)
              }}
              onNewChat={() => {
                setMessages([])
                setSessionId(null)
                setShowSidebar(false)
              }}
              currentSessionId={sessionId}
            />
          </div>
        </>
      )}

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Clean Header */}
        <div className="header">
          <div className="flex items-center gap-2 md:gap-3 flex-1 min-w-0">
            <button
              onClick={() => setShowSidebar(!showSidebar)}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors flex-shrink-0"
              aria-label="Toggle sidebar"
            >
              <svg className="w-5 h-5 md:w-6 md:h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <div className="logo flex-shrink-0">
              <span className="text-sm md:text-base">Vision Research AI</span>
            </div>
            
            {/* Save Conversation Button */}
            {sessionId && messages.length > 0 && (
              <button
                onClick={() => setShowAddToFolderModal(true)}
                className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-700 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors border border-gray-300 hover:border-blue-300"
                title="Save conversation to folder"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                </svg>
                <span>Save</span>
              </button>
            )}
            
            {/* Mobile Save Button */}
            {sessionId && messages.length > 0 && (
              <button
                onClick={() => setShowAddToFolderModal(true)}
                className="sm:hidden p-2 text-gray-700 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                title="Save conversation"
                aria-label="Save conversation"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                </svg>
              </button>
            )}
          </div>
          
          <div className="flex items-center gap-3 flex-shrink-0">
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
                  <div className="flex items-center justify-end gap-1 mb-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    {message.role === 'user' && !message.id.startsWith('temp-') && (
                      <StarButton messageId={message.id} size="sm" />
                    )}
                    
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
                  
                  {/* Perplexity-style: Compact SQUARE sources at the TOP for assistant messages */}
                  {message.role === 'assistant' && message.citations && message.citations.length > 0 && (
                    <div className="flex items-center gap-2 mb-4 flex-wrap">
                      {message.citations.slice(0, 3).map((citation, idx) => (
                        <a
                          key={idx}
                          href={citation.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="perplexity-source-card"
                          title={citation.title}
                        >
                          <div className="perplexity-source-number">{idx + 1}</div>
                          <div className="perplexity-source-title">{citation.title}</div>
                          <div className="perplexity-source-journal">{citation.journal || 'Research Paper'}</div>
                        </a>
                      ))}
                      
                      {message.citations.length > 3 && (
                        <button
                          onClick={() => {
                            setSelectedSourcesCitations(message.citations || [])
                            setShowSourcesModal(true)
                          }}
                          className="perplexity-source-more"
                        >
                          <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                          </svg>
                          <span className="text-xs font-medium">
                            +{message.citations.length - 3} more
                          </span>
                        </button>
                      )}
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
                    renderMessageWithCitations(
                      message.content, 
                      message.citations, 
                      message.role === 'user'
                    )
                  )}
                  
                  {/* View MSigDB Results button for messages with results */}
                  {message.role === 'assistant' && message.msigdb_results && message.msigdb_results.results && message.msigdb_results.results.length > 0 && (
                    <div className="mt-3">
                      <button
                        onClick={() => {
                          setResults(
                            message.msigdb_results.results || [],
                            message.msigdb_results.genes || [],
                            message.msigdb_results.species || 'auto',
                            message.msigdb_results.num_results || 0
                          )
                          setShowResultsPanel(true)
                        }}
                        className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors border border-blue-200"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                        </svg>
                        View {message.msigdb_results.num_results || 0} Gene Sets
                      </button>
                    </div>
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
          {/* Search Type Toggle */}
          <div className="px-4 pb-3">
            <SearchTypeToggle />
          </div>
          
          <div className="input-wrapper">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={searchType === 'msigdb' ? 'Enter gene symbols (e.g., TP53, BRCA1, EGFR)...' : 'Ask anything...'}
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
      
      {/* MSigDB Results Panel */}
      <MsigDBResultsPanel />
      
      {/* Add to Folder Modal */}
      {showAddToFolderModal && sessionId && (
        <AddToFolderModal
          sessionId={sessionId}
          sessionTitle={currentSessionTitle}
          onClose={() => setShowAddToFolderModal(false)}
        />
      )}
      
      {/* Sources Modal */}
      <SourcesModal
        isOpen={showSourcesModal}
        onClose={() => setShowSourcesModal(false)}
        citations={selectedSourcesCitations}
      />
    </div>
  )
}
