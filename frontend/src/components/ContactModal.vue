<script setup lang="ts">
/**
 * ContactModal - Display full contact details in a modal
 * Features:
 * - Shows all phone numbers and emails
 * - Click outside or ESC to close
 * - Smooth animations
 * - Copy to clipboard functionality
 */
import { onMounted, onUnmounted, computed } from 'vue'
import type { Contact } from '@/types/api'

interface Props {
  contact: Contact
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

// =====================
// Computed Properties
// =====================

const initials = computed(() => {
  if (!props.contact.display_name) {
    return '?'
  }
  const parts = props.contact.display_name.split(' ')
  if (parts.length === 1 && parts[0]) {
    return parts[0].substring(0, 2).toUpperCase()
  }
  const first = parts[0]?.[0] || ''
  const last = parts[parts.length - 1]?.[0] || ''
  return (first + last).toUpperCase() || '?'
})

const avatarColor = computed(() => {
  const colors = [
    'bg-blue-500',
    'bg-green-500',
    'bg-purple-500',
    'bg-pink-500',
    'bg-indigo-500',
    'bg-yellow-500',
    'bg-red-500',
    'bg-teal-500'
  ]
  const hash = props.contact.id.split('').reduce((acc, char) => {
    return char.charCodeAt(0) + ((acc << 5) - acc)
  }, 0)
  return colors[Math.abs(hash) % colors.length]
})

const formattedDate = computed(() => {
  if (!props.contact.updated_at) return null
  try {
    const date = new Date(props.contact.updated_at)
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return null
  }
})

// =====================
// Event Handlers
// =====================

function handleEscape(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    emit('close')
  }
}

function handleBackdropClick(event: MouseEvent) {
  // Only close if clicking the backdrop, not the modal content
  if (event.target === event.currentTarget) {
    emit('close')
  }
}

async function copyToClipboard(text: string, type: string) {
  try {
    await navigator.clipboard.writeText(text)
    // Could show a toast notification here
    console.log(`${type} copied to clipboard`)
  } catch (err) {
    console.error('Failed to copy:', err)
  }
}

function formatPhoneType(type: string): string {
  return type.charAt(0).toUpperCase() + type.slice(1).toLowerCase()
}

function formatEmailType(type: string): string {
  return type.charAt(0).toUpperCase() + type.slice(1).toLowerCase()
}

// =====================
// Lifecycle
// =====================

onMounted(() => {
  document.addEventListener('keydown', handleEscape)
  // Prevent body scroll when modal is open
  document.body.style.overflow = 'hidden'
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleEscape)
  // Restore body scroll
  document.body.style.overflow = ''
})
</script>

<template>
  <!-- Modal Backdrop -->
  <div
    class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4 animate-fade-in"
    @click="handleBackdropClick"
  >
    <!-- Modal Content -->
    <div
      class="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto animate-scale-in"
      @click.stop
    >
      <!-- Header -->
      <div class="sticky top-0 bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
        <h2 class="text-xl font-semibold text-slate-900">Contact Details</h2>
        <button
          @click="emit('close')"
          class="p-2 rounded-full hover:bg-slate-100 transition-colors"
          aria-label="Close modal"
        >
          <svg class="w-5 h-5 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Body -->
      <div class="p-6">
        <!-- Contact Header -->
        <div class="flex items-center gap-4 mb-6">
          <div :class="['w-20 h-20 rounded-full flex items-center justify-center text-white text-2xl font-semibold flex-shrink-0', avatarColor]">
            {{ initials }}
          </div>
          <div class="flex-1 min-w-0">
            <h3 class="text-2xl font-bold text-slate-900 mb-1">
              {{ contact.display_name }}
            </h3>
            <p v-if="contact.given_name || contact.family_name" class="text-slate-600">
              <span v-if="contact.given_name">{{ contact.given_name }}</span>
              <span v-if="contact.given_name && contact.family_name"> </span>
              <span v-if="contact.family_name">{{ contact.family_name }}</span>
            </p>
          </div>
        </div>

        <!-- Phone Numbers -->
        <div v-if="contact.phone_numbers.length > 0" class="mb-6">
          <h4 class="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
            <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
            </svg>
            Phone Numbers
          </h4>
          <div class="space-y-2">
            <div
              v-for="phone in contact.phone_numbers"
              :key="phone.id"
              class="flex items-center justify-between p-3 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors group"
            >
              <div class="flex-1">
                <p class="font-medium text-slate-900">{{ phone.display_value }}</p>
                <p class="text-xs text-slate-500 mt-0.5">
                  {{ formatPhoneType(phone.type) }}
                  <span v-if="phone.primary" class="ml-2 px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-medium">
                    Primary
                  </span>
                </p>
              </div>
              <button
                @click="copyToClipboard(phone.value, 'Phone number')"
                class="p-2 rounded hover:bg-white transition-colors opacity-0 group-hover:opacity-100"
                title="Copy to clipboard"
              >
                <svg class="w-4 h-4 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <!-- Email Addresses -->
        <div v-if="contact.email_addresses && contact.email_addresses.length > 0" class="mb-6">
          <h4 class="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
            <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            Email Addresses
          </h4>
          <div class="space-y-2">
            <div
              v-for="email in contact.email_addresses"
              :key="email.id"
              class="flex items-center justify-between p-3 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors group"
            >
              <div class="flex-1 min-w-0">
                <p class="font-medium text-slate-900 truncate">{{ email.value }}</p>
                <p class="text-xs text-slate-500 mt-0.5">
                  {{ formatEmailType(email.type) }}
                  <span v-if="email.primary" class="ml-2 px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-medium">
                    Primary
                  </span>
                </p>
              </div>
              <button
                @click="copyToClipboard(email.value, 'Email address')"
                class="p-2 rounded hover:bg-white transition-colors opacity-0 group-hover:opacity-100 flex-shrink-0"
                title="Copy to clipboard"
              >
                <svg class="w-4 h-4 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <!-- Metadata -->
        <div class="pt-4 border-t border-slate-200">
          <div class="flex items-center justify-between text-xs text-slate-500">
            <span>Contact ID: {{ contact.id }}</span>
            <span v-if="formattedDate">Last updated: {{ formattedDate }}</span>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="sticky bottom-0 bg-slate-50 border-t border-slate-200 px-6 py-4 flex justify-end">
        <button
          @click="emit('close')"
          class="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-900 font-medium rounded-lg transition-colors"
        >
          Close
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
@keyframes fade-in {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes scale-in {
  from {
    transform: scale(0.95);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}

.animate-fade-in {
  animation: fade-in 0.2s ease-out;
}

.animate-scale-in {
  animation: scale-in 0.2s ease-out;
}
</style>
