<script setup lang="ts">
/**
 * NotFoundView - 404 page.
 */
import { useRouter } from 'vue-router'

const router = useRouter()

const goHome = () => {
  router.push('/')
}

const goBack = () => {
  router.back()
}
</script>

<template>
  <div class="min-h-[calc(100vh-16rem)] flex items-center justify-center">
    <div class="text-center px-4">
      <!-- 404 illustration -->
      <div class="relative mb-8">
        <div class="text-9xl font-display font-bold text-slate-100 select-none">
          404
        </div>
        <div class="absolute inset-0 flex items-center justify-center">
          <div class="w-24 h-24 rounded-2xl bg-gradient-to-br from-brand-500 to-accent-600 flex items-center justify-center shadow-xl">
            <svg class="w-12 h-12 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        </div>
      </div>
      
      <!-- Text -->
      <h1 class="font-display text-3xl font-bold text-slate-900 mb-4">
        Page Not Found
      </h1>
      <p class="text-slate-600 max-w-md mx-auto mb-8">
        Sorry, the page you're looking for doesn't exist or has been moved to a different location.
      </p>
      
      <!-- Actions -->
      <div class="flex flex-col sm:flex-row items-center justify-center gap-4">
        <button class="btn-primary" @click="goHome">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
          </svg>
          Go Home
        </button>
        <button class="btn-secondary" @click="goBack">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Go Back
        </button>
      </div>
    </div>
  </div>
</template>

