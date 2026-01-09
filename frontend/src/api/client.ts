/**
 * API client for backend communication.
 * Provides type-safe methods for all backend API endpoints.
 */
import axios, { type AxiosInstance, type AxiosError } from 'axios'
import type {
  ContactListResponse,
  Contact,
  SearchResponse,
  SyncStatus,
  SyncInfo,
  SyncTriggerResponse,
  SyncHistoryResponse,
  SyncStatisticsResponse,
  OAuthStatus,
  HealthResponse,
  ContactStats,
  OAuthUrlResponse,
  OAuthCallbackResponse,
  ApiError,
} from '@/types/api'

/**
 * API client class for interacting with the backend.
 */
class ApiClient {
  private client: AxiosInstance

  constructor() {
    // baseURL is intentionally empty:
    // - Development: Vite proxy (vite.config.ts) forwards /api, /auth, etc. to backend
    // - Production: Frontend served from same origin as API, no proxy needed
    this.client = axios.create({
      baseURL: import.meta.env.DEV ? '' : '',
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000, // 30 second timeout
    })

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError<ApiError>) => {
        // Log errors in development
        if (import.meta.env.DEV) {
          console.error('API Error:', {
            url: error.config?.url,
            method: error.config?.method,
            status: error.response?.status,
            data: error.response?.data,
          })
        }
        return Promise.reject(error)
      }
    )
  }

  // =====================
  // Health & Status
  // =====================

  /**
   * Check API health status.
   */
  async getHealth(): Promise<HealthResponse> {
    const response = await this.client.get<HealthResponse>('/health')
    return response.data
  }

  // =====================
  // Contacts
  // =====================

  /**
   * Get a paginated list of contacts.
   */
  async getContacts(params?: {
    limit?: number
    offset?: number
    sort?: 'name' | 'recent'
    group?: string
  }): Promise<ContactListResponse> {
    const response = await this.client.get<ContactListResponse>('/api/contacts', { params })
    return response.data
  }

  /**
   * Get a single contact by ID.
   */
  async getContact(id: string): Promise<Contact> {
    const response = await this.client.get<Contact>(`/api/contacts/${id}`)
    return response.data
  }

  /**
   * Get contact statistics.
   */
  async getContactStats(): Promise<ContactStats> {
    const response = await this.client.get<ContactStats>('/api/contacts/stats')
    return response.data
  }

  // =====================
  // Search
  // =====================

  /**
   * Search contacts by name or phone number.
   */
  async search(query: string, limit?: number): Promise<SearchResponse> {
    const response = await this.client.get<SearchResponse>('/api/search', {
      params: { q: query, limit },
    })
    return response.data
  }

  // =====================
  // Sync
  // =====================

  /**
   * Get current sync status.
   */
  async getSyncStatus(): Promise<SyncStatus> {
    const response = await this.client.get<SyncStatus>('/api/sync/status')
    return response.data
  }

  /**
   * Trigger automatic synchronization (chooses full or incremental).
   */
  async triggerSync(): Promise<SyncTriggerResponse> {
    const response = await this.client.post<SyncTriggerResponse>('/api/sync')
    return response.data
  }

  /**
   * Trigger a full synchronization (re-sync all contacts).
   */
  async triggerFullSync(): Promise<SyncTriggerResponse> {
    const response = await this.client.post<SyncTriggerResponse>('/api/sync/full')
    return response.data
  }

  /**
   * Trigger an incremental synchronization (only changed contacts).
   */
  async triggerIncrementalSync(): Promise<SyncTriggerResponse> {
    const response = await this.client.post<SyncTriggerResponse>('/api/sync/incremental')
    return response.data
  }

  /**
   * Get sync history.
   */
  async getSyncHistory(limit: number = 10): Promise<SyncHistoryResponse> {
    const response = await this.client.get<SyncHistoryResponse>('/api/sync/history', {
      params: { limit },
    })
    return response.data
  }

  /**
   * Get comprehensive sync statistics.
   */
  async getSyncStatistics(): Promise<SyncStatisticsResponse> {
    const response = await this.client.get<SyncStatisticsResponse>('/api/sync/statistics')
    return response.data
  }

  /**
   * Check if a full sync is needed.
   */
  async checkNeedsSync(): Promise<{ needs_full_sync: boolean; reason: string }> {
    const response = await this.client.get<{ needs_full_sync: boolean; reason: string }>('/api/sync/needs-sync')
    return response.data
  }

  // =====================
  // OAuth / Authentication
  // =====================

  /**
   * Get OAuth authentication status.
   */
  async getOAuthStatus(): Promise<OAuthStatus> {
    const response = await this.client.get<OAuthStatus>('/auth/status')
    return response.data
  }

  /**
   * Get OAuth authorization URL to start authentication flow.
   */
  async getOAuthUrl(): Promise<OAuthUrlResponse> {
    const response = await this.client.get<OAuthUrlResponse>('/auth/url')
    return response.data
  }

  /**
   * Handle OAuth callback with authorization code.
   */
  async handleOAuthCallback(code: string, state?: string): Promise<OAuthCallbackResponse> {
    const response = await this.client.get<OAuthCallbackResponse>('/auth/callback', {
      params: { code, state },
    })
    return response.data
  }

  /**
   * Refresh the OAuth token.
   */
  async refreshToken(): Promise<{ message: string }> {
    const response = await this.client.post('/auth/refresh')
    return response.data
  }

  /**
   * Disconnect from Google (revoke OAuth tokens).
   */
  async disconnect(): Promise<{ message: string }> {
    const response = await this.client.post('/auth/disconnect')
    return response.data
  }
}

// Export singleton instance
export const api = new ApiClient()

// Also export the class for testing purposes
export { ApiClient }

