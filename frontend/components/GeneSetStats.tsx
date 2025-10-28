'use client'

interface GeneSetStatsProps {
  overlapCount: number
  geneSetSize: number
  overlapPercentage: number
  pValue: number
  adjustedPValue?: number
  oddsRatio?: number
}

export default function GeneSetStats({
  overlapCount,
  geneSetSize,
  overlapPercentage,
  pValue,
  adjustedPValue,
  oddsRatio
}: GeneSetStatsProps) {
  
  const formatPValue = (val: number): string => {
    if (val < 0.001) {
      return val.toExponential(2)
    }
    return val.toFixed(4)
  }

  const getSignificanceColor = (val: number): string => {
    if (val < 0.001) return 'text-green-700 bg-green-100'
    if (val < 0.01) return 'text-yellow-700 bg-yellow-100'
    if (val < 0.05) return 'text-orange-700 bg-orange-100'
    return 'text-gray-700 bg-gray-100'
  }

  const getSignificanceLabel = (val: number): string => {
    if (val < 0.001) return '***'
    if (val < 0.01) return '**'
    if (val < 0.05) return '*'
    return 'ns'
  }

  return (
    <div className="space-y-3">
      {/* Overlap Statistics */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium text-gray-700">Gene Overlap</span>
          <span className="text-gray-900 font-semibold">
            {overlapCount}/{geneSetSize} ({overlapPercentage.toFixed(1)}%)
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
          <div
            className="h-2.5 rounded-full bg-gradient-to-r from-blue-500 to-purple-600 transition-all duration-500"
            style={{ width: `${Math.min(overlapPercentage, 100)}%` }}
          />
        </div>
      </div>

      {/* P-value */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <span className="text-sm font-medium text-gray-700">P-value</span>
          <button
            className="text-gray-400 hover:text-gray-600 transition-colors"
            title="Probability that the overlap occurred by chance. Lower is more significant."
          >
            <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm font-mono text-gray-900">
            {formatPValue(pValue)}
          </span>
          <span className={`text-xs px-2 py-0.5 rounded font-semibold ${getSignificanceColor(pValue)}`}>
            {getSignificanceLabel(pValue)}
          </span>
        </div>
      </div>

      {/* Adjusted P-value (FDR) */}
      {adjustedPValue !== undefined && (
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <span className="text-sm font-medium text-gray-700">Adjusted P</span>
            <button
              className="text-gray-400 hover:text-gray-600 transition-colors"
              title="FDR-corrected p-value for multiple testing. Use this for significance."
            >
              <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
            </button>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-mono text-gray-900">
              {formatPValue(adjustedPValue)}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded font-semibold ${getSignificanceColor(adjustedPValue)}`}>
              {getSignificanceLabel(adjustedPValue)}
            </span>
          </div>
        </div>
      )}

      {/* Odds Ratio */}
      {oddsRatio !== undefined && oddsRatio > 0 && oddsRatio < Infinity && (
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <span className="text-sm font-medium text-gray-700">Odds Ratio</span>
            <button
              className="text-gray-400 hover:text-gray-600 transition-colors"
              title="Strength of association. Values > 1 indicate enrichment."
            >
              <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
            </button>
          </div>
          <span className="text-sm font-mono text-gray-900">
            {oddsRatio.toFixed(2)}
          </span>
        </div>
      )}

      {/* Significance Legend */}
      <div className="pt-2 mt-2 border-t border-gray-200">
        <div className="flex items-center gap-3 text-xs text-gray-500">
          <span>Significance:</span>
          <span className="font-mono">*** p&lt;0.001</span>
          <span className="font-mono">** p&lt;0.01</span>
          <span className="font-mono">* p&lt;0.05</span>
          <span className="font-mono">ns p≥0.05</span>
        </div>
      </div>
    </div>
  )
}

