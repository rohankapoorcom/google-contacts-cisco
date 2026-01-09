<script setup lang="ts">
/**
 * OAuthSetupView - OAuth configuration wizard.
 * Provides interface for connecting/disconnecting Google account.
 */
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/api/client'
import type { OAuthStatus, ApiError } from '@/types/api'
import type { AxiosError } from 'axios'

// Reactive state
const oauthStatus = ref<OAuthStatus | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const actionLoading = ref(false)
const showDisconnectConfirm = ref(false)

// Vue Router
const route = useRoute()

// Computed properties
const isConnected = computed(() => oauthStatus.value?.authenticated ?? false)
const hasValidCredentials = computed(() => oauthStatus.value?.credentials_valid ?? false)
const isExpired = computed(() => oauthStatus.value?.credentials_expired ?? false)
const hasRefreshToken = computed(() => oauthStatus.value?.has_refresh_token ?? false)
const scopes = computed(() => oauthStatus.value?.scopes ?? [])

/**
 * Load OAuth status from API
 */
async function loadOAuthStatus() {
  loading.value = true
  error.value = null

  try {
    oauthStatus.value = await api.getOAuthStatus()
  } catch (err) {
    const axiosError = err as AxiosError<ApiError>
    error.value = axiosError.response?.data?.detail || 'Failed to load OAuth status'
    console.error('Error loading OAuth status:', err)
  } finally {
    loading.value = false
  }
}

/**
 * Start OAuth flow by getting auth URL and redirecting
 */
async function connectGoogle() {
  actionLoading.value = true
  error.value = null

  try {
    const response = await api.getOAuthUrl()
    // Redirect to Google OAuth consent screen
    window.location.href = response.auth_url
  } catch (err) {
    const axiosError = err as AxiosError<ApiError>
    error.value = axiosError.response?.data?.detail || 'Failed to start OAuth flow'
    console.error('Error starting OAuth:', err)
    actionLoading.value = false
  }
}

/**
 * Refresh OAuth token
 */
async function refreshToken() {
  actionLoading.value = true
  error.value = null

  try {
    const response = await api.refreshToken()
    // Reload status after refresh
    await loadOAuthStatus()
    console.log('Token refreshed:', response.message)
  } catch (err) {
    const axiosError = err as AxiosError<ApiError>
    error.value = axiosError.response?.data?.detail || 'Failed to refresh token'
    console.error('Error refreshing token:', err)
  } finally {
    actionLoading.value = false
  }
}

/**
 * Disconnect from Google (revoke credentials)
 */
async function disconnect() {
  actionLoading.value = true
  error.value = null

  try {
    await api.disconnect()
    // Reload status after disconnect
    await loadOAuthStatus()
    showDisconnectConfirm.value = false
  } catch (err) {
    const axiosError = err as AxiosError<ApiError>
    error.value = axiosError.response?.data?.detail || 'Failed to disconnect'
    console.error('Error disconnecting:', err)
  } finally {
    actionLoading.value = false
  }
}

// Lifecycle hooks
onMounted(async () => {
  // Handle OAuth callback query parameters
  const errorParam = route.query.error as string | undefined

  if (errorParam) {
    error.value = `OAuth error: ${errorParam}`
  }

  // Load OAuth status (only once, whether callback or normal page load)
  await loadOAuthStatus()
})
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 py-12 sm:px-6 lg:px-8">
    <div class="card max-w-3xl mx-auto">
      <!-- Header -->
      <div class="card-header">
        <div class="flex items-center gap-3">
          <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
            <svg class="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
            </svg>
          </div>
          <div>
            <h1 class="section-title mb-0">OAuth Setup</h1>
            <p class="text-sm text-slate-500">Connect your Google account to sync contacts</p>
          </div>
        </div>
      </div>

      <div class="card-body space-y-6">
        <!-- Loading State -->
        <div v-if="loading" class="text-center py-12">
          <div class="inline-block w-8 h-8 border-4 border-slate-200 border-t-blue-500 rounded-full animate-spin"></div>
          <p class="text-slate-500 mt-4">Loading OAuth status...</p>
        </div>

        <!-- Error Message -->
        <div v-if="error" class="alert alert-error">
          <svg class="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <p class="font-semibold">Error</p>
            <p class="text-sm">{{ error }}</p>
          </div>
          <button
            @click="error = null"
            class="ml-auto text-red-600 hover:text-red-700"
          >
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Connected Status -->
        <div v-if="!loading && isConnected" class="space-y-6">
          <!-- Status Card -->
          <div class="bg-green-50 border border-green-200 rounded-xl p-6">
            <div class="flex items-start gap-4">
              <div class="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0">
                <svg class="w-6 h-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div class="flex-1">
                <h3 class="text-lg font-semibold text-green-900 mb-1">
                  Connected to Google
                </h3>
                <p class="text-sm text-green-700">
                  Your Google account is connected and ready to sync contacts.
                </p>
              </div>
            </div>

            <!-- Credentials Status -->
            <div class="mt-4 pt-4 border-t border-green-200 space-y-2">
              <div class="flex items-center justify-between text-sm">
                <span class="text-green-700 font-medium">Credentials Status:</span>
                <span v-if="hasValidCredentials && !isExpired" class="inline-flex items-center gap-1 text-green-600">
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                  Valid
                </span>
                <span v-else-if="isExpired" class="inline-flex items-center gap-1 text-amber-600">
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Expired
                </span>
                <span v-else class="inline-flex items-center gap-1 text-red-600">
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  Invalid
                </span>
              </div>

              <div class="flex items-center justify-between text-sm">
                <span class="text-green-700 font-medium">Refresh Token:</span>
                <span class="text-green-600">
                  {{ hasRefreshToken ? 'Available' : 'Not Available' }}
                </span>
              </div>

              <div class="flex items-start justify-between text-sm">
                <span class="text-green-700 font-medium">Scopes:</span>
                <div class="text-right text-green-600 max-w-xs">
                  <span v-if="scopes.length === 0" class="text-green-500 italic">None</span>
                  <div v-else class="space-y-1">
                    <div v-for="scope in scopes" :key="scope" class="text-xs">
                      {{ scope }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex flex-wrap gap-3">
            <button
              @click="refreshToken"
              :disabled="actionLoading || !hasRefreshToken"
              class="btn btn-secondary"
            >
              <svg v-if="!actionLoading" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              <div v-else class="w-4 h-4 border-2 border-slate-300 border-t-white rounded-full animate-spin"></div>
              Refresh Token
            </button>

            <button
              @click="showDisconnectConfirm = true"
              :disabled="actionLoading"
              class="btn bg-red-50 text-red-600 hover:bg-red-100"
            >
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
              </svg>
              Disconnect
            </button>
          </div>
        </div>

        <!-- Not Connected -->
        <div v-if="!loading && !isConnected" class="space-y-6">
          <!-- Instructions -->
          <div class="bg-blue-50 border border-blue-200 rounded-xl p-6">
            <h3 class="text-lg font-semibold text-blue-900 mb-3">
              Setup Instructions
            </h3>
            <ol class="space-y-2 text-sm text-blue-700">
              <li class="flex gap-2">
                <span class="font-semibold">1.</span>
                <span>Click the "Connect Google Account" button below</span>
              </li>
              <li class="flex gap-2">
                <span class="font-semibold">2.</span>
                <span>Sign in to your Google account</span>
              </li>
              <li class="flex gap-2">
                <span class="font-semibold">3.</span>
                <span>Grant permission to access your contacts</span>
              </li>
              <li class="flex gap-2">
                <span class="font-semibold">4.</span>
                <span>You'll be redirected back to complete setup</span>
              </li>
            </ol>
          </div>

          <!-- Required Permissions -->
          <div class="space-y-2">
            <h4 class="text-sm font-semibold text-slate-700">Required Permissions:</h4>
            <ul class="space-y-1 text-sm text-slate-600">
              <li class="flex items-center gap-2">
                <svg class="w-4 h-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                </svg>
                Read your contacts
              </li>
              <li class="flex items-center gap-2">
                <svg class="w-4 h-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                </svg>
                Maintain access to data you have given it access to
              </li>
            </ul>
          </div>

          <!-- Connect Button -->
          <button
            @click="connectGoogle"
            :disabled="actionLoading"
            class="btn btn-primary w-full sm:w-auto"
          >
            <svg v-if="!actionLoading" class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            <div v-else class="w-5 h-5 border-3 border-white border-t-transparent rounded-full animate-spin"></div>
            Connect Google Account
          </button>
        </div>
      </div>
    </div>

    <!-- Disconnect Confirmation Dialog -->
    <div
      v-if="showDisconnectConfirm"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
      @click.self="showDisconnectConfirm = false"
      @keydown.escape="showDisconnectConfirm = false"
    >
      <div
        class="bg-white rounded-xl shadow-2xl max-w-md w-full p-6"
        role="dialog"
        aria-modal="true"
        aria-labelledby="disconnect-dialog-title"
      >
        <h3 id="disconnect-dialog-title" class="text-xl font-semibold text-slate-800 mb-3">
          Disconnect from Google?
        </h3>
        <p class="text-slate-600 mb-6">
          This will revoke access to your Google contacts and delete stored credentials.
          You'll need to reconnect to sync contacts again.
        </p>
        <div class="flex gap-3 justify-end">
          <button
            @click="showDisconnectConfirm = false"
            :disabled="actionLoading"
            class="btn btn-secondary"
          >
            Cancel
          </button>
          <button
            @click="disconnect"
            :disabled="actionLoading"
            class="btn bg-red-600 text-white hover:bg-red-700"
          >
            <div v-if="actionLoading" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            <span v-else>Disconnect</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.alert {
  @apply flex items-start gap-3 p-4 rounded-xl border;
}

.alert-error {
  @apply bg-red-50 border-red-200 text-red-800;
}
</style>
