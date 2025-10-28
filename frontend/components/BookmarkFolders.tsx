'use client'

import { useEffect, useState } from 'react'
import { bookmarksApi } from '@/lib/api'
import { useBookmarkStore } from '@/lib/store'

interface BookmarkChat {
  id: string
  session_id: string
  session_title: string
  notes?: string
  created_at: string
  updated_at: string
}

interface BookmarkFoldersProps {
  onSelectChat?: (sessionId: string) => void
}

export default function BookmarkFolders({ onSelectChat }: BookmarkFoldersProps) {
  const { folders, setFolders, selectedFolderId, setSelectedFolder, addFolder, deleteFolder } = useBookmarkStore()
  const [isLoading, setIsLoading] = useState(true)
  const [isCreating, setIsCreating] = useState(false)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')
  const [newFolderColor, setNewFolderColor] = useState('#3B82F6')
  const [newFolderIcon, setNewFolderIcon] = useState('📁')
  const [folderChats, setFolderChats] = useState<BookmarkChat[]>([])
  const [isLoadingChats, setIsLoadingChats] = useState(false)

  useEffect(() => {
    fetchFolders()
  }, [])

  useEffect(() => {
    if (selectedFolderId) {
      fetchFolderChats(selectedFolderId)
    } else {
      setFolderChats([])
    }
  }, [selectedFolderId])

  const fetchFolders = async () => {
    try {
      setIsLoading(true)
      const response = await bookmarksApi.getFolders()
      setFolders(response.data)
    } catch (error) {
      console.error('Failed to fetch folders:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const fetchFolderChats = async (folderId: string) => {
    try {
      setIsLoadingChats(true)
      const response = await bookmarksApi.getFolderChats(folderId)
      setFolderChats(response.data)
    } catch (error) {
      console.error('Failed to fetch folder chats:', error)
      setFolderChats([])
    } finally {
      setIsLoadingChats(false)
    }
  }

  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) return

    try {
      setIsCreating(true)
      const response = await bookmarksApi.createFolder(
        newFolderName,
        '',
        newFolderColor,
        newFolderIcon
      )
      addFolder(response.data)
      setShowCreateModal(false)
      setNewFolderName('')
      setNewFolderColor('#3B82F6')
      setNewFolderIcon('📁')
    } catch (error) {
      console.error('Failed to create folder:', error)
      alert('Failed to create folder')
    } finally {
      setIsCreating(false)
    }
  }

  const handleDeleteFolder = async (folderId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm('Are you sure you want to delete this folder? The conversations will not be deleted.')) return

    try {
      await bookmarksApi.deleteFolder(folderId)
      deleteFolder(folderId)
      if (selectedFolderId === folderId) {
        setSelectedFolder(null)
        setFolderChats([])
      }
    } catch (error) {
      console.error('Failed to delete folder:', error)
      alert('Failed to delete folder')
    }
  }

  const handleRemoveChatFromFolder = async (chatId: string, sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!selectedFolderId) return
    
    if (!confirm('Remove this conversation from the folder?')) return

    try {
      await bookmarksApi.removeChatFromFolder(selectedFolderId, sessionId)
      setFolderChats(prev => prev.filter(chat => chat.id !== chatId))
      // Refresh folders to update count
      fetchFolders()
    } catch (error) {
      console.error('Failed to remove chat from folder:', error)
      alert('Failed to remove conversation')
    }
  }

  const handleSelectFolder = (folderId: string) => {
    if (selectedFolderId === folderId) {
      // Clicking on the same folder deselects it
      setSelectedFolder(null)
    } else {
      setSelectedFolder(folderId)
    }
  }

  const handleBackToFolders = () => {
    setSelectedFolder(null)
  }

  const handleChatClick = (sessionId: string) => {
    onSelectChat?.(sessionId)
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

  const iconOptions = ['📁', '⭐', '📚', '🔖', '💼', '🎯', '📌', '🏷️', '📝']
  const colorOptions = [
    '#3B82F6', '#EF4444', '#10B981', '#F59E0B', '#8B5CF6',
    '#EC4899', '#06B6D4', '#84CC16', '#F97316', '#6366F1'
  ]

  // Loading state
  if (isLoading) {
    return (
      <div className="p-3 space-y-2">
        {[1, 2, 3].map(i => (
          <div key={i} className="h-12 bg-gray-100 dark:bg-gray-800 rounded animate-pulse" />
        ))}
      </div>
    )
  }

  // Show folder contents when a folder is selected
  if (selectedFolderId) {
    const selectedFolder = folders.find(f => f.id === selectedFolderId)
    
    return (
      <div className="h-full flex flex-col bg-white dark:bg-gray-900">
        {/* Header with back button */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-800 flex-shrink-0 bg-white dark:bg-gray-900">
          <button
            onClick={handleBackToFolders}
            className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white mb-3 font-medium"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Folders
          </button>
          
          {selectedFolder && (
            <div className="flex items-center gap-2">
              <div 
                className="w-2 h-2 rounded-full flex-shrink-0" 
                style={{ backgroundColor: selectedFolder.color }}
              />
              <span className="text-lg flex-shrink-0">{selectedFolder.icon}</span>
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white flex-1 truncate">
                {selectedFolder.name}
              </h3>
              <span className="text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-[#1a1a1a] px-2 py-0.5 rounded-full">
                {folderChats.length}
              </span>
            </div>
          )}
        </div>

        {/* Chats List */}
        <div className="flex-1 overflow-y-auto p-3 bg-[#f8f9fa] dark:bg-[#1a1a1a]">
          {isLoadingChats ? (
            <div className="space-y-2">
              {[1, 2].map(i => (
                <div key={i} className="h-16 bg-white dark:bg-gray-800 rounded-lg animate-pulse" />
              ))}
            </div>
          ) : folderChats.length === 0 ? (
            <div className="text-center py-12 text-sm text-[#5f6368] dark:text-gray-400">
              No conversations saved in this folder yet.
            </div>
          ) : (
            <div className="space-y-1.5">
              {folderChats.map(chat => (
                <div
                  key={chat.id}
                  className="group p-3 rounded-lg border border-transparent hover:border-[#e8eaed] dark:hover:border-gray-700 hover:shadow-sm transition-all cursor-pointer bg-white dark:bg-gray-800"
                  onClick={() => handleChatClick(chat.session_id)}
                >
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-gray-900 dark:text-white truncate">
                        {chat.session_title}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        Saved {formatDate(chat.created_at)}
                      </div>
                    </div>
                    <button
                      onClick={(e) => handleRemoveChatFromFolder(chat.id, chat.session_id, e)}
                      className="opacity-0 group-hover:opacity-100 p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-all flex-shrink-0"
                      title="Remove from folder"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                  
                  {chat.notes && (
                    <div className="mt-2 pt-2 border-t border-gray-100 dark:border-gray-800">
                      <div className="text-xs text-gray-600 dark:text-gray-400 italic line-clamp-2">
                        {chat.notes}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    )
  }

  // Show folder list
  return (
    <div className="h-full flex flex-col bg-white dark:bg-gray-900">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-800 flex-shrink-0 bg-white dark:bg-gray-900">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
          Bookmark Folders
        </h3>
        <button
          onClick={() => setShowCreateModal(true)}
          className="p-1.5 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          title="Create folder"
          aria-label="Create folder"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 bg-[#f8f9fa] dark:bg-[#1a1a1a]">
        {folders.length === 0 ? (
          <div className="text-center py-12 text-sm text-[#5f6368] dark:text-gray-400">
            No bookmark folders yet.
            <br />
            Click + to create one.
          </div>
        ) : (
          <div className="space-y-1.5">
            {folders.map(folder => (
              <div
                key={folder.id}
                className="group flex items-center justify-between p-3 rounded-lg cursor-pointer transition-all bg-white dark:bg-gray-800 hover:shadow-sm border border-transparent hover:border-[#e8eaed] dark:hover:border-gray-700"
                onClick={() => handleSelectFolder(folder.id)}
              >
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <div 
                    className="w-2 h-2 rounded-full flex-shrink-0" 
                    style={{ backgroundColor: folder.color }}
                  />
                  <span className="text-lg flex-shrink-0">{folder.icon}</span>
                  <span className="text-sm font-medium text-gray-900 dark:text-white truncate">
                    {folder.name}
                  </span>
                  {folder.bookmark_count !== undefined && folder.bookmark_count > 0 && (
                    <span className="text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-[#1a1a1a] px-2 py-0.5 rounded-full">
                      {folder.bookmark_count}
                    </span>
                  )}
                </div>
                <button
                  onClick={(e) => handleDeleteFolder(folder.id, e)}
                  className="opacity-0 group-hover:opacity-100 p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-all flex-shrink-0"
                  title="Delete folder"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create Folder Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowCreateModal(false)}>
          <div className="bg-white dark:bg-gray-900 rounded-lg p-4 sm:p-6 w-full max-w-md max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg sm:text-xl font-semibold mb-4 text-gray-900 dark:text-white">
              Create Bookmark Folder
            </h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Folder Name
                </label>
                <input
                  type="text"
                  value={newFolderName}
                  onChange={(e) => setNewFolderName(e.target.value)}
                  placeholder="My Research Papers"
                  className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Color
                </label>
                <div className="flex gap-2 flex-wrap">
                  {colorOptions.map(color => (
                    <button
                      key={color}
                      onClick={() => setNewFolderColor(color)}
                      className={`w-8 h-8 rounded-full transition-transform ${
                        newFolderColor === color ? 'ring-2 ring-offset-2 ring-gray-400 scale-110' : 'hover:scale-110'
                      }`}
                      style={{ backgroundColor: color }}
                      aria-label={`Select ${color} color`}
                    />
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Icon
                </label>
                <div className="flex gap-2 flex-wrap">
                  {iconOptions.map(icon => (
                    <button
                      key={icon}
                      onClick={() => setNewFolderIcon(icon)}
                      className={`px-3 py-1 text-lg rounded border transition-colors ${
                        newFolderIcon === icon
                          ? 'bg-blue-100 dark:bg-blue-900 border-blue-500 text-blue-700 dark:text-blue-300'
                          : 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                      }`}
                    >
                      {icon}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowCreateModal(false)}
                className="flex-1 px-4 py-2 text-sm border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateFolder}
                disabled={!newFolderName.trim() || isCreating}
                className="flex-1 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isCreating ? 'Creating...' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
