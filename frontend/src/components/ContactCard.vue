<script setup lang="ts">
/**
 * ContactCard - Display a contact in grid or list view
 * Features:
 * - Grid and list layout modes
 * - Search result highlighting
 * - Primary phone/email display
 * - Hover effects
 */
import { computed } from 'vue'
import type { Contact } from '@/types/api'

interface Props {
  contact: Contact
  searchQuery?: string
  listMode?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  searchQuery: '',
  listMode: false
})

// =====================
// Computed Properties
// =====================

const primaryPhone = computed(() => {
  const phones = props.contact.phone_numbers || []
  const primary = phones.find(p => p.primary)
  return primary || phones[0]
})

const primaryEmail = computed(() => {
  const primary = props.contact.email_addresses?.find(e => e.primary)
  return primary || props.contact.email_addresses?.[0]
})

const initials = computed(() => {
  if (!props.contact.display_name) {
    return '?'
  }
  const parts = props.contact.display_name.split(' ')
  if (parts.length === 1) {
    return parts[0].substring(0, 2).toUpperCase()
  }
  const first = parts[0]?.[0] || ''
  const last = parts[parts.length - 1]?.[0] || ''
  return (first + last).toUpperCase() || '?'
})

const avatarColor = computed(() => {
  // Generate a consistent color based on the contact's name
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

// =====================
// Helper Functions
// =====================

function highlightMatch(text: string): string {
  if (!props.searchQuery || !text) return text
  
  const query = props.searchQuery.trim()
  if (!query) return text
  
  // HTML-escape the text first to prevent XSS
  const escapeHtml = (str: string) => str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
  
  const safeText = escapeHtml(text)
  const safeQuery = escapeHtml(query)
  
  // Escape special regex characters
  const escapedQuery = safeQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const regex = new RegExp(`(${escapedQuery})`, 'gi')
  
  return safeText.replace(regex, '<mark class="bg-yellow-200 px-0.5 rounded">$1</mark>')
}

function formatPhoneType(type: string): string {
  return type.charAt(0).toUpperCase() + type.slice(1).toLowerCase()
}
</script>

<template>
  <!-- Grid Mode -->
  <div
    v-if="!listMode"
    class="bg-white border border-slate-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
  >
    <!-- Avatar -->
    <div class="flex items-center gap-3 mb-3">
      <div :class="['w-12 h-12 rounded-full flex items-center justify-center text-white font-semibold', avatarColor]">
        {{ initials }}
      </div>
      <div class="flex-1 min-w-0">
        <h3
          class="font-semibold text-slate-900 truncate"
          v-html="highlightMatch(contact.display_name)"
        />
        <p v-if="contact.given_name || contact.family_name" class="text-xs text-slate-500 truncate">
          <span v-if="contact.given_name" v-html="highlightMatch(contact.given_name)" />
          <span v-if="contact.given_name && contact.family_name"> </span>
          <span v-if="contact.family_name" v-html="highlightMatch(contact.family_name)" />
        </p>
      </div>
    </div>

    <!-- Contact Info -->
    <div class="space-y-2">
      <!-- Primary Phone -->
      <div v-if="primaryPhone" class="flex items-center gap-2 text-sm">
        <svg class="h-4 w-4 text-slate-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
        </svg>
        <span class="text-slate-700 truncate" v-html="highlightMatch(primaryPhone.display_value)" />
        <span v-if="primaryPhone.type" class="text-xs text-slate-500">
          {{ formatPhoneType(primaryPhone.type) }}
        </span>
      </div>

      <!-- Primary Email -->
      <div v-if="primaryEmail" class="flex items-center gap-2 text-sm">
        <svg class="h-4 w-4 text-slate-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
        <span class="text-slate-700 truncate" v-html="highlightMatch(primaryEmail.value)" />
      </div>

      <!-- Additional Info Badge -->
      <div class="flex items-center gap-2 text-xs text-slate-500 mt-2 pt-2 border-t border-slate-100">
        <span v-if="contact.phone_numbers.length > 1">
          +{{ contact.phone_numbers.length - 1 }} more phone
        </span>
        <span v-if="contact.email_addresses && contact.email_addresses.length > 1">
          +{{ contact.email_addresses.length - 1 }} more email
        </span>
      </div>
    </div>
  </div>

  <!-- List Mode -->
  <div
    v-else
    class="bg-white border border-slate-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer flex items-center gap-4"
  >
    <!-- Avatar -->
    <div :class="['w-12 h-12 rounded-full flex items-center justify-center text-white font-semibold flex-shrink-0', avatarColor]">
      {{ initials }}
    </div>

    <!-- Contact Info -->
    <div class="flex-1 min-w-0 grid grid-cols-1 sm:grid-cols-3 gap-2">
      <!-- Name -->
      <div>
        <h3
          class="font-semibold text-slate-900 truncate"
          v-html="highlightMatch(contact.display_name)"
        />
        <p v-if="contact.given_name || contact.family_name" class="text-xs text-slate-500 truncate">
          <span v-if="contact.given_name" v-html="highlightMatch(contact.given_name)" />
          <span v-if="contact.given_name && contact.family_name"> </span>
          <span v-if="contact.family_name" v-html="highlightMatch(contact.family_name)" />
        </p>
      </div>

      <!-- Phone -->
      <div v-if="primaryPhone" class="flex items-center gap-2">
        <svg class="h-4 w-4 text-slate-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
        </svg>
        <span class="text-sm text-slate-700 truncate" v-html="highlightMatch(primaryPhone.display_value)" />
        <span v-if="contact.phone_numbers.length > 1" class="text-xs text-slate-500">
          +{{ contact.phone_numbers.length - 1 }}
        </span>
      </div>

      <!-- Email -->
      <div v-if="primaryEmail" class="flex items-center gap-2">
        <svg class="h-4 w-4 text-slate-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
        <span class="text-sm text-slate-700 truncate" v-html="highlightMatch(primaryEmail.value)" />
      </div>
    </div>
  </div>
</template>
