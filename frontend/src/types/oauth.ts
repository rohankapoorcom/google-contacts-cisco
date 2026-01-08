/**
 * OAuth-related TypeScript types
 */

export interface OAuthTokenInfo {
  valid: boolean
  expired: boolean
  expiry: string | null
  scopes: string[]
}

export interface OAuthStatus {
  authenticated: boolean
  token_info: OAuthTokenInfo | null
}

export interface OAuthStatusResponse {
  authenticated: boolean
  has_token_file: boolean
  credentials_valid: boolean
  credentials_expired: boolean
  has_refresh_token: boolean
  scopes: string[]
}

export interface ApiResponse<T = unknown> {
  message?: string
  detail?: string
  data?: T
}

export interface ApiError {
  detail: string
  status?: number
}
