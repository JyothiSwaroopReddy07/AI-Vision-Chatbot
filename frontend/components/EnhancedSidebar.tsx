'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { api, chatAPI } from '@/lib/api'
import { useChatStore } from '@/lib/store'
import BookmarkFolders from './BookmarkFolders'
import StarredMessages from './StarredMessages'

interface Session {
  id: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
}

interface EnhancedSidebarProps {
  onClose?: () => void
  onSelectSession: (sessionId: string) => void
  onNewChat: () => void
  currentSessionId?: string | null
}

export default function EnhancedSidebar({ onClose, onSelectSession, onNewChat, currentSessionId }: EnhancedSidebarProps) {
  const [activeTab, setActiveTab] = useState<'chats' | 'bookmarks' | 'starred'>('chats')
  const [searchQuery, setSearchQuery] = useState('')
  const [dateFilter, setDateFilter] = useState<'all' | 'today' | 'week' | 'month' | 'custom'>('all')
  const [customStartDate, setCustomStartDate] = useState('')
  const [customEndDate, setCustomEndDate] = useState('')
  const [sessions, setSessions] = useState<Session[]>([])
  const [filteredSessions, setFilteredSessions] = useState<Session[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [hasMore, setHasMore] = useState(true)
  const [page, setPage] = useState(0)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const searchTimeoutRef = useRef<NodeJS.Timeout>()
  
  const ITEMS_PER_PAGE = 20

  // Load sessions when component mounts or when filters/tab changes
  useEffect(() => {
    if (activeTab === 'chats') {
      resetAndLoadSessions()
    }
  }, [activeTab, dateFilter, customStartDate, customEndDate])

  const resetAndLoadSessions = () => {
    setSessions([])
    setPage(0)
    setHasMore(true)
    loadSessions(0, true)
  }

  const loadSessions = async (pageNum: number = page, reset: boolean = false) => {
    if ((!hasMore && !reset) || (isLoadingMore && !reset)) return
    
    try {
      if (reset) {
        setIsLoading(true)
      } else {
        setIsLoadingMore(true)
      }
      
      let params: any = {
        limit: ITEMS_PER_PAGE,
        offset: pageNum * ITEMS_PER_PAGE
      }
      
      // Add search query - ALWAYS search on backend for global search
      if (searchQuery.trim()) {
        params.search = searchQuery.trim()
      }
      
      // Add date filters
      if (dateFilter !== 'all') {
        const now = new Date()
        let startDate: Date | null = null
        
        switch (dateFilter) {
          case 'today':
            startDate = new Date(now.setHours(0, 0, 0, 0))
            break
          case 'week':
            startDate = new Date(now.setDate(now.getDate() - 7))
            break
          case 'month':
            startDate = new Date(now.setMonth(now.getMonth() - 1))
            break
          case 'custom':
            if (customStartDate) params.start_date = customStartDate
            if (customEndDate) params.end_date = customEndDate
            break
        }
        
        if (startDate && dateFilter !== 'custom') {
          params.start_date = startDate.toISOString()
        }
      }
      
      const response = await chatAPI.getSessions(params)
      const newSessions = response.data
      
      if (reset) {
        setSessions(newSessions)
        setFilteredSessions(newSessions)
      } else {
        setSessions(prev => [...prev, ...newSessions])
        setFilteredSessions(prev => [...prev, ...newSessions])
      }
      
      setHasMore(newSessions.length === ITEMS_PER_PAGE)
      setPage(pageNum + 1)
    } catch (error) {
      console.error('Failed to load sessions:', error)
    } finally {
      setIsLoading(false)
      setIsLoadingMore(false)
    }
  }

  // Infinite scroll handler
  const handleScroll = useCallback(() => {
    const container = scrollContainerRef.current
    if (!container) return

    const { scrollTop, scrollHeight, clientHeight } = container
    const threshold = 100 // Load more when 100px from bottom

    if (scrollHeight - scrollTop - clientHeight < threshold && !isLoadingMore && hasMore) {
      loadSessions(page, false)
    }
  }, [page, isLoadingMore, hasMore])

  useEffect(() => {
    const container = scrollContainerRef.current
    if (!container) return

    container.addEventListener('scroll', handleScroll)
    return () => container.removeEventListener('scroll', handleScroll)
  }, [handleScroll])

  // Debounced search
  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setSearchQuery(value)
    
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current)
    }
    
    searchTimeoutRef.current = setTimeout(() => {
      resetAndLoadSessions()
    }, 500)
  }

  const handleDateFilterChange = (filter: 'all' | 'today' | 'week' | 'month' | 'custom') => {
    setDateFilter(filter)
  }

  const deleteSession = async (sessionId: string) => {
    if (!confirm('Delete this conversation?')) return
    
    try {
      await chatAPI.deleteSession(sessionId)
      setSessions(prev => prev.filter(s => s.id !== sessionId))
      setFilteredSessions(prev => prev.filter(s => s.id !== sessionId))
    } catch (error) {
      console.error('Failed to delete session:', error)
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffInMs = now.getTime() - date.getTime()
    const diffInDays = Math.floor(diffInMs / (1000 * 60 * 60 * 24))

    if (diffInDays === 0) return 'Today'
    if (diffInDays === 1) return 'Yesterday'
    if (diffInDays < 7) return `${diffInDays}d ago`
    if (diffInDays < 30) return `${Math.floor(diffInDays / 7)}w ago`
    if (diffInDays < 365) return `${Math.floor(diffInDays / 30)}mo ago`
    return date.toLocaleDateString()
  }

  return (
    <div className="flex flex-col h-full bg-[#f8f9fa] dark:bg-[#1a1a1a] w-full sm:w-80 md:w-96 border-r border-[#e8eaed] dark:border-gray-800">
      {/* Header with tabs */}
      <div className="p-4 border-b border-[#e8eaed] dark:border-gray-800 flex-shrink-0 bg-white dark:bg-gray-900">
        <button
          onClick={onNewChat}
          className="w-full py-2.5 px-4 text-sm font-medium text-white bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-700 hover:to-blue-600 rounded-lg transition-all shadow-sm hover:shadow mb-4"
        >
          + New Chat
        </button>

        {/* Tabs */}
        <div className="flex gap-1 bg-gray-100 dark:bg-[#1a1a1a] p-1 rounded-lg">
          {[
            { id: 'chats', label: 'Chats', icon: 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z' },
            { id: 'bookmarks', label: 'Saved', icon: 'M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z' },
            { id: 'starred', label: 'Starred', icon: 'M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z' },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex-1 py-2 px-3 text-xs font-medium rounded-md transition-all flex items-center justify-center gap-1.5 ${
                activeTab === tab.id
                  ? 'bg-white dark:bg-[#2a2a2a] text-gray-900 dark:text-white shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
              }`}
              title={tab.label}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={tab.icon} />
              </svg>
              <span className="hidden md:inline">{tab.label}</span>
            </button>
          ))}
        </div>
      </div>

      {activeTab === 'chats' && (
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Search and Filters */}
          <div className="p-3 space-y-2 border-b border-[#e8eaed] dark:border-gray-800 flex-shrink-0 bg-white dark:bg-gray-900">
            {/* Search */}
            <div className="relative">
              <svg
                className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-[#9aa0a6]"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
              <input
                type="text"
                value={searchQuery}
                onChange={handleSearch}
                placeholder="Search conversations..."
                className="w-full pl-10 pr-4 py-2 text-sm border border-[#e8eaed] dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-[#202124] dark:text-white placeholder-[#9aa0a6] focus:ring-2 focus:ring-[#1a73e8] focus:border-transparent outline-none transition-all"
              />
            </div>

            {/* Date Filter */}
            <div className="space-y-2">
              <div className="flex gap-1 flex-wrap">
                {['all', 'today', 'week', 'month', 'custom'].map(filter => (
                  <button
                    key={filter}
                    onClick={() => handleDateFilterChange(filter as any)}
                    className={`px-2.5 py-1 text-xs rounded-md transition-all font-medium ${
                      dateFilter === filter
                        ? 'bg-[#e8f0fe] dark:bg-blue-900/30 text-[#1a73e8] dark:text-blue-300'
                        : 'bg-[#f0f2f5] dark:bg-gray-800 text-[#5f6368] dark:text-gray-400 hover:bg-[#e8eaed] dark:hover:bg-gray-700'
                    }`}
                  >
                    {filter.charAt(0).toUpperCase() + filter.slice(1)}
                  </button>
                ))}
              </div>

              {/* Custom Date Range Pickers */}
              {dateFilter === 'custom' && (
                <div className="space-y-2 pt-1">
                  <div>
                    <label className="block text-xs text-[#5f6368] dark:text-gray-400 mb-1">From</label>
                    <input
                      type="date"
                      value={customStartDate}
                      onChange={(e) => {
                        setCustomStartDate(e.target.value)
                        if (e.target.value) {
                          resetAndLoadSessions()
                        }
                      }}
                      className="w-full px-2 py-1.5 text-xs border border-[#e8eaed] dark:border-gray-700 rounded-md bg-white dark:bg-gray-800 text-[#202124] dark:text-white focus:ring-2 focus:ring-[#1a73e8] outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-[#5f6368] dark:text-gray-400 mb-1">To</label>
                    <input
                      type="date"
                      value={customEndDate}
                      onChange={(e) => {
                        setCustomEndDate(e.target.value)
                        if (e.target.value) {
                          resetAndLoadSessions()
                        }
                      }}
                      className="w-full px-2 py-1.5 text-xs border border-[#e8eaed] dark:border-gray-700 rounded-md bg-white dark:bg-gray-800 text-[#202124] dark:text-white focus:ring-2 focus:ring-[#1a73e8] outline-none"
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Sessions List with Infinite Scroll */}
          <div 
            ref={scrollContainerRef}
            className="flex-1 overflow-y-auto scroll-smooth bg-[#f8f9fa] dark:bg-[#1a1a1a]"
            style={{ scrollBehavior: 'smooth' }}
          >
            {isLoading && sessions.length === 0 ? (
              <div className="space-y-2 p-3">
                {[1, 2, 3, 4, 5].map(i => (
                  <div key={i} className="h-16 bg-white dark:bg-gray-800 rounded-lg animate-pulse" />
                ))}
              </div>
            ) : filteredSessions.length === 0 ? (
              <div className="text-center text-sm text-[#5f6368] dark:text-gray-400 py-12 px-4">
                {searchQuery ? 'No conversations found' : 'No conversations yet'}
              </div>
            ) : (
              <div className="p-3 space-y-1.5">
                {filteredSessions.map(session => (
                  <div
                    key={session.id}
                    className={`group relative p-3 rounded-lg cursor-pointer transition-all ${
                      currentSessionId === session.id
                        ? 'bg-[#e8f0fe] dark:bg-blue-900/20 shadow-sm border border-[#1a73e8] dark:border-blue-700'
                        : 'bg-white dark:bg-gray-800 hover:shadow-sm border border-transparent hover:border-[#e8eaed] dark:hover:border-gray-700'
                    }`}
                    onClick={() => {
                      onSelectSession(session.id)
                      onClose?.()
                    }}
                  >
                    <div className="flex items-start gap-2 min-w-0">
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-[#202124] dark:text-white truncate leading-tight mb-1">
                          {session.title}
                        </div>
                        <div className="text-xs text-[#5f6368] dark:text-gray-400 flex items-center gap-1.5">
                          <span>{formatDate(session.updated_at)}</span>
                          {session.message_count > 0 && (
                            <>
                              <span>•</span>
                              <span>{session.message_count} msgs</span>
                            </>
                          )}
                        </div>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          deleteSession(session.id)
                        }}
                        className="opacity-0 group-hover:opacity-100 p-1.5 text-[#5f6368] hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-all"
                        title="Delete conversation"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </div>
                ))}
                
                {/* Loading More Indicator */}
                {isLoadingMore && (
                  <div className="py-4 space-y-2">
                    {[1, 2].map(i => (
                      <div key={i} className="h-16 bg-white dark:bg-gray-800 rounded-lg animate-pulse" />
                    ))}
                  </div>
                )}
                
                {/* End of List Indicator */}
                {!hasMore && sessions.length > 0 && (
                  <div className="text-center text-xs text-[#9aa0a6] dark:text-gray-500 py-6">
                    All conversations loaded
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'bookmarks' && (
        <div className="flex-1 overflow-hidden bg-[#f8f9fa] dark:bg-[#1a1a1a]">
          <BookmarkFolders 
            onSelectChat={(sessionId) => {
              onSelectSession(sessionId)
              onClose?.()
            }}
          />
        </div>
      )}

      {activeTab === 'starred' && (
        <div className="flex-1 overflow-hidden bg-[#f8f9fa] dark:bg-[#1a1a1a]">
          <StarredMessages 
            onSelectSession={(sessionId) => {
              onSelectSession(sessionId)
              onClose?.()
            }}
          />
        </div>
      )}
    </div>
  )
}
