/**
 * API type definitions for the Google Contacts Cisco Directory application.
 * These types mirror the backend Pydantic schemas for type-safe API communication.
 */

/**
 * Phone number data from contacts.
 */
export interface PhoneNumber {
  id: string
  value: string
  display_value: string
  type: string
  primary: boolean
}

/**
 * Email address data from contacts.
 */
export interface EmailAddress {
  id: string
  value: string
  type: string
  primary: boolean
}

/**
 * Contact information.
 */
export interface Contact {
  id: string
  display_name: string
  given_name?: string
  family_name?: string
  phone_numbers: PhoneNumber[]
  email_addresses: EmailAddress[]
  updated_at?: string
}

/**
 * Paginated list of contacts response.
 */
export interface ContactListResponse {
  contacts: Contact[]
  total: number
  offset: number
  limit: number
  has_more: boolean
}

/**
 * Individual search result with match metadata.
 */
export interface SearchResult {
  id: string
  display_name: string
  given_name?: string
  family_name?: string
  phone_numbers: PhoneNumber[]
  email_addresses: EmailAddress[]
  match_type: 'exact' | 'prefix' | 'substring' | 'phone'
  match_field: string
}

/**
 * Search API response with results and metadata.
 */
export interface SearchResponse {
  results: SearchResult[]
  count: number
  query: string
  elapsed_ms: number
}

/**
 * Synchronization status from the sync service.
 */
export interface SyncStatus {
  status: 'idle' | 'running' | 'completed' | 'error'
  progress: number
  current_operation: string
  stats: {
    added: number
    updated: number
    deleted: number
  }
  started_at?: string
  completed_at?: string
  error?: string
}

/**
 * OAuth authentication status.
 */
export interface OAuthStatus {
  authenticated: boolean
  token_info?: {
    valid: boolean
    expired: boolean
    expiry?: string
    scopes: string[]
  }
}

/**
 * Sync information response.
 */
export interface SyncInfo {
  total_contacts: number
  last_sync?: string
  next_sync?: string
  sync_token?: string
}

/**
 * Generic API error response.
 */
export interface ApiError {
  detail: string
  status_code?: number
}

/**
 * Health check response.
 */
export interface HealthResponse {
  status: 'healthy' | 'unhealthy'
  version: string
  debug: boolean
  config_valid: boolean
  config_errors: string[]
}

/**
 * Contact statistics.
 */
export interface ContactStats {
  total_contacts: number
  contacts_with_phone: number
  contacts_with_email: number
  total_phone_numbers: number
  total_emails: number
}

/**
 * OAuth URL response for starting authentication.
 */
export interface OAuthUrlResponse {
  auth_url: string
}

/**
 * OAuth callback response after successful authentication.
 */
export interface OAuthCallbackResponse {
  success: boolean
  message: string
}

