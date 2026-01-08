/**
 * OAuth-related TypeScript types
 * 
 * Note: Most types are re-exported from api.ts for consistency.
 * This file is maintained for backward compatibility and additional OAuth-specific types.
 */

export interface ApiResponse<T = unknown> {
  message?: string
  detail?: string
  data?: T
}

// Re-export common types from api.ts to avoid duplication
export type { OAuthStatus, ApiError } from './api'
