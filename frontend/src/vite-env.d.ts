/// <reference types="vite/client" />

/**
 * Vite Environment Variable Type Definitions
 *
 * This file extends ImportMeta to include custom environment variables
 * used by Canopy Intelligence in both development and production.
 *
 * Environment variables must be prefixed with VITE_ to be exposed to the client.
 */

interface ImportMetaEnv {
  /**
   * Backend API URL
   * - Development: http://localhost:8000
   * - Production: https://canopy-intelligence-api.onrender.com
   */
  readonly VITE_API_URL: string

  /**
   * Enable/disable pipeline execution (multi-agent analysis)
   * - 'true': Full functionality (local development)
   * - 'false': Demo mode, read-only (production)
   */
  readonly VITE_ENABLE_PIPELINE_EXECUTION: string

  /**
   * Environment identifier
   * - 'development': Local development
   * - 'production': Deployed to Vercel
   */
  readonly VITE_ENV: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
