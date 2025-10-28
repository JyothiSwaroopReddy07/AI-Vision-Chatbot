'use client'

import { useEffect } from 'react'

interface Citation {
  source_type: string
  source_id: string
  title: string
  authors?: string
  journal?: string
  url?: string
  excerpt?: string
  relevance_score?: number
}

interface SourcesModalProps {
  isOpen: boolean
  onClose: () => void
  citations: Citation[]
}

export default function SourcesModal({ isOpen, onClose, citations }: SourcesModalProps) {
  // Close on escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    
    if (isOpen) {
      document.addEventListener('keydown', handleEscape)
      document.body.style.overflow = 'hidden'
    }
    
    return () => {
      document.removeEventListener('keydown', handleEscape)
      document.body.style.overflow = 'unset'
    }
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50 backdrop-blur-sm">
      {/* Modal Container */}
      <div className="relative w-full max-w-3xl max-h-[85vh] bg-white rounded-xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900">
            Sources ({citations.length})
          </h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            aria-label="Close modal"
          >
            <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto max-h-[calc(85vh-80px)] px-6 py-4">
          <div className="space-y-4">
            {citations.map((citation, idx) => (
              <div
                key={idx}
                className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 hover:bg-blue-50 transition-all"
              >
                <div className="flex gap-4">
                  {/* Source Number */}
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-semibold text-sm">
                      {idx + 1}
                    </div>
                  </div>

                  {/* Source Details */}
                  <div className="flex-1 min-w-0">
                    <a
                      href={citation.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="group"
                    >
                      <h3 className="font-semibold text-gray-900 mb-2 group-hover:text-blue-600 transition-colors line-clamp-2">
                        {citation.title}
                      </h3>
                    </a>

                    {citation.authors && (
                      <p className="text-sm text-gray-600 mb-1">
                        <span className="font-medium">Authors:</span> {citation.authors}
                      </p>
                    )}

                    {citation.journal && (
                      <p className="text-sm text-gray-600 mb-2">
                        <span className="font-medium">Journal:</span> {citation.journal}
                      </p>
                    )}

                    {citation.excerpt && (
                      <p className="text-sm text-gray-700 mt-3 pt-3 border-t border-gray-100 line-clamp-3">
                        {citation.excerpt}
                      </p>
                    )}

                    <a
                      href={citation.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 mt-3 text-sm text-blue-600 hover:text-blue-700 font-medium"
                    >
                      <span>View source</span>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                    </a>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

