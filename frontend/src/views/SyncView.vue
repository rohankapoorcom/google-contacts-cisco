<script setup lang="ts">
/**
 * SyncView - Comprehensive sync management interface.
 * 
 * Features:
 * - Real-time sync status display
 * - Manual sync trigger buttons (auto, full, incremental)
 * - Sync statistics and history
 * - Error handling and display
 * - OAuth status check
 */
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { api } from '@/api/client'
import type {
  SyncStatus,
  SyncStatisticsResponse,
  SyncHistoryResponse,
  SyncTriggerResponse,
  OAuthStatus,
} from '@/types/api'

// =====================
// State
// =====================

const syncStatus = ref<SyncStatus | null>(null)
const syncStatistics = ref<SyncStatisticsResponse | null>(null)
const syncHistory = ref<SyncHistoryResponse | null>(null)
const oauthStatus = ref<OAuthStatus | null>(null)

const loading = ref(true)
const syncing = ref(false)
const error = ref<string | null>(null)
const successMessage = ref<string | null>(null)

let pollInterval: number | null = null

// =====================
// Computed
// =====================

const statusColor = computed(() => {
  if (!syncStatus.value) return 'gray'
  
  const status = syncStatus.value.status.toLowerCase()
  if (status.includes('error')) return 'red'
  if (status === 'syncing') return 'blue'
  if (status === 'idle' || status === 'completed') return 'green'
  if (status === 'never_synced') return 'yellow'
  return 'gray'
})

const statusIcon = computed(() => {
  const color = statusColor.value
  if (color === 'red') return '❌'
  if (color === 'blue') return '🔄'
  if (color === 'green') return '✅'
  if (color === 'yellow') return '⚠️'
  return '⚪'
})

const statusText = computed(() => {
  if (!syncStatus.value) return 'Unknown'
  
  const status = syncStatus.value.status
  if (status === 'never_synced') return 'Never Synced'
  if (status === 'syncing') return 'Syncing...'
  if (status === 'idle') return 'Idle'
  if (status === 'error') return 'Error'
  
  // Capitalize first letter
  return status.charAt(0).toUpperCase() + status.slice(1)
})

const lastSyncText = computed(() => {
  if (!syncStatus.value?.last_sync_at) return 'Never'
  
  const date = new Date(syncStatus.value.last_sync_at)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMinutes = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMinutes / 60)
  const diffDays = Math.floor(diffHours / 24)
  
  if (diffMinutes < 1) return 'Just now'
  if (diffMinutes < 60) return `${diffMinutes} minute${diffMinutes !== 1 ? 's' : ''} ago`
  if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`
  if (diffDays < 7) return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`
  
  return date.toLocaleString()
})

const canSync = computed(() => {
  return oauthStatus.value?.authenticated && !syncing.value
})

// =====================
// Methods
// =====================

async function loadData() {
  try {
    loading.value = true
    error.value = null
    
    // Load all data in parallel
    const [statusRes, statsRes, historyRes, oauthRes] = await Promise.allSettled([
      api.getSyncStatus(),
      api.getSyncStatistics(),
      api.getSyncHistory(10),
      api.getOAuthStatus(),
    ])
    
    if (statusRes.status === 'fulfilled') {
      syncStatus.value = statusRes.value
    } else {
      console.error('Failed to load sync status:', statusRes.reason)
      const err = statusRes.reason as any
      error.value = err.response?.data?.detail || err.message || 'Failed to load sync data'
    }
    
    if (statsRes.status === 'fulfilled') {
      syncStatistics.value = statsRes.value
    }
    
    if (historyRes.status === 'fulfilled') {
      syncHistory.value = historyRes.value
    }
    
    if (oauthRes.status === 'fulfilled') {
      oauthStatus.value = oauthRes.value
    }
  } finally {
    loading.value = false
  }
}

async function triggerAutoSync() {
  if (!canSync.value) return
  
  try {
    syncing.value = true
    error.value = null
    successMessage.value = null
    
    const response = await api.triggerSync()
    successMessage.value = response.message
    
    // Start polling for status updates
    startPolling()
    
    // Reload data after a short delay
    setTimeout(loadData, 1000)
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || 'Failed to trigger sync'
  } finally {
    syncing.value = false
  }
}

async function triggerFullSync() {
  if (!canSync.value) return
  
  if (!confirm('Are you sure you want to perform a full sync? This will re-sync all contacts and may take a while.')) {
    return
  }
  
  try {
    syncing.value = true
    error.value = null
    successMessage.value = null
    
    const response = await api.triggerFullSync()
    successMessage.value = response.message
    
    // Start polling for status updates
    startPolling()
    
    // Reload data after a short delay
    setTimeout(loadData, 1000)
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || 'Failed to trigger full sync'
  } finally {
    syncing.value = false
  }
}

async function triggerIncrementalSync() {
  if (!canSync.value) return
  
  try {
    syncing.value = true
    error.value = null
    successMessage.value = null
    
    const response = await api.triggerIncrementalSync()
    successMessage.value = response.message
    
    // Start polling for status updates
    startPolling()
    
    // Reload data after a short delay
    setTimeout(loadData, 1000)
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || 'Failed to trigger incremental sync'
  } finally {
    syncing.value = false
  }
}

function startPolling() {
  if (pollInterval) return
  
  pollInterval = window.setInterval(async () => {
    try {
      const status = await api.getSyncStatus()
      syncStatus.value = status
      
      // Stop polling if sync is complete
      if (status.status !== 'syncing') {
        stopPolling()
        await loadData()
      }
    } catch (err) {
      // Silently fail - don't interrupt user experience
      console.error('Polling error:', err)
    }
  }, 2000) // Poll every 2 seconds
}

function stopPolling() {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return 'Never'
  const date = new Date(dateStr)
  return date.toLocaleString()
}

function dismissSuccess() {
  successMessage.value = null
}

function dismissError() {
  error.value = null
}

// =====================
// Lifecycle
// =====================

onMounted(() => {
  loadData()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 py-12 sm:px-6 lg:px-8">
    <!-- Header -->
    <div class="mb-8">
      <h1 class="text-3xl font-bold text-slate-800 mb-2">Sync Management</h1>
      <p class="text-slate-600">Manage contact synchronization with Google</p>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="card">
      <div class="card-body text-center py-12">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p class="text-slate-600">Loading sync information...</p>
      </div>
    </div>

    <!-- Main Content -->
    <div v-else class="space-y-6">
      <!-- OAuth Status Warning -->
      <div v-if="!oauthStatus?.authenticated" class="card border-yellow-200 bg-yellow-50">
        <div class="card-body">
          <div class="flex items-start gap-4">
            <div class="text-2xl">⚠️</div>
            <div class="flex-1">
              <h3 class="font-semibold text-yellow-800 mb-1">Not Authenticated</h3>
              <p class="text-yellow-700 text-sm mb-3">
                You need to authenticate with Google before you can sync contacts.
              </p>
              <router-link
                to="/oauth/setup"
                class="inline-flex items-center px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition-colors text-sm font-medium"
              >
                Go to OAuth Setup
              </router-link>
            </div>
          </div>
        </div>
      </div>

      <!-- Success Message -->
      <div v-if="successMessage" class="card border-green-200 bg-green-50">
        <div class="card-body">
          <div class="flex items-start justify-between gap-4">
            <div class="flex items-start gap-3">
              <div class="text-2xl">✅</div>
              <div>
                <h3 class="font-semibold text-green-800 mb-1">Success</h3>
                <p class="text-green-700 text-sm">{{ successMessage }}</p>
              </div>
            </div>
            <button
              @click="dismissSuccess"
              class="text-green-600 hover:text-green-800 transition-colors"
              aria-label="Dismiss success message"
            >
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      <!-- Error Message -->
      <div v-if="error" class="card border-red-200 bg-red-50">
        <div class="card-body">
          <div class="flex items-start justify-between gap-4">
            <div class="flex items-start gap-3">
              <div class="text-2xl">❌</div>
              <div>
                <h3 class="font-semibold text-red-800 mb-1">Error</h3>
                <p class="text-red-700 text-sm">{{ error }}</p>
              </div>
            </div>
            <button
              @click="dismissError"
              class="text-red-600 hover:text-red-800 transition-colors"
              aria-label="Dismiss error message"
            >
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      <!-- Current Status -->
      <div class="card">
        <div class="card-header">
          <h2 class="text-xl font-semibold text-slate-800">Current Status</h2>
        </div>
        <div class="card-body">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <!-- Status -->
            <div class="space-y-4">
              <div class="flex items-center gap-3">
                <span class="text-3xl">{{ statusIcon }}</span>
                <div>
                  <div class="text-sm text-slate-600">Status</div>
                  <div class="text-lg font-semibold text-slate-800">{{ statusText }}</div>
                </div>
              </div>
              
              <div>
                <div class="text-sm text-slate-600">Last Sync</div>
                <div class="text-lg font-medium text-slate-800">{{ lastSyncText }}</div>
                <div v-if="syncStatus?.last_sync_at" class="text-xs text-slate-500 mt-1">
                  {{ formatDate(syncStatus.last_sync_at) }}
                </div>
              </div>

              <div v-if="syncStatus?.error_message" class="p-3 bg-red-50 border border-red-200 rounded-lg">
                <div class="text-sm font-medium text-red-800 mb-1">Last Error</div>
                <div class="text-sm text-red-700">{{ syncStatus.error_message }}</div>
              </div>
            </div>

            <!-- Statistics -->
            <div class="space-y-4">
              <div>
                <div class="text-sm text-slate-600">Total Contacts</div>
                <div class="text-2xl font-bold text-slate-800">
                  {{ syncStatus?.total_contacts?.toLocaleString() || 0 }}
                </div>
              </div>

              <div>
                <div class="text-sm text-slate-600">Active Contacts</div>
                <div class="text-2xl font-bold text-slate-800">
                  {{ syncStatus?.contact_count?.toLocaleString() || 0 }}
                </div>
              </div>

              <div class="flex items-center gap-2">
                <div
                  :class="[
                    'w-2 h-2 rounded-full',
                    syncStatus?.has_sync_token ? 'bg-green-500' : 'bg-yellow-500'
                  ]"
                ></div>
                <div class="text-sm text-slate-600">
                  {{ syncStatus?.has_sync_token ? 'Incremental sync available' : 'Full sync required' }}
                </div>
              </div>
            </div>
          </div>

          <!-- Sync Buttons -->
          <div class="mt-6 pt-6 border-t border-slate-200">
            <div class="flex flex-wrap gap-3">
              <button
                @click="triggerAutoSync"
                :disabled="!canSync"
                class="btn btn-primary flex items-center gap-2"
              >
                <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Sync Now
              </button>

              <button
                @click="triggerIncrementalSync"
                :disabled="!canSync || !syncStatus?.has_sync_token"
                class="btn btn-secondary flex items-center gap-2"
              >
                <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Incremental Sync
              </button>

              <button
                @click="triggerFullSync"
                :disabled="!canSync"
                class="btn btn-outline flex items-center gap-2"
              >
                <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Full Sync
              </button>

              <button
                @click="loadData"
                :disabled="syncing"
                class="btn btn-outline flex items-center gap-2"
              >
                <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Refresh
              </button>
            </div>
            
            <div class="mt-3 text-sm text-slate-600">
              <p><strong>Sync Now:</strong> Automatically chooses between full and incremental sync</p>
              <p><strong>Incremental Sync:</strong> Only syncs changes since last sync (faster)</p>
              <p><strong>Full Sync:</strong> Re-syncs all contacts from Google (slower)</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Detailed Statistics -->
      <div v-if="syncStatistics" class="card">
        <div class="card-header">
          <h2 class="text-xl font-semibold text-slate-800">Detailed Statistics</h2>
        </div>
        <div class="card-body">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="stat-card">
              <div class="stat-value">{{ syncStatistics.contacts.total.toLocaleString() }}</div>
              <div class="stat-label">Total Contacts</div>
              <div class="text-xs text-slate-500 mt-1">
                {{ syncStatistics.contacts.active.toLocaleString() }} active,
                {{ syncStatistics.contacts.deleted.toLocaleString() }} deleted
              </div>
            </div>

            <div class="stat-card">
              <div class="stat-value">{{ syncStatistics.phone_numbers.toLocaleString() }}</div>
              <div class="stat-label">Phone Numbers</div>
            </div>

            <div class="stat-card">
              <div class="stat-value">{{ Object.keys(syncStatistics.sync_history).length }}</div>
              <div class="stat-label">Sync Records</div>
              <div class="text-xs text-slate-500 mt-1">
                <span v-for="(count, status) in syncStatistics.sync_history" :key="status" class="mr-2">
                  {{ status }}: {{ count }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Sync History -->
      <div v-if="syncHistory?.history.length" class="card">
        <div class="card-header">
          <h2 class="text-xl font-semibold text-slate-800">Sync History</h2>
        </div>
        <div class="card-body">
          <div class="space-y-3">
            <div
              v-for="entry in syncHistory.history"
              :key="entry.id"
              class="p-4 border border-slate-200 rounded-lg hover:border-slate-300 transition-colors"
            >
              <div class="flex items-start justify-between gap-4">
                <div class="flex-1">
                  <div class="flex items-center gap-2 mb-1">
                    <span
                      :class="[
                        'w-2 h-2 rounded-full',
                        entry.status === 'idle' ? 'bg-green-500' :
                        entry.status === 'error' ? 'bg-red-500' :
                        entry.status === 'syncing' ? 'bg-blue-500' :
                        'bg-gray-500'
                      ]"
                    ></span>
                    <span class="font-medium text-slate-800">{{ entry.status }}</span>
                    <span v-if="entry.has_sync_token" class="text-xs px-2 py-0.5 bg-green-100 text-green-700 rounded">
                      Token Available
                    </span>
                  </div>
                  
                  <div class="text-sm text-slate-600">
                    {{ formatDate(entry.last_sync_at) }}
                  </div>

                  <div v-if="entry.error_message" class="mt-2 text-sm text-red-700">
                    Error: {{ entry.error_message }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- No History -->
      <div v-else class="card">
        <div class="card-header">
          <h2 class="text-xl font-semibold text-slate-800">Sync History</h2>
        </div>
        <div class="card-body text-center py-12">
          <div class="text-slate-400 mb-2">📋</div>
          <p class="text-slate-600">No sync history available yet</p>
          <p class="text-sm text-slate-500 mt-1">Sync history will appear here after your first sync</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.stat-card {
  @apply p-4 bg-slate-50 rounded-lg;
}

.stat-value {
  @apply text-3xl font-bold text-slate-800;
}

.stat-label {
  @apply text-sm text-slate-600 mt-1;
}
</style>
