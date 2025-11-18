'use client'

import { useMSigDBStore } from '@/lib/store'

export default function SearchTypeToggle() {
  const { searchType, setSearchType } = useMSigDBStore()

  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg">
      <label className="text-sm font-medium text-gray-700">Mode:</label>
      <div className="flex gap-1 bg-white rounded-md border border-gray-300 p-1">
        <button
          onClick={() => setSearchType('none')}
          className={`px-3 py-1.5 text-sm rounded transition-all ${
            searchType === 'none'
              ? 'bg-green-600 text-white font-medium shadow-sm'
              : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
          }`}
          title="Chat with AI (no database search)"
        >
          <div className="flex items-center gap-1.5">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
            <span>Chat</span>
          </div>
        </button>
        <button
          onClick={() => setSearchType('pubmed')}
          className={`px-3 py-1.5 text-sm rounded transition-all ${
            searchType === 'pubmed'
              ? 'bg-blue-600 text-white font-medium shadow-sm'
              : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
          }`}
          title="Search PubMed scientific literature"
        >
          <div className="flex items-center gap-1.5">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
            <span>PubMed</span>
          </div>
        </button>
        <button
          onClick={() => setSearchType('msigdb')}
          className={`px-3 py-1.5 text-sm rounded transition-all ${
            searchType === 'msigdb'
              ? 'bg-purple-600 text-white font-medium shadow-sm'
              : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
          }`}
          title="Search MSigDB gene sets"
        >
          <div className="flex items-center gap-1.5">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
            </svg>
            <span>MSigDB</span>
          </div>
        </button>
      </div>
      {searchType === 'msigdb' && (
        <span className="text-xs text-purple-600 bg-purple-50 px-2 py-1 rounded">
          Enter gene symbols
        </span>
      )}
      {searchType === 'pubmed' && (
        <span className="text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded">
          Search research papers
        </span>
      )}
      {searchType === 'none' && (
        <span className="text-xs text-green-600 bg-green-50 px-2 py-1 rounded">
          General conversation
        </span>
      )}
    </div>
  )
}

