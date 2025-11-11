/**
 * ConfigForm - Configuration form for pipeline execution.
 *
 * Features:
 * - Technology count slider with numeric input
 * - Community version selector
 * - Tavily search toggle
 * - Minimum documents input
 * - Professional validation
 * - Estimated duration indicator
 */

import React, { useState } from 'react'
import { PipelineConfig, DEFAULT_PIPELINE_CONFIG, CommunityVersion } from '../../types/pipeline'

interface ConfigFormProps {
  onSubmit: (config: PipelineConfig) => void
  onCancel: () => void
  disabled?: boolean
}

export function ConfigForm({ onSubmit, onCancel, disabled = false }: ConfigFormProps) {
  const [config, setConfig] = useState<PipelineConfig>(DEFAULT_PIPELINE_CONFIG)
  const [errors, setErrors] = useState<Record<string, string>>({})

  // Validate configuration
  const validate = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (config.tech_count < 1 || config.tech_count > 200) {
      newErrors.tech_count = 'Technology count must be between 1 and 200'
    }

    if (config.min_docs < 1 || config.min_docs > 20) {
      newErrors.min_docs = 'Minimum documents must be between 1 and 20'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  // Handle form submission
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (validate()) {
      onSubmit(config)
    }
  }

  // Estimate duration based on tech count
  const estimateDuration = (): string => {
    const seconds = config.tech_count * 10 // Rough estimate: 10 seconds per tech
    if (seconds < 60) {
      return `~${seconds}s`
    } else if (seconds < 3600) {
      return `~${Math.round(seconds / 60)}m`
    } else {
      const hours = Math.floor(seconds / 3600)
      const mins = Math.round((seconds % 3600) / 60)
      return `~${hours}h ${mins}m`
    }
  }

  // Community version descriptions
  const communityDescriptions: Record<CommunityVersion, string> = {
    v0: 'Raw communities (no lifecycle weighting)',
    v1: 'Balanced lifecycle distribution (recommended)',
    v2: 'Enhanced topic coherence',
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Technology Count */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label htmlFor="tech-count" className="text-sm font-medium text-gray-700">
            Technology Count
          </label>
          <span className="text-sm text-gray-600">{estimateDuration()} estimated</span>
        </div>

        <div className="flex items-center gap-4">
          {/* Slider */}
          <input
            id="tech-count"
            type="range"
            min="10"
            max="100"
            step="10"
            value={config.tech_count}
            onChange={(e) =>
              setConfig({ ...config, tech_count: parseInt(e.target.value) })
            }
            disabled={disabled}
            className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-[#0f766e]"
          />

          {/* Numeric input */}
          <input
            type="number"
            min="1"
            max="200"
            value={config.tech_count}
            onChange={(e) =>
              setConfig({ ...config, tech_count: parseInt(e.target.value) || 1 })
            }
            disabled={disabled}
            className="w-20 px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#0f766e] focus:border-transparent"
          />
        </div>

        {errors.tech_count && (
          <p className="text-xs text-red-600 mt-1">{errors.tech_count}</p>
        )}
      </div>

      {/* Community Version */}
      <div className="space-y-3">
        <label className="text-sm font-medium text-gray-700">Community Version</label>
        <div className="space-y-2">
          {(['v0', 'v1', 'v2'] as CommunityVersion[]).map((version) => (
            <label
              key={version}
              className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                config.community_version === version
                  ? 'bg-teal-50 border-teal-300'
                  : 'bg-gray-50 border-gray-300 hover:border-gray-400'
              }`}
            >
              <input
                type="radio"
                name="community_version"
                value={version}
                checked={config.community_version === version}
                onChange={(e) =>
                  setConfig({ ...config, community_version: e.target.value as CommunityVersion })
                }
                disabled={disabled}
                className="mt-0.5 accent-[#0f766e]"
              />
              <div className="flex-1">
                <div className="text-sm font-medium text-gray-900">{version}</div>
                <div className="text-xs text-gray-600 mt-0.5">
                  {communityDescriptions[version]}
                </div>
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* Enable Tavily Search */}
      <div className="flex items-start gap-3 p-4 bg-gray-50 rounded-lg border border-gray-300">
        <input
          type="checkbox"
          id="enable-tavily"
          checked={config.enable_tavily}
          onChange={(e) => setConfig({ ...config, enable_tavily: e.target.checked })}
          disabled={disabled}
          className="mt-0.5 accent-[#0f766e]"
        />
        <div className="flex-1">
          <label htmlFor="enable-tavily" className="text-sm font-medium text-gray-700 cursor-pointer">
            Enable Tavily Real-Time Search
          </label>
          <p className="text-xs text-gray-600 mt-1">
            Fetch current news and signals for more accurate narrative scoring. May increase execution time.
          </p>
        </div>
      </div>

      {/* Minimum Documents */}
      <div className="space-y-3">
        <label htmlFor="min-docs" className="text-sm font-medium text-gray-700">
          Minimum Documents per Technology
        </label>
        <input
          id="min-docs"
          type="number"
          min="1"
          max="20"
          value={config.min_docs}
          onChange={(e) =>
            setConfig({ ...config, min_docs: parseInt(e.target.value) || 1 })
          }
          disabled={disabled}
          className="w-full px-4 py-2.5 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#0f766e] focus:border-transparent"
        />
        <p className="text-xs text-gray-600">
          Technologies with fewer documents will be excluded from analysis
        </p>
        {errors.min_docs && (
          <p className="text-xs text-red-600 mt-1">{errors.min_docs}</p>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200">
        <button
          type="button"
          onClick={onCancel}
          disabled={disabled}
          className="px-5 py-2.5 text-sm font-medium text-gray-700 bg-gray-200 rounded-lg hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={disabled}
          className="px-5 py-2.5 text-sm font-medium text-white bg-[#0f766e] rounded-lg hover:bg-[#0d9488] focus:outline-none focus:ring-2 focus:ring-[#0f766e] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Start Analysis
        </button>
      </div>
    </form>
  )
}
