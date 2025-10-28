'use client'

import { useState } from 'react'
import GeneSetStats from './GeneSetStats'

interface GeneSetCardProps {
  geneSetId: string
  geneSetName: string
  collection: string
  subCollection?: string | null
  description?: string | null
  species: string
  geneSetSize: number
  overlapCount: number
  overlapPercentage: number
  pValue: number
  adjustedPValue?: number
  oddsRatio?: number
  matchedGenes: string[]
  allGenes?: string[]  // All genes in the gene set
  msigdbUrl?: string | null
  externalUrl?: string | null
  rank: number
}

export default function GeneSetCard({
  geneSetId,
  geneSetName,
  collection,
  subCollection,
  description,
  species,
  geneSetSize,
  overlapCount,
  overlapPercentage,
  pValue,
  adjustedPValue,
  oddsRatio,
  matchedGenes,
  allGenes,
  msigdbUrl,
  externalUrl,
  rank
}: GeneSetCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [showAllMatchedGenes, setShowAllMatchedGenes] = useState(false)
  const [showAllGeneSetGenes, setShowAllGeneSetGenes] = useState(false)
  const [copied, setCopied] = useState(false)
  const [copiedAll, setCopiedAll] = useState(false)

  const getCollectionColor = (coll: string): string => {
    const colors: Record<string, string> = {
      'H': 'bg-purple-100 text-purple-700 border-purple-300',
      'C1': 'bg-blue-100 text-blue-700 border-blue-300',
      'C2': 'bg-green-100 text-green-700 border-green-300',
      'C3': 'bg-yellow-100 text-yellow-700 border-yellow-300',
      'C4': 'bg-orange-100 text-orange-700 border-orange-300',
      'C5': 'bg-teal-100 text-teal-700 border-teal-300',
      'C6': 'bg-red-100 text-red-700 border-red-300',
      'C7': 'bg-pink-100 text-pink-700 border-pink-300',
      'C8': 'bg-indigo-100 text-indigo-700 border-indigo-300'
    }
    return colors[coll] || 'bg-gray-100 text-gray-700 border-gray-300'
  }

  const getCollectionName = (coll: string): string => {
    const names: Record<string, string> = {
      'H': 'Hallmark',
      'C1': 'Positional',
      'C2': 'Curated',
      'C3': 'Motif',
      'C4': 'Computational',
      'C5': 'Gene Ontology',
      'C6': 'Oncogenic',
      'C7': 'Immunologic',
      'C8': 'Cell Type'
    }
    return names[coll] || coll
  }

  const handleCopyGenes = async () => {
    try {
      await navigator.clipboard.writeText(matchedGenes.join(', '))
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const handleCopyAllGenes = async () => {
    if (!allGenes) return
    try {
      await navigator.clipboard.writeText(allGenes.join(', '))
      setCopiedAll(true)
      setTimeout(() => setCopiedAll(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const truncatedDescription = description && description.length > 150
    ? description.substring(0, 150) + '...'
    : description

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5 hover:shadow-lg transition-all duration-200 hover:border-purple-300">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-semibold text-gray-500">#{rank}</span>
            <span className={`text-xs px-2 py-1 rounded-md border font-medium ${getCollectionColor(collection)}`}>
              {getCollectionName(collection)}
            </span>
            {subCollection && (
              <span className="text-xs px-2 py-1 rounded-md bg-gray-100 text-gray-600 border border-gray-300">
                {subCollection}
              </span>
            )}
            <span className="text-xs px-2 py-1 rounded-md bg-blue-50 text-blue-700 border border-blue-200">
              {species === 'human' ? '🧬 Human' : '🐭 Mouse'}
            </span>
          </div>
          <h3 className="text-lg font-bold text-gray-900 break-words leading-tight">
            {geneSetName}
          </h3>
        </div>
      </div>

      {/* Description */}
      {description && (
        <div className="mb-4">
          <p className="text-sm text-gray-600 leading-relaxed">
            {isExpanded ? description : truncatedDescription}
            {description.length > 150 && (
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="ml-1 text-purple-600 hover:text-purple-800 font-medium text-sm"
              >
                {isExpanded ? 'Show less' : 'Read more'}
              </button>
            )}
          </p>
        </div>
      )}

      {/* Statistics */}
      <div className="mb-4">
        <GeneSetStats
          overlapCount={overlapCount}
          geneSetSize={geneSetSize}
          overlapPercentage={overlapPercentage}
          pValue={pValue}
          adjustedPValue={adjustedPValue}
          oddsRatio={oddsRatio}
        />
      </div>

      {/* Matched Genes */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">
            Matched Genes ({matchedGenes.length})
          </span>
          <button
            onClick={handleCopyGenes}
            className="text-xs px-2 py-1 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition-colors flex items-center gap-1"
            title="Copy genes to clipboard"
          >
            {copied ? (
              <>
                <svg className="w-3.5 h-3.5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-green-600">Copied!</span>
              </>
            ) : (
              <>
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                <span>Copy</span>
              </>
            )}
          </button>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {(showAllMatchedGenes ? matchedGenes : matchedGenes.slice(0, 10)).map((gene, idx) => (
            <span
              key={idx}
              className="inline-flex items-center px-2.5 py-1 rounded-md text-sm font-medium bg-purple-50 text-purple-700 border border-purple-200"
            >
              {gene}
            </span>
          ))}
          {matchedGenes.length > 10 && (
            <button
              onClick={() => setShowAllMatchedGenes(!showAllMatchedGenes)}
              className="inline-flex items-center px-2.5 py-1 rounded-md text-sm font-medium bg-gray-100 text-gray-700 border border-gray-300 hover:bg-gray-200 transition-colors"
            >
              {showAllMatchedGenes ? 'Show less' : `+${matchedGenes.length - 10} more`}
            </button>
          )}
        </div>
      </div>

      {/* All Genes in Set */}
      {allGenes && allGenes.length > 0 && (
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">
              All Genes in Set ({allGenes.length})
            </span>
            <button
              onClick={handleCopyAllGenes}
              className="text-xs px-2 py-1 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition-colors flex items-center gap-1"
              title="Copy all genes to clipboard"
            >
              {copiedAll ? (
                <>
                  <svg className="w-3.5 h-3.5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="text-green-600">Copied!</span>
                </>
              ) : (
                <>
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  <span>Copy All</span>
                </>
              )}
            </button>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {(showAllGeneSetGenes ? allGenes : allGenes.slice(0, 15)).map((gene, idx) => (
              <span
                key={idx}
                className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-50 text-gray-600 border border-gray-200"
              >
                {gene}
              </span>
            ))}
            {allGenes.length > 15 && (
              <button
                onClick={() => setShowAllGeneSetGenes(!showAllGeneSetGenes)}
                className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700 border border-gray-300 hover:bg-gray-200 transition-colors"
              >
                {showAllGeneSetGenes ? 'Show less' : `+${allGenes.length - 15} more`}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 pt-3 border-t border-gray-200">
        {msigdbUrl && (
          <a
            href={msigdbUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 text-sm font-medium text-purple-700 bg-purple-50 border border-purple-200 rounded-lg hover:bg-purple-100 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
            View on MSigDB
          </a>
        )}
        {externalUrl && (
          <a
            href={externalUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 text-sm font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
            </svg>
            External Link
          </a>
        )}
      </div>
    </div>
  )
}

