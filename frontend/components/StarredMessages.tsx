'use client'

import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { useStarredStore } from '@/lib/store'

interface StarredMessagesProps {
  onSelectSession?: (sessionId: string) => void
}

export default function StarredMessages({ onSelectSession }: StarredMessagesProps) {
  const { starredMessages, setStarredMessages, searchQuery, setSearchQuery } = useStarredStore()
  const [isLoading, setIsLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  useEffect(() => {
    fetchStarredMessages()
  }, [])

  const fetchStarredMessages = async () => {
    try {
      setIsLoading(true)
      const response = await api.get('/starred/starred')
      setStarredMessages(response.data)
    } catch (error) {
      console.error('Failed to fetch starred messages:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSearch = async (query: string) => {
    setSearchQuery(query)
    
    if (query.trim().length < 2) {
      fetchStarredMessages()
      return
    }

    try {
      const response = await api.get('/starred/starred/search', {
        params: { query }
      })
      setStarredMessages(response.data)
    } catch (error) {
      console.error('Failed to search starred messages:', error)
    }
  }

  const handleUnstar = async (messageId: string) => {
    try {
      await api.delete(`/starred/star/${messageId}`)
      setStarredMessages(starredMessages.filter(m => m.message_id !== messageId))
    } catch (error) {
      console.error('Failed to unstar message:', error)
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))

    if (days === 0) return 'Today'
    if (days === 1) return 'Yesterday'
    if (days < 7) return `${days} days ago`
    if (days < 30) return `${Math.floor(days / 7)} weeks ago`
    if (days < 365) return `${Math.floor(days / 30)} months ago`
    return `${Math.floor(days / 365)} years ago`
  }

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        {[1, 2, 3].map(i => (
          <div key={i} className="h-32 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse" />
        ))}
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-900">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-800 flex-shrink-0 bg-white dark:bg-gray-900">
        <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
          Starred Messages
        </h2>
        
        {/* Search */}
        <div className="relative">
          <svg
            className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400"
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
            onChange={(e) => handleSearch(e.target.value)}
            placeholder="Search starred messages..."
            className="w-full pl-10 pr-4 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-[#1a1a1a] text-gray-900 dark:text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
          />
        </div>
      </div>

      {/* Messages List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-1.5 bg-[#f8f9fa] dark:bg-[#1a1a1a]">
        {starredMessages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center text-[#5f6368] dark:text-gray-400 py-12">
            <svg className="w-16 h-16 mb-4 text-gray-300 dark:text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"
              />
            </svg>
            <p className="text-lg font-medium mb-1">No starred messages yet</p>
            <p className="text-sm">
              Star important Q&A pairs to find them easily later
            </p>
          </div>
        ) : (
          starredMessages.map(msg => (
            <div
              key={msg.id}
              className="border border-transparent hover:border-[#e8eaed] dark:hover:border-gray-700 rounded-lg p-3 sm:p-4 hover:shadow-sm transition-all bg-white dark:bg-gray-800 cursor-pointer"
              onClick={() => onSelectSession?.(msg.session_id)}
            >
              <div className="flex items-start justify-between gap-2 sm:gap-3 mb-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 sm:gap-2 text-xs text-gray-500 dark:text-gray-400 mb-1">
                    <span className="truncate hover:text-blue-600 dark:hover:text-blue-400">{msg.session_title}</span>
                    <span className="hidden xs:inline">•</span>
                    <span className="hidden xs:inline">{formatDate(msg.starred_at)}</span>
                  </div>
                  {msg.tags && msg.tags.length > 0 && (
                    <div className="flex gap-1 flex-wrap mb-2">
                      {msg.tags.map((tag, idx) => (
                        <span
                          key={idx}
                          className="px-1.5 sm:px-2 py-0.5 text-xs bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    handleUnstar(msg.message_id)
                  }}
                  className="flex-shrink-0 p-1 text-yellow-500 hover:text-gray-400 transition-colors"
                  title="Unstar"
                  aria-label="Unstar message"
                >
                  <svg className="w-4 h-4 sm:w-5 sm:h-5 fill-current" viewBox="0 0 24 24">
                    <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
                  </svg>
                </button>
              </div>

              {/* Question */}
              {msg.question && (
                <div className="mb-2 sm:mb-3">
                  <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                    Question
                  </div>
                  <div className="text-xs sm:text-sm text-gray-900 dark:text-white leading-relaxed">
                    {msg.question}
                  </div>
                </div>
              )}

              {/* Answer */}
              <div>
                <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                  Answer
                </div>
                <div
                  className={`text-xs sm:text-sm text-gray-700 dark:text-gray-300 leading-relaxed ${
                    expandedId === msg.id ? '' : 'line-clamp-3'
                  }`}
                >
                  {msg.answer}
                </div>
                {msg.answer.length > 200 && (
                  <button
                    onClick={() => setExpandedId(expandedId === msg.id ? null : msg.id)}
                    className="text-xs text-blue-600 dark:text-blue-400 hover:underline mt-1"
                  >
                    {expandedId === msg.id ? 'Show less' : 'Show more'}
                  </button>
                )}
              </div>

              {/* Notes */}
              {msg.notes && (
                <div className="mt-2 sm:mt-3 pt-2 sm:pt-3 border-t border-gray-200 dark:border-gray-700">
                  <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                    Notes
                  </div>
                  <div className="text-xs sm:text-sm text-gray-600 dark:text-gray-400 italic leading-relaxed">
                    {msg.notes}
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  )
}

