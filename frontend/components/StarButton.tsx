'use client'

import { useState } from 'react'
import { api } from '@/lib/api'
import { useChatStore, useStarredStore } from '@/lib/store'

interface StarButtonProps {
  messageId: string
  isStarred?: boolean
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export default function StarButton({ messageId, isStarred: initialStarred = false, size = 'md', className = '' }: StarButtonProps) {
  const [isStarred, setIsStarred] = useState(initialStarred)
  const [isLoading, setIsLoading] = useState(false)
  const updateMessageStarStatus = useChatStore(state => state.updateMessageStarStatus)
  const { addStarredMessage, removeStarredMessage } = useStarredStore()

  const sizeClasses = {
    sm: 'w-3.5 h-3.5 sm:w-4 sm:h-4',
    md: 'w-4 h-4 sm:w-5 sm:h-5',
    lg: 'w-5 h-5 sm:w-6 sm:h-6'
  }

  const buttonSizeClasses = {
    sm: 'p-1 sm:p-1.5 min-w-[32px] min-h-[32px]', // Ensure minimum touch target
    md: 'p-1.5 sm:p-2 min-w-[36px] min-h-[36px]',
    lg: 'p-2 sm:p-2.5 min-w-[40px] min-h-[40px]'
  }

  const handleToggleStar = async (e: React.MouseEvent) => {
    e.stopPropagation()
    
    if (isLoading) return

    setIsLoading(true)
    
    try {
      if (isStarred) {
        // Unstar
        await api.delete(`/starred/star/${messageId}`)
        setIsStarred(false)
        updateMessageStarStatus(messageId, false)
        removeStarredMessage(messageId)
      } else {
        // Star
        await api.post('/starred/star', {
          message_id: messageId
        })
        setIsStarred(true)
        updateMessageStarStatus(messageId, true)
        // Note: Full starred message data would need to be fetched/provided for addStarredMessage
      }
    } catch (error) {
      console.error('Failed to toggle star:', error)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <button
      onClick={handleToggleStar}
      disabled={isLoading}
      className={`
        group relative inline-flex items-center justify-center
        ${buttonSizeClasses[size]}
        transition-all duration-200 ease-in-out
        hover:scale-110 active:scale-95
        disabled:opacity-50 disabled:cursor-not-allowed
        rounded-md hover:bg-gray-100 dark:hover:bg-gray-800
        ${className}
      `}
      aria-label={isStarred ? 'Unstar message' : 'Star message'}
      title={isStarred ? 'Unstar message' : 'Star message'}
    >
      {isStarred ? (
        <svg
          className={`${sizeClasses[size]} text-yellow-500 fill-current`}
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
        >
          <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
        </svg>
      ) : (
        <svg
          className={`${sizeClasses[size]} text-gray-400 group-hover:text-gray-600 dark:text-gray-500 dark:group-hover:text-gray-300 transition-colors`}
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"
          />
        </svg>
      )}
      
      {/* Tooltip - Hidden on mobile, shown on larger screens */}
      <span className="hidden sm:block absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 text-xs text-white bg-gray-900 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
        {isStarred ? 'Unstar' : 'Star this'}
      </span>
    </button>
  )
}

