'use client'

import { useState, useEffect } from 'react'
import { bookmarksApi } from '@/lib/api'
import { useBookmarkStore } from '@/lib/store'

interface AddToFolderModalProps {
  sessionId: string
  sessionTitle: string
  onClose: () => void
}

export default function AddToFolderModal({ sessionId, sessionTitle, onClose }: AddToFolderModalProps) {
  const { folders, setFolders } = useBookmarkStore()
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null)
  const [notes, setNotes] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isCreatingFolder, setIsCreatingFolder] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')
  const [newFolderColor, setNewFolderColor] = useState('#3B82F6')
  const [newFolderIcon, setNewFolderIcon] = useState('📁')

  const colorOptions = [
    '#3B82F6', '#EF4444', '#10B981', '#F59E0B', '#8B5CF6',
    '#EC4899', '#06B6D4', '#84CC16', '#F97316', '#6366F1'
  ]

  const iconOptions = ['📁', '⭐', '📚', '🔖', '💼', '🎯', '📌', '🏷️', '📝']

  useEffect(() => {
    loadFolders()
  }, [])

  const loadFolders = async () => {
    try {
      const response = await bookmarksApi.getFolders()
      setFolders(response.data)
    } catch (error) {
      console.error('Error loading folders:', error)
    }
  }

  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) return

    setIsCreatingFolder(true)
    try {
      const response = await bookmarksApi.createFolder(
        newFolderName,
        '',
        newFolderColor,
        newFolderIcon
      )
      
      // Add to local state
      setFolders([...folders, response.data])
      
      // Select the new folder
      setSelectedFolderId(response.data.id)
      
      // Reset form
      setNewFolderName('')
      setNewFolderColor('#3B82F6')
      setNewFolderIcon('📁')
      
    } catch (error) {
      console.error('Error creating folder:', error)
      alert('Failed to create folder')
    } finally {
      setIsCreatingFolder(false)
    }
  }

  const handleSave = async () => {
    if (!selectedFolderId) {
      alert('Please select a folder')
      return
    }

    setIsLoading(true)
    try {
      await bookmarksApi.addChatToFolder(selectedFolderId, sessionId, notes)
      alert('Chat saved to folder successfully!')
      onClose()
    } catch (error: any) {
      console.error('Error saving to folder:', error)
      if (error.response?.status === 409) {
        alert('This chat is already in this folder')
      } else {
        alert('Failed to save chat to folder')
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div 
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div 
        className="bg-white dark:bg-gray-900 rounded-lg shadow-xl w-full max-w-md max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-4 sm:p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg sm:text-xl font-semibold text-gray-900 dark:text-white">
              Save Conversation
            </h2>
            <button
              onClick={onClose}
              className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors"
              aria-label="Close"
            >
              <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Chat Title */}
          <div className="mb-4 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Conversation</div>
            <div className="text-sm font-medium text-gray-900 dark:text-white truncate">
              {sessionTitle}
            </div>
          </div>

          {/* Select Folder */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Select Folder
            </label>
            
            {folders.length === 0 ? (
              <div className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
                No folders yet. Create one below.
              </div>
            ) : (
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {folders.map(folder => (
                  <div
                    key={folder.id}
                    onClick={() => setSelectedFolderId(folder.id)}
                    className={`flex items-center gap-2 p-3 rounded-lg border-2 cursor-pointer transition-all ${
                      selectedFolderId === folder.id
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                    }`}
                  >
                    <div 
                      className="w-2 h-2 rounded-full flex-shrink-0" 
                      style={{ backgroundColor: folder.color }}
                    />
                    <span className="text-sm">{folder.icon}</span>
                    <span className="text-sm font-medium text-gray-900 dark:text-white flex-1">
                      {folder.name}
                    </span>
                    {selectedFolderId === folder.id && (
                      <svg className="w-5 h-5 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Create New Folder */}
          <div className="mb-4 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Or Create New Folder
            </div>
            <input
              type="text"
              value={newFolderName}
              onChange={(e) => setNewFolderName(e.target.value)}
              placeholder="Folder name..."
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white mb-2"
            />
            
            <div className="flex gap-2 mb-2">
              {colorOptions.slice(0, 5).map(color => (
                <button
                  key={color}
                  onClick={() => setNewFolderColor(color)}
                  className={`w-6 h-6 rounded-full transition-transform ${
                    newFolderColor === color ? 'ring-2 ring-offset-1 ring-gray-400 scale-110' : ''
                  }`}
                  style={{ backgroundColor: color }}
                />
              ))}
            </div>
            
            <div className="flex gap-1 mb-2">
              {iconOptions.slice(0, 6).map(icon => (
                <button
                  key={icon}
                  onClick={() => setNewFolderIcon(icon)}
                  className={`px-2 py-1 text-sm rounded border transition-colors ${
                    newFolderIcon === icon
                      ? 'bg-blue-100 dark:bg-blue-900 border-blue-500'
                      : 'border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800'
                  }`}
                >
                  {icon}
                </button>
              ))}
            </div>
            
            <button
              onClick={handleCreateFolder}
              disabled={!newFolderName.trim() || isCreatingFolder}
              className="w-full px-3 py-2 text-sm bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isCreatingFolder ? 'Creating...' : 'Create Folder'}
            </button>
          </div>

          {/* Notes */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Notes (optional)
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add a note about this conversation..."
              rows={3}
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white resize-none"
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2 text-sm border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={!selectedFolderId || isLoading}
              className="flex-1 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

