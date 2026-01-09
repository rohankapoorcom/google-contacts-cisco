<script setup lang="ts">
/**
 * HomeView - Dashboard/landing page.
 * Shows system status, quick actions, and feature overview.
 */
import { ref, onMounted } from 'vue'
import { api } from '@/api/client'
import type { OAuthStatus } from '@/types/api'

interface SystemStatus {
  total_contacts: number
  last_sync?: string
  oauth_configured: boolean
  loading: boolean
  error?: string
}

const status = ref<SystemStatus>({
  total_contacts: 0,
  last_sync: undefined,
  oauth_configured: false,
  loading: true,
  error: undefined,
})

// Features data
const features = [
  {
    icon: 'phone',
    title: 'Cisco Phone Support',
    description: 'Access your contacts directly from Cisco IP Phone directory with optimized XML format.',
    gradient: 'from-emerald-500 to-teal-600',
  },
  {
    icon: 'sync',
    title: 'Auto Sync',
    description: 'Automatic synchronization with Google Contacts keeps your directory always up-to-date.',
    gradient: 'from-brand-500 to-brand-700',
  },
  {
    icon: 'search',
    title: 'Fast Search',
    description: 'Quick full-text search by name or phone number with instant results.',
    gradient: 'from-accent-500 to-pink-600',
  },
]

onMounted(async () => {
  // Fetch sync status and OAuth status in parallel
  const [syncStatusResult, oauthStatus] = await Promise.allSettled([
    api.getSyncStatus(),
    api.getOAuthStatus(),
  ])

  // Handle sync status
  if (syncStatusResult.status === 'fulfilled') {
    const info = syncStatusResult.value
    status.value.total_contacts = info.total_contacts
    status.value.last_sync = info.last_sync_at
  } else {
    console.error('Failed to load sync status:', syncStatusResult.reason)
    status.value.error = 'Failed to load system status'
  }

  // Handle OAuth status
  if (oauthStatus.status === 'fulfilled') {
    const auth = oauthStatus.value as OAuthStatus
    status.value.oauth_configured = auth.authenticated
  } else {
    console.error('Failed to load OAuth status:', oauthStatus.reason)
    status.value.error = 'Failed to load system status'
  }

  status.value.loading = false
})

// Format date for display
const formatDate = (dateStr?: string): string => {
  if (!dateStr) return 'Never'
  try {
    return new Date(dateStr).toLocaleString()
  } catch {
    return 'Unknown'
  }
}

// Reload page
const reloadPage = () => {
  window.location.reload()
}
</script>

<template>
  <div class="min-h-[calc(100vh-8rem)]">
    <!-- Hero Section -->
    <section class="relative overflow-hidden">
      <!-- Background decoration -->
      <div class="absolute inset-0 -z-10">
        <div class="absolute top-0 right-0 w-96 h-96 bg-brand-500/10 rounded-full blur-3xl transform translate-x-1/2 -translate-y-1/2"></div>
        <div class="absolute bottom-0 left-0 w-72 h-72 bg-accent-500/10 rounded-full blur-3xl transform -translate-x-1/2 translate-y-1/2"></div>
      </div>

      <div class="max-w-7xl mx-auto px-4 py-16 sm:px-6 lg:px-8 lg:py-24">
        <div class="text-center max-w-3xl mx-auto">
          <!-- Badge -->
          <div class="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-brand-100 text-brand-700 text-sm font-medium mb-6 animate-fade-in">
            <span class="w-2 h-2 rounded-full bg-brand-500 animate-pulse"></span>
            Sync with Google Contacts
          </div>
          
          <!-- Title -->
          <h1 class="font-display text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-slate-900 animate-slide-up">
            Google Contacts
            <span class="text-gradient"> Directory</span>
          </h1>
          
          <!-- Subtitle -->
          <p class="mt-6 text-lg sm:text-xl text-slate-600 max-w-2xl mx-auto animate-slide-up" style="animation-delay: 100ms;">
            Access your Google Contacts on Cisco IP Phones with automatic synchronization and a modern web interface.
          </p>
          
          <!-- CTA Buttons -->
          <div class="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4 animate-slide-up" style="animation-delay: 200ms;">
            <router-link to="/contacts" class="btn-primary px-6 py-3">
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
              View Contacts
            </router-link>
            <router-link to="/sync" class="btn-secondary px-6 py-3">
              Sync Now
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </router-link>
          </div>
        </div>
      </div>
    </section>

    <!-- Features Section -->
    <section class="py-16">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-8">
          <div
            v-for="(feature, index) in features"
            :key="feature.title"
            class="card p-6 hover:-translate-y-1 transition-transform duration-300 animate-slide-up"
            :style="{ animationDelay: `${index * 100}ms` }"
          >
            <!-- Icon -->
            <div 
              :class="[
                'w-12 h-12 rounded-xl flex items-center justify-center mb-4',
                `bg-gradient-to-br ${feature.gradient}`,
                'shadow-lg'
              ]"
            >
              <!-- Phone icon -->
              <svg v-if="feature.icon === 'phone'" class="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
              </svg>
              <!-- Sync icon -->
              <svg v-else-if="feature.icon === 'sync'" class="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
              </svg>
              <!-- Search icon -->
              <svg v-else-if="feature.icon === 'search'" class="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
              </svg>
            </div>
            
            <!-- Content -->
            <h3 class="text-lg font-semibold text-slate-900 mb-2">
              {{ feature.title }}
            </h3>
            <p class="text-slate-600 text-sm leading-relaxed">
              {{ feature.description }}
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- System Status Section -->
    <section class="py-16">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="card max-w-2xl mx-auto">
          <div class="card-header">
            <h2 class="section-title flex items-center gap-3">
              <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-slate-500 to-slate-700 flex items-center justify-center">
                <svg class="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              System Status
            </h2>
          </div>
          
          <div class="card-body">
            <!-- Loading state -->
            <div v-if="status.loading" class="flex justify-center py-8">
              <div class="spinner spinner-lg"></div>
            </div>
            
            <!-- Error state -->
            <div v-else-if="status.error" class="text-center py-8">
              <div class="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center mx-auto mb-3">
                <svg class="w-6 h-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <p class="text-red-600 font-medium">{{ status.error }}</p>
              <button class="btn-ghost mt-4" @click="reloadPage">
                Retry
              </button>
            </div>
            
            <!-- Status content -->
            <div v-else class="space-y-4">
              <!-- Total Contacts -->
              <div class="flex items-center justify-between p-4 rounded-xl bg-slate-50">
                <div class="flex items-center gap-3">
                  <div class="w-10 h-10 rounded-lg bg-brand-100 flex items-center justify-center">
                    <svg class="w-5 h-5 text-brand-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                    </svg>
                  </div>
                  <span class="text-slate-600">Total Contacts</span>
                </div>
                <span class="text-2xl font-bold text-slate-900">{{ status.total_contacts.toLocaleString() }}</span>
              </div>
              
              <!-- Last Sync -->
              <div class="flex items-center justify-between p-4 rounded-xl bg-slate-50">
                <div class="flex items-center gap-3">
                  <div class="w-10 h-10 rounded-lg bg-emerald-100 flex items-center justify-center">
                    <svg class="w-5 h-5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <span class="text-slate-600">Last Sync</span>
                </div>
                <span class="text-sm font-medium text-slate-900">{{ formatDate(status.last_sync) }}</span>
              </div>
              
              <!-- OAuth Status -->
              <div class="flex items-center justify-between p-4 rounded-xl bg-slate-50">
                <div class="flex items-center gap-3">
                  <div :class="[
                    'w-10 h-10 rounded-lg flex items-center justify-center',
                    status.oauth_configured ? 'bg-emerald-100' : 'bg-amber-100'
                  ]">
                    <svg v-if="status.oauth_configured" class="w-5 h-5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <svg v-else class="w-5 h-5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                  </div>
                  <span class="text-slate-600">OAuth Status</span>
                </div>
                <div class="flex items-center gap-2">
                  <span :class="[
                    'badge',
                    status.oauth_configured ? 'badge-success' : 'badge-warning'
                  ]">
                    {{ status.oauth_configured ? 'Configured' : 'Not Configured' }}
                  </span>
                  <router-link
                    v-if="!status.oauth_configured"
                    to="/oauth/setup"
                    class="btn-ghost text-xs py-1 px-2"
                  >
                    Setup
                  </router-link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

