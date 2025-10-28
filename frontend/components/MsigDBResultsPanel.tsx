'use client'

import { useState, useMemo, useEffect } from 'react'
import { useMSigDBStore } from '@/lib/store'
import GeneSetCard from './GeneSetCard'

export default function MsigDBResultsPanel() {
  const {
    currentResults,
    showResultsPanel,
    setShowResultsPanel,
    queryGenes,
    species,
    numResults,
    isLoading
  } = useMSigDBStore()

  const [sortBy, setSortBy] = useState<'overlap' | 'pvalue' | 'name'>('overlap')
  const [filterCollection, setFilterCollection] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [resultsKey, setResultsKey] = useState(0)
  
  // Reset filters and scroll to top when results change
  useEffect(() => {
    if (currentResults && currentResults.length > 0) {
      setSortBy('overlap')
      setFilterCollection('all')
      setSearchQuery('')
      setResultsKey(prev => prev + 1) // Force re-render
      
      // Scroll to top of results
      const resultsContainer = document.getElementById('msigdb-results-container')
      if (resultsContainer) {
        resultsContainer.scrollTop = 0
      }
    }
  }, [currentResults])

  // Get unique collections from results
  const collections = useMemo(() => {
    if (!currentResults) return []
    const unique = new Set(currentResults.map(r => r.collection))
    return Array.from(unique).sort()
  }, [currentResults])

  // Filter and sort results
  const filteredResults = useMemo(() => {
    if (!currentResults) return []
    
    let filtered = [...currentResults]

    // Filter by collection
    if (filterCollection !== 'all') {
      filtered = filtered.filter(r => r.collection === filterCollection)
    }

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(r =>
        r.gene_set_name.toLowerCase().includes(query) ||
        r.description?.toLowerCase().includes(query) ||
        r.matched_genes.some(g => g.toLowerCase().includes(query))
      )
    }

    // Sort
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'overlap':
          return b.overlap_count - a.overlap_count
        case 'pvalue':
          return a.p_value - b.p_value
        case 'name':
          return a.gene_set_name.localeCompare(b.gene_set_name)
        default:
          return 0
      }
    })

    return filtered
  }, [currentResults, filterCollection, searchQuery, sortBy])

  const handleExport = (format: 'csv' | 'json') => {
    if (!currentResults) return

    if (format === 'json') {
      const dataStr = JSON.stringify(currentResults, null, 2)
      const blob = new Blob([dataStr], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `msigdb_results_${new Date().toISOString().split('T')[0]}.json`
      link.click()
      URL.revokeObjectURL(url)
    } else if (format === 'csv') {
      const headers = [
        'Rank',
        'Gene Set Name',
        'Collection',
        'Species',
        'Overlap Count',
        'Gene Set Size',
        'Overlap %',
        'P-value',
        'Adjusted P-value',
        'Matched Genes'
      ]
      
      const rows = currentResults.map(r => [
        r.rank,
        r.gene_set_name,
        r.collection,
        r.species,
        r.overlap_count,
        r.gene_set_size,
        r.overlap_percentage.toFixed(2),
        r.p_value.toExponential(3),
        r.adjusted_p_value?.toExponential(3) || 'N/A',
        r.matched_genes.join('; ')
      ])

      const csv = [headers, ...rows]
        .map(row => row.map(cell => `"${cell}"`).join(','))
        .join('\n')

      const blob = new Blob([csv], { type: 'text/csv' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `msigdb_results_${new Date().toISOString().split('T')[0]}.csv`
      link.click()
      URL.revokeObjectURL(url)
    }
  }

  if (!showResultsPanel) return null

  return (
    <>
      {/* Overlay for mobile */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
        onClick={() => setShowResultsPanel(false)}
      />

      {/* Panel */}
      <div className="fixed lg:relative inset-y-0 right-0 z-50 w-full lg:w-[35%] xl:w-[30%] bg-white border-l border-gray-200 shadow-2xl lg:shadow-none flex flex-col overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white p-4 flex-shrink-0">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xl font-bold">MSigDB Results</h2>
            <button
              onClick={() => setShowResultsPanel(false)}
              className="p-2 hover:bg-white/20 rounded-lg transition-colors"
              aria-label="Close panel"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Summary */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              <span className="font-medium">{numResults} gene sets found</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
              </svg>
              <span>{queryGenes.length} genes queried</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="capitalize">{species}</span>
            </div>
          </div>
        </div>

        {/* Controls */}
        <div className="p-4 border-b border-gray-200 space-y-3 bg-gray-50 flex-shrink-0">
          {/* Search within results */}
          <div className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search results..."
              className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 text-sm"
            />
            <svg className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>

          <div className="grid grid-cols-2 gap-2">
            {/* Collection Filter */}
            <select
              value={filterCollection}
              onChange={(e) => setFilterCollection(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              <option value="all">All Collections</option>
              {collections.map(c => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>

            {/* Sort */}
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as 'overlap' | 'pvalue' | 'name')}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              <option value="overlap">Sort by Overlap</option>
              <option value="pvalue">Sort by P-value</option>
              <option value="name">Sort by Name</option>
            </select>
          </div>

          {/* Export buttons */}
          <div className="flex gap-2">
            <button
              onClick={() => handleExport('csv')}
              className="flex-1 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors flex items-center justify-center gap-1.5"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Export CSV
            </button>
            <button
              onClick={() => handleExport('json')}
              className="flex-1 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors flex items-center justify-center gap-1.5"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Export JSON
            </button>
          </div>

          {/* Result count */}
          <div className="text-sm text-gray-600">
            Showing {filteredResults.length} of {numResults} results
          </div>
        </div>

        {/* Results List */}
        <div id="msigdb-results-container" className="flex-1 overflow-y-auto p-4 space-y-4">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-20">
              {/* Loading Animation */}
              <div className="relative w-20 h-20 mb-6">
                <div className="absolute top-0 left-0 w-full h-full">
                  <div className="w-20 h-20 border-4 border-purple-200 border-t-purple-600 rounded-full animate-spin"></div>
                </div>
              </div>
              <h3 className="text-lg font-semibold text-gray-700 mb-2">Loading Gene Sets...</h3>
              <p className="text-sm text-gray-500">Searching MSigDB for matching gene sets</p>
            </div>
          ) : filteredResults.length > 0 ? (
            filteredResults.map((result, idx) => (
              <GeneSetCard
                key={`${result.gene_set_id}-${idx}-${resultsKey}`}
                geneSetId={result.gene_set_id}
                geneSetName={result.gene_set_name}
                collection={result.collection}
                subCollection={result.sub_collection}
                description={result.description}
                species={result.species}
                geneSetSize={result.gene_set_size}
                overlapCount={result.overlap_count}
                overlapPercentage={result.overlap_percentage}
                pValue={result.p_value}
                adjustedPValue={result.adjusted_p_value}
                oddsRatio={result.odds_ratio}
                matchedGenes={result.matched_genes}
                allGenes={result.all_genes}
                msigdbUrl={result.msigdb_url}
                externalUrl={result.external_url}
                rank={result.rank}
              />
            ))
          ) : (
            <div className="text-center py-12">
              <svg className="w-16 h-16 mx-auto text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-gray-600 font-medium mb-2">No results match your filters</p>
              <p className="text-sm text-gray-500">Try adjusting your search or filter settings</p>
            </div>
          )}
        </div>
      </div>
    </>
  )
}

