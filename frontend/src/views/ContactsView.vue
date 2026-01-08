<script setup lang="ts">
/**
 * ContactsView - Contact directory with integrated search
 * Features:
 * - Real-time search with debouncing
 * - Alphabetical filtering (A-Z, #)
 * - Grid/List view toggle
 * - Contact details modal
 * - Pagination
 * - Responsive design
 */
import { ref, computed, watch, onMounted } from 'vue'
import { api } from '@/api/client'
import type { Contact, SearchResult } from '@/types/api'
import ContactCard from '@/components/ContactCard.vue'
import ContactModal from '@/components/ContactModal.vue'

// =====================
// State Management
// =====================

const contacts = ref<Contact[]>([])
const searchResults = ref<SearchResult[]>([])
const isSearchMode = ref(false)
const searchQuery = ref('')
const selectedLetter = ref<string>('')
const isLoading = ref(false)
const error = ref<string | null>(null)
const selectedContact = ref<Contact | null>(null)
const showModal = ref(false)

// View preferences (persisted in localStorage)
const viewMode = ref<'grid' | 'list'>(
  (localStorage.getItem('contactsViewMode') as 'grid' | 'list') || 'grid'
)
const sortOrder = ref<'name' | 'recent'>(
  (localStorage.getItem('contactsSortOrder') as 'name' | 'recent') || 'name'
)

// Pagination
const currentPage = ref(1)
const pageSize = 30
const totalContacts = ref(0)
const hasMore = ref(false)

// Debounce timer
let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null

// =====================
// Computed Properties
// =====================

const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ#'.split('')

const displayedContacts = computed(() => {
  if (isSearchMode.value) {
    // In search mode, show search results (converted to Contact type)
    return searchResults.value.map(r => r.contact)
  }
  return contacts.value
})

const totalPages = computed(() => {
  return Math.ceil(totalContacts.value / pageSize)
})

const paginationInfo = computed(() => {
  const start = (currentPage.value - 1) * pageSize + 1
  const end = Math.min(currentPage.value * pageSize, totalContacts.value)
  return { start, end, total: totalContacts.value }
})

const emptyStateMessage = computed(() => {
  if (isSearchMode.value) {
    return `No contacts found for "${searchQuery.value}"`
  }
  if (selectedLetter.value) {
    return `No contacts starting with "${selectedLetter.value}"`
  }
  return 'No contacts available. Sync your Google Contacts to get started.'
})

// =====================
// API Methods
// =====================

async function loadContacts() {
  isLoading.value = true
  error.value = null
  
  try {
    const offset = (currentPage.value - 1) * pageSize
    const params: any = {
      limit: pageSize,
      offset,
      sort: sortOrder.value
    }
    
    if (selectedLetter.value && selectedLetter.value !== '') {
      params.group = selectedLetter.value
    }
    
    const response = await api.getContacts(params)
    contacts.value = response.contacts
    totalContacts.value = response.total
    hasMore.value = response.has_more
  } catch (err: any) {
    error.value = err.response?.data?.detail || 'Failed to load contacts'
    console.error('Error loading contacts:', err)
  } finally {
    isLoading.value = false
  }
}

async function performSearch(query: string) {
  if (!query.trim()) {
    // Empty search, exit search mode
    isSearchMode.value = false
    await loadContacts()
    return
  }
  
  isLoading.value = true
  error.value = null
  isSearchMode.value = true
  
  try {
    const response = await api.search(query, 100) // Get up to 100 search results
    searchResults.value = response.results
  } catch (err: any) {
    error.value = err.response?.data?.detail || 'Search failed'
    console.error('Error searching contacts:', err)
  } finally {
    isLoading.value = false
  }
}

// =====================
// Event Handlers
// =====================

function handleSearchInput(event: Event) {
  const target = event.target as HTMLInputElement
  searchQuery.value = target.value
  
  // Clear existing timer
  if (searchDebounceTimer) {
    clearTimeout(searchDebounceTimer)
  }
  
  // Debounce search by 300ms
  searchDebounceTimer = setTimeout(() => {
    performSearch(searchQuery.value)
  }, 300)
}

function clearSearch() {
  searchQuery.value = ''
  isSearchMode.value = false
  selectedLetter.value = ''
  currentPage.value = 1
  loadContacts()
}

function selectLetter(letter: string) {
  if (isSearchMode.value) {
    // Clear search first
    searchQuery.value = ''
    isSearchMode.value = false
  }
  
  selectedLetter.value = letter === selectedLetter.value ? '' : letter
  currentPage.value = 1
  loadContacts()
}

function toggleViewMode() {
  viewMode.value = viewMode.value === 'grid' ? 'list' : 'grid'
  localStorage.setItem('contactsViewMode', viewMode.value)
}

function changeSortOrder(order: 'name' | 'recent') {
  sortOrder.value = order
  localStorage.setItem('contactsSortOrder', order)
  currentPage.value = 1
  if (!isSearchMode.value) {
    loadContacts()
  }
}

function goToPage(page: number) {
  if (page < 1 || page > totalPages.value || isSearchMode.value) return
  currentPage.value = page
  loadContacts()
}

function openContactModal(contact: Contact) {
  selectedContact.value = contact
  showModal.value = true
}

function closeContactModal() {
  showModal.value = false
  setTimeout(() => {
    selectedContact.value = null
  }, 300) // Wait for modal animation
}

// =====================
// Lifecycle
// =====================

onMounted(() => {
  loadContacts()
})

// Watch for view mode changes in other tabs
watch(viewMode, () => {
  // View mode already updated and saved
})
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
    <!-- Header -->
    <div class="mb-8">
      <h1 class="text-3xl font-bold text-slate-900 mb-2">Contacts Directory</h1>
      <p class="text-slate-600">Browse and search your synced Google Contacts</p>
    </div>

    <!-- Search Bar -->
    <div class="mb-6">
      <div class="relative">
        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <svg class="h-5 w-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
        <input
          type="text"
          :value="searchQuery"
          @input="handleSearchInput"
          placeholder="Search contacts by name or phone number..."
          class="block w-full pl-10 pr-12 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        <button
          v-if="searchQuery"
          @click="clearSearch"
          class="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600"
        >
          <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Controls Bar -->
    <div class="mb-6 flex flex-wrap items-center justify-between gap-4">
      <!-- Alphabetical Filter (hidden in search mode) -->
      <div v-if="!isSearchMode" class="flex flex-wrap gap-1">
        <button
          v-for="letter in alphabet"
          :key="letter"
          @click="selectLetter(letter)"
          :class="[
            'px-2 py-1 text-sm font-medium rounded transition-colors',
            selectedLetter === letter
              ? 'bg-blue-600 text-white'
              : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
          ]"
        >
          {{ letter }}
        </button>
      </div>
      <div v-else class="text-sm text-slate-600">
        Search mode: {{ searchResults.length }} result(s)
      </div>

      <!-- Right Controls -->
      <div class="flex items-center gap-3">
        <!-- Sort Order -->
        <div v-if="!isSearchMode" class="flex items-center gap-2">
          <label class="text-sm text-slate-600">Sort:</label>
          <select
            :value="sortOrder"
            @change="(e) => changeSortOrder((e.target as HTMLSelectElement).value as 'name' | 'recent')"
            class="text-sm border border-slate-300 rounded px-2 py-1 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="name">Name</option>
            <option value="recent">Recently Updated</option>
          </select>
        </div>

        <!-- View Toggle -->
        <button
          @click="toggleViewMode"
          class="p-2 rounded hover:bg-slate-100 transition-colors"
          :title="viewMode === 'grid' ? 'Switch to list view' : 'Switch to grid view'"
        >
          <svg v-if="viewMode === 'grid'" class="h-5 w-5 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
          <svg v-else class="h-5 w-5 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="text-center py-12">
      <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      <p class="mt-4 text-slate-600">Loading contacts...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
      <div class="flex items-center gap-2">
        <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span>{{ error }}</span>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else-if="displayedContacts.length === 0" class="text-center py-12">
      <div class="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mx-auto mb-4">
        <svg class="w-8 h-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
        </svg>
      </div>
      <h3 class="text-lg font-semibold text-slate-700 mb-2">No Contacts Found</h3>
      <p class="text-slate-500 text-sm max-w-md mx-auto">{{ emptyStateMessage }}</p>
    </div>

    <!-- Contacts Grid/List -->
    <div v-else>
      <!-- Grid View -->
      <div
        v-if="viewMode === 'grid'"
        class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
      >
        <ContactCard
          v-for="contact in displayedContacts"
          :key="contact.id"
          :contact="contact"
          :search-query="isSearchMode ? searchQuery : ''"
          @click="openContactModal(contact)"
        />
      </div>

      <!-- List View -->
      <div v-else class="space-y-2">
        <ContactCard
          v-for="contact in displayedContacts"
          :key="contact.id"
          :contact="contact"
          :search-query="isSearchMode ? searchQuery : ''"
          :list-mode="true"
          @click="openContactModal(contact)"
        />
      </div>

      <!-- Pagination (only in browse mode) -->
      <div v-if="!isSearchMode && totalPages > 1" class="mt-8 flex items-center justify-between">
        <div class="text-sm text-slate-600">
          Showing {{ paginationInfo.start }} - {{ paginationInfo.end }} of {{ paginationInfo.total }}
        </div>
        <div class="flex items-center gap-2">
          <button
            @click="goToPage(currentPage - 1)"
            :disabled="currentPage === 1"
            :class="[
              'px-3 py-1 rounded border transition-colors',
              currentPage === 1
                ? 'border-slate-200 text-slate-400 cursor-not-allowed'
                : 'border-slate-300 text-slate-700 hover:bg-slate-50'
            ]"
          >
            Previous
          </button>
          <span class="text-sm text-slate-600">
            Page {{ currentPage }} of {{ totalPages }}
          </span>
          <button
            @click="goToPage(currentPage + 1)"
            :disabled="currentPage === totalPages"
            :class="[
              'px-3 py-1 rounded border transition-colors',
              currentPage === totalPages
                ? 'border-slate-200 text-slate-400 cursor-not-allowed'
                : 'border-slate-300 text-slate-700 hover:bg-slate-50'
            ]"
          >
            Next
          </button>
        </div>
      </div>
    </div>

    <!-- Contact Detail Modal -->
    <ContactModal
      v-if="showModal && selectedContact"
      :contact="selectedContact"
      @close="closeContactModal"
    />
  </div>
</template>
