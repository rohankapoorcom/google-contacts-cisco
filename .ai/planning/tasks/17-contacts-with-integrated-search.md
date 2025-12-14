# Task 6.3: Contacts Directory with Integrated Search (Vue 3 + TypeScript)

## Overview

Create a comprehensive Vue 3 contact management interface with real-time integrated search, alphabetical filtering, grid/list views, and contact details modal. This combines traditional directory browsing with powerful search capabilities in a single, cohesive interface.

## Priority

**P1 (High)** - Required for MVP

## Dependencies

- Task 1.2: Database Setup
- Task 2.1: Contact Data Models
- Task 5.3: Search API Endpoints
- Task 6.1: Frontend Framework Setup (Vue 3 + Vite + TypeScript)

## Objectives

1. Create contacts list page with real-time search integrated
2. Display contacts in grid/list view toggle
3. Show contact details in modal
4. Implement alphabetical filtering (A-Z, #)
5. Add sorting (by name, recently updated)
6. Integrate real-time search with debouncing
7. Add pagination for large contact lists
8. Make fully responsive (mobile/tablet/desktop)
9. Type-safe with full TypeScript coverage
10. Test with various data sizes (1-10,000 contacts)

## Technical Context

### Integrated Search Architecture
- **Single Page**: One `/contacts` route with search integrated
- **Search Bar**: Prominent search input at top
- **Dual Mode**: 
  - **Browse Mode**: Alphabetical filtering, pagination (default)
  - **Search Mode**: Real-time search results (when typing)
- **Smooth Transition**: Seamlessly switch between modes

### UI/UX Design
- **Search First**: Large search bar is the primary interaction
- **Filter Pills**: Alphabetical buttons below search
- **View Toggle**: Grid (cards) or List (table) views
- **Modal**: Quick-view contact details without navigation
- **Responsive**: Stack on mobile, 2-col tablet, 3-col desktop

### Performance
- **Debounced Search**: 300ms delay prevents excessive API calls
- **Pagination**: Handle 100+ contacts efficiently
- **Lazy Loading**: Contact details loaded on-demand
- **Client Caching**: Cache search results briefly

## Acceptance Criteria

- [ ] Search bar is prominent and functional
- [ ] Real-time search works with debouncing
- [ ] Alphabetical filtering works alongside search
- [ ] Grid and list views toggle correctly
- [ ] Sorting by name and recent works
- [ ] Pagination handles 100+ contacts
- [ ] Contact detail modal shows full information
- [ ] Responsive on mobile, tablet, desktop
- [ ] Loading states shown appropriately
- [ ] Empty states handled gracefully
- [ ] TypeScript types cover all components
- [ ] Tests cover search and filtering
- [ ] Performance acceptable with 1000+ contacts

## Implementation Steps

### 1. Define TypeScript Types

Create `frontend/src/types/contact.ts`:

```typescript
/**
 * Contact-related TypeScript types
 */

export interface PhoneNumber {
  id: string;
  value: string;
  display_value: string;
  type: string;
  primary: boolean;
}

export interface EmailAddress {
  id: string;
  value: string;
  type: string;
  primary: boolean;
}

export interface Contact {
  id: string;
  display_name: string;
  given_name?: string;
  family_name?: string;
  phone_numbers: PhoneNumber[];
  email_addresses: EmailAddress[];
  updated_at?: string;
}

export interface ContactListResponse {
  contacts: Contact[];
  total: number;
  offset: number;
  limit: number;
  has_more: boolean;
}

export interface ContactStats {
  total: number;
  by_letter: Record<string, number>;
}

export interface SearchResult extends Contact {
  match_type: 'exact' | 'prefix' | 'substring' | 'phone';
  match_field?: string;
  relevance_score?: number;
}

export interface SearchResponse {
  results: SearchResult[];
  count: number;
  query: string;
  elapsed_ms: number;
}

export type ViewMode = 'grid' | 'list';
export type SortOrder = 'name' | 'recent';
export type LetterGroup = 'A' | 'B' | 'C' | 'D' | 'E' | 'F' | 'G' | 'H' | 'I' | 'J' | 'K' | 'L' | 'M' | 'N' | 'O' | 'P' | 'Q' | 'R' | 'S' | 'T' | 'U' | 'V' | 'W' | 'X' | 'Y' | 'Z' | '#' | '';
```

### 2. Create Contacts API Client

Create `frontend/src/api/contacts.ts`:

```typescript
/**
 * Contacts API client with TypeScript
 */
import { apiClient } from './client';
import type {
  Contact,
  ContactListResponse,
  ContactStats,
  SearchResponse,
  SortOrder,
  LetterGroup,
} from '@/types/contact';

export const contactsApi = {
  /**
   * List contacts with pagination and filtering
   */
  async list(params: {
    limit?: number;
    offset?: number;
    sort?: SortOrder;
    group?: LetterGroup;
  } = {}): Promise<ContactListResponse> {
    const response = await apiClient.get<ContactListResponse>('/api/contacts', {
      params: {
        limit: params.limit ?? 30,
        offset: params.offset ?? 0,
        sort: params.sort ?? 'name',
        group: params.group || undefined,
      },
    });
    return response.data;
  },

  /**
   * Get single contact by ID
   */
  async getById(id: string): Promise<Contact> {
    const response = await apiClient.get<Contact>(`/api/contacts/${id}`);
    return response.data;
  },

  /**
   * Get contact statistics
   */
  async getStats(): Promise<ContactStats> {
    const response = await apiClient.get<ContactStats>('/api/contacts/stats');
    return response.data;
  },

  /**
   * Search contacts by name or phone
   */
  async search(query: string, limit: number = 50): Promise<SearchResponse> {
    const response = await apiClient.get<SearchResponse>('/api/search', {
      params: { q: query, limit },
    });
    return response.data;
  },
};
```

### 3. Create Search Composable

Create `frontend/src/composables/useContactSearch.ts`:

```typescript
/**
 * Composable for contact search functionality
 */
import { ref, watch, type Ref } from 'vue';
import { contactsApi } from '@/api/contacts';
import type { SearchResult } from '@/types/contact';

export function useContactSearch() {
  const searchQuery = ref('');
  const searchResults = ref<SearchResult[]>([]);
  const isSearching = ref(false);
  const searchError = ref<string | null>(null);
  const searchElapsedMs = ref(0);

  let searchTimeout: ReturnType<typeof setTimeout> | null = null;
  const DEBOUNCE_MS = 300;

  /**
   * Perform search with debouncing
   */
  function performSearch(query: string) {
    if (searchTimeout) {
      clearTimeout(searchTimeout);
    }

    if (!query || query.trim().length < 2) {
      searchResults.value = [];
      searchElapsedMs.value = 0;
      return;
    }

    isSearching.value = true;
    searchError.value = null;

    searchTimeout = setTimeout(async () => {
      try {
        const response = await contactsApi.search(query.trim());
        searchResults.value = response.results;
        searchElapsedMs.value = response.elapsed_ms;
      } catch (err) {
        searchError.value = 'Failed to search contacts';
        console.error('Search error:', err);
        searchResults.value = [];
      } finally {
        isSearching.value = false;
      }
    }, DEBOUNCE_MS);
  }

  /**
   * Clear search
   */
  function clearSearch() {
    searchQuery.value = '';
    searchResults.value = [];
    searchError.value = null;
    searchElapsedMs.value = 0;
    if (searchTimeout) {
      clearTimeout(searchTimeout);
    }
  }

  /**
   * Check if in search mode
   */
  const isSearchMode = ref(false);
  watch(searchQuery, (newQuery) => {
    isSearchMode.value = newQuery.trim().length >= 2;
    performSearch(newQuery);
  });

  return {
    searchQuery,
    searchResults,
    isSearching,
    searchError,
    searchElapsedMs,
    isSearchMode,
    clearSearch,
  };
}
```

### 4. Create Main Contacts Component

Create `frontend/src/views/Contacts.vue`:

```vue
<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { contactsApi } from '@/api/contacts';
import { useContactSearch } from '@/composables/useContactSearch';
import ContactCard from '@/components/ContactCard.vue';
import ContactModal from '@/components/ContactModal.vue';
import type {
  Contact,
  ContactStats,
  ViewMode,
  SortOrder,
  LetterGroup,
} from '@/types/contact';

// State
const loading = ref(true);
const contacts = ref<Contact[]>([]);
const stats = ref<ContactStats | null>(null);
const error = ref<string | null>(null);

// Pagination
const currentPage = ref(0);
const pageSize = 30;
const totalContacts = ref(0);
const hasMore = ref(false);

// Filters and sorting
const selectedGroup = ref<LetterGroup>('');
const sortOrder = ref<SortOrder>('name');
const viewMode = ref<ViewMode>('grid');

// Modal
const selectedContact = ref<Contact | null>(null);
const showModal = ref(false);

// Search
const {
  searchQuery,
  searchResults,
  isSearching,
  searchError,
  searchElapsedMs,
  isSearchMode,
  clearSearch,
} = useContactSearch();

// Computed
const displayedContacts = computed(() => {
  return isSearchMode.value ? searchResults.value : contacts.value;
});

const totalDisplayed = computed(() => {
  return isSearchMode.value ? searchResults.value.length : totalContacts.value;
});

const letterGroups: LetterGroup[] = [
  '', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
  'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '#'
];

/**
 * Load contacts from API
 */
async function loadContacts() {
  loading.value = true;
  error.value = null;

  try {
    const response = await contactsApi.list({
      limit: pageSize,
      offset: currentPage.value * pageSize,
      sort: sortOrder.value,
      group: selectedGroup.value,
    });

    contacts.value = response.contacts;
    totalContacts.value = response.total;
    hasMore.value = response.has_more;
  } catch (err) {
    error.value = 'Failed to load contacts';
    console.error('Load contacts error:', err);
  } finally {
    loading.value = false;
  }
}

/**
 * Load contact statistics
 */
async function loadStats() {
  try {
    stats.value = await contactsApi.getStats();
  } catch (err) {
    console.error('Load stats error:', err);
  }
}

/**
 * Filter by letter group
 */
function filterByGroup(group: LetterGroup) {
  selectedGroup.value = group;
  currentPage.value = 0;
  clearSearch();
  loadContacts();
}

/**
 * Change sort order
 */
function changeSortOrder(order: SortOrder) {
  sortOrder.value = order;
  currentPage.value = 0;
  loadContacts();
}

/**
 * Change view mode
 */
function changeViewMode(mode: ViewMode) {
  viewMode.value = mode;
  // Persist to localStorage
  localStorage.setItem('contactsViewMode', mode);
}

/**
 * Pagination
 */
function nextPage() {
  if (hasMore.value) {
    currentPage.value++;
    loadContacts();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}

function previousPage() {
  if (currentPage.value > 0) {
    currentPage.value--;
    loadContacts();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}

/**
 * Show contact detail modal
 */
async function showContactDetail(contact: Contact) {
  selectedContact.value = contact;
  showModal.value = true;
}

function closeModal() {
  showModal.value = false;
  selectedContact.value = null;
}

/**
 * Get count for letter group
 */
function getGroupCount(group: LetterGroup): number {
  if (!stats.value) return 0;
  if (group === '') return stats.value.total;
  return stats.value.by_letter[group] || 0;
}

// Load data on mount
onMounted(() => {
  // Restore view mode from localStorage
  const savedViewMode = localStorage.getItem('contactsViewMode');
  if (savedViewMode === 'grid' || savedViewMode === 'list') {
    viewMode.value = savedViewMode;
  }

  loadStats();
  loadContacts();
});

// Watch for search mode changes
watch(isSearchMode, (newValue) => {
  // When exiting search mode, reload contacts
  if (!newValue && searchQuery.value.length < 2) {
    loadContacts();
  }
});
</script>

<template>
  <div class="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
    <!-- Header with Search -->
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900 mb-4">Contacts</h1>
      
      <!-- Search Bar -->
      <div class="relative">
        <div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
          <svg class="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
        <input
          v-model="searchQuery"
          type="text"
          class="block w-full rounded-md border-gray-300 pl-10 pr-12 focus:border-indigo-500 focus:ring-indigo-500 text-lg py-3"
          placeholder="Search contacts by name or phone..."
          autocomplete="off"
        />
        <div v-if="isSearching" class="absolute inset-y-0 right-0 flex items-center pr-3">
          <div class="animate-spin rounded-full h-5 w-5 border-b-2 border-indigo-600"></div>
        </div>
        <button
          v-else-if="searchQuery"
          @click="clearSearch"
          class="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600"
        >
          <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Search Info -->
      <div v-if="isSearchMode" class="mt-2 text-sm text-gray-600">
        Found {{ searchResults.length }} result{{ searchResults.length !== 1 ? 's' : '' }}
        <span v-if="searchElapsedMs > 0" class="text-gray-400">
          ({{ searchElapsedMs.toFixed(1) }}ms)
        </span>
      </div>
    </div>

    <!-- Controls (hidden in search mode) -->
    <div v-if="!isSearchMode" class="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <!-- View and Sort Controls -->
      <div class="flex gap-4">
        <select
          v-model="sortOrder"
          @change="changeSortOrder(sortOrder)"
          class="rounded-md border-gray-300 text-sm"
        >
          <option value="name">Sort by Name</option>
          <option value="recent">Recently Updated</option>
        </select>
        
        <select
          v-model="viewMode"
          @change="changeViewMode(viewMode)"
          class="rounded-md border-gray-300 text-sm"
        >
          <option value="grid">Grid View</option>
          <option value="list">List View</option>
        </select>
      </div>

      <!-- Total Count -->
      <div class="text-sm text-gray-600">
        {{ totalContacts }} contact{{ totalContacts !== 1 ? 's' : '' }}
      </div>
    </div>

    <!-- Letter Filter Pills (hidden in search mode) -->
    <div v-if="!isSearchMode" class="mb-6 flex flex-wrap gap-2">
      <button
        v-for="group in letterGroups"
        :key="group"
        @click="filterByGroup(group)"
        :class="[
          'px-3 py-1 text-sm rounded-md border transition-colors',
          selectedGroup === group
            ? 'bg-indigo-600 text-white border-indigo-600'
            : 'bg-white border-gray-300 hover:bg-gray-50'
        ]"
      >
        {{ group || 'All' }}
        <span v-if="stats" class="ml-1 text-xs opacity-75">
          ({{ getGroupCount(group) }})
        </span>
      </button>
    </div>

    <!-- Error State -->
    <div v-if="error || searchError" class="rounded-md bg-red-50 p-4 mb-6">
      <p class="text-sm text-red-800">{{ error || searchError }}</p>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
    </div>

    <!-- Empty State -->
    <div v-else-if="displayedContacts.length === 0" class="text-center py-12 text-gray-500">
      <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
      </svg>
      <p class="mt-4">
        {{ isSearchMode ? `No results found for "${searchQuery}"` : 'No contacts found' }}
      </p>
      <p v-if="!isSearchMode && selectedGroup" class="mt-2 text-sm">
        Try a different filter
      </p>
      <p v-else-if="isSearchMode" class="mt-2 text-sm">
        Try searching with different keywords
      </p>
      <p v-else class="mt-2 text-sm">
        Sync contacts to get started
      </p>
    </div>

    <!-- Grid View -->
    <div
      v-else-if="viewMode === 'grid'"
      class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
    >
      <ContactCard
        v-for="contact in displayedContacts"
        :key="contact.id"
        :contact="contact"
        :highlight="isSearchMode ? searchQuery : undefined"
        @click="showContactDetail(contact)"
      />
    </div>

    <!-- List View -->
    <div v-else class="bg-white rounded-lg shadow overflow-hidden">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Name
            </th>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Phone
            </th>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Email
            </th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr
            v-for="contact in displayedContacts"
            :key="contact.id"
            @click="showContactDetail(contact)"
            class="hover:bg-gray-50 cursor-pointer"
          >
            <td class="px-6 py-4 whitespace-nowrap">
              <div class="text-sm font-medium text-gray-900">
                <span v-html="highlightText(contact.display_name, searchQuery)"></span>
              </div>
            </td>
            <td class="px-6 py-4">
              <div v-if="contact.phone_numbers.length > 0" class="text-sm text-gray-900">
                <span v-html="highlightText(contact.phone_numbers[0].display_value, searchQuery)"></span>
              </div>
              <div v-else class="text-sm text-gray-400">-</div>
            </td>
            <td class="px-6 py-4">
              <div v-if="contact.email_addresses.length > 0" class="text-sm text-gray-900 truncate max-w-xs">
                {{ contact.email_addresses[0].value }}
              </div>
              <div v-else class="text-sm text-gray-400">-</div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination (hidden in search mode) -->
    <div
      v-if="!isSearchMode && totalContacts > pageSize"
      class="mt-8 flex items-center justify-between"
    >
      <div class="text-sm text-gray-700">
        Showing
        <span class="font-medium">{{ currentPage * pageSize + 1 }}</span>
        to
        <span class="font-medium">{{ Math.min((currentPage + 1) * pageSize, totalContacts) }}</span>
        of
        <span class="font-medium">{{ totalContacts }}</span>
        contacts
      </div>
      <div class="flex gap-2">
        <button
          @click="previousPage"
          :disabled="currentPage === 0"
          :class="[
            'px-3 py-2 text-sm font-medium rounded-md',
            currentPage === 0
              ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
              : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
          ]"
        >
          Previous
        </button>
        <div class="flex items-center px-4 text-sm text-gray-700">
          Page {{ currentPage + 1 }} of {{ Math.ceil(totalContacts / pageSize) }}
        </div>
        <button
          @click="nextPage"
          :disabled="!hasMore"
          :class="[
            'px-3 py-2 text-sm font-medium rounded-md',
            !hasMore
              ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
              : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
          ]"
        >
          Next
        </button>
      </div>
    </div>

    <!-- Contact Detail Modal -->
    <ContactModal
      v-if="showModal && selectedContact"
      :contact="selectedContact"
      @close="closeModal"
    />
  </div>
</template>

<script lang="ts">
/**
 * Highlight search text in results
 */
export function highlightText(text: string, query: string): string {
  if (!query || query.length < 2) return text;
  
  const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
  return text.replace(regex, '<mark class="bg-yellow-200 px-1 rounded">$1</mark>');
}
</script>

<style scoped>
mark {
  background-color: #fef08a;
  padding: 0 0.25rem;
  border-radius: 0.125rem;
}
</style>
```

### 5. Create Contact Card Component

Create `frontend/src/components/ContactCard.vue`:

```vue
<script setup lang="ts">
import type { Contact } from '@/types/contact';

interface Props {
  contact: Contact;
  highlight?: string;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  click: [];
}>();

function highlightText(text: string): string {
  if (!props.highlight || props.highlight.length < 2) return text;
  
  const regex = new RegExp(`(${props.highlight.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
  return text.replace(regex, '<mark class="bg-yellow-200 px-1 rounded">$1</mark>');
}
</script>

<template>
  <div
    class="bg-white p-4 rounded-lg shadow hover:shadow-md transition cursor-pointer"
    @click="emit('click')"
  >
    <div class="flex items-start justify-between">
      <h3 class="font-semibold text-gray-900 truncate flex-1" v-html="highlightText(contact.display_name)"></h3>
      <span
        v-if="contact.phone_numbers.some(p => p.primary)"
        class="ml-2 inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800"
      >
        Primary
      </span>
    </div>

    <!-- Phone Numbers -->
    <div v-if="contact.phone_numbers.length > 0" class="mt-3 space-y-1">
      <div
        v-for="phone in contact.phone_numbers.slice(0, 2)"
        :key="phone.id"
        class="flex items-center text-sm text-gray-600"
      >
        <svg class="h-4 w-4 mr-2 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
        </svg>
        <span class="truncate" v-html="highlightText(phone.display_value)"></span>
        <span class="ml-auto text-xs text-gray-500">{{ phone.type }}</span>
      </div>
      <div v-if="contact.phone_numbers.length > 2" class="text-xs text-gray-500 ml-6">
        +{{ contact.phone_numbers.length - 2 }} more
      </div>
    </div>
    <div v-else class="mt-3 text-sm text-gray-400">No phone numbers</div>

    <!-- Email -->
    <div v-if="contact.email_addresses.length > 0" class="mt-2">
      <div class="flex items-center text-sm text-gray-600 truncate">
        <svg class="h-4 w-4 mr-2 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
        <span class="truncate">{{ contact.email_addresses[0].value }}</span>
      </div>
    </div>
  </div>
</template>
```

### 6. Create Contact Modal Component

Create `frontend/src/components/ContactModal.vue`:

```vue
<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue';
import type { Contact } from '@/types/contact';

interface Props {
  contact: Contact;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  close: [];
}>();

function handleEscape(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    emit('close');
  }
}

function handleBackdropClick(event: MouseEvent) {
  if ((event.target as HTMLElement).id === 'modal-backdrop') {
    emit('close');
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleEscape);
});

onUnmounted(() => {
  document.removeEventListener('keydown', handleEscape);
});
</script>

<template>
  <div
    id="modal-backdrop"
    class="fixed inset-0 bg-gray-500 bg-opacity-75 z-50 flex items-center justify-center p-4"
    @click="handleBackdropClick"
  >
    <div class="relative bg-white rounded-lg shadow-xl max-w-2xl w-full p-6 max-h-[90vh] overflow-y-auto">
      <button
        @click="emit('close')"
        class="absolute top-4 right-4 text-gray-400 hover:text-gray-500"
      >
        <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>

      <h2 class="text-2xl font-bold text-gray-900 mb-2">{{ contact.display_name }}</h2>
      <p v-if="contact.given_name || contact.family_name" class="text-sm text-gray-600 mb-4">
        {{ contact.given_name }} {{ contact.family_name }}
      </p>

      <!-- Phone Numbers -->
      <div v-if="contact.phone_numbers.length > 0" class="mb-6">
        <h3 class="text-sm font-medium text-gray-500 mb-3">Phone Numbers</h3>
        <div class="space-y-2">
          <div
            v-for="phone in contact.phone_numbers"
            :key="phone.id"
            class="flex items-center justify-between p-3 bg-gray-50 rounded-md"
          >
            <div class="flex items-center">
              <svg class="h-5 w-5 mr-3 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
              </svg>
              <div>
                <div class="text-sm font-medium text-gray-900">{{ phone.display_value }}</div>
                <div class="text-xs text-gray-500">{{ phone.type }}{{ phone.primary ? ' • Primary' : '' }}</div>
              </div>
            </div>
            <a :href="`tel:${phone.value}`" class="text-sm text-indigo-600 hover:text-indigo-500">
              Call
            </a>
          </div>
        </div>
      </div>
      <div v-else class="mb-6 text-sm text-gray-500">No phone numbers</div>

      <!-- Email Addresses -->
      <div v-if="contact.email_addresses.length > 0" class="mb-6">
        <h3 class="text-sm font-medium text-gray-500 mb-3">Email Addresses</h3>
        <div class="space-y-2">
          <div
            v-for="email in contact.email_addresses"
            :key="email.id"
            class="flex items-center justify-between p-3 bg-gray-50 rounded-md"
          >
            <div class="flex items-center">
              <svg class="h-5 w-5 mr-3 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              <div>
                <div class="text-sm font-medium text-gray-900">{{ email.value }}</div>
                <div class="text-xs text-gray-500">{{ email.type }}{{ email.primary ? ' • Primary' : '' }}</div>
              </div>
            </div>
            <a :href="`mailto:${email.value}`" class="text-sm text-indigo-600 hover:text-indigo-500">
              Email
            </a>
          </div>
        </div>
      </div>
      <div v-else class="mb-6 text-sm text-gray-500">No email addresses</div>

      <!-- Last Updated -->
      <div v-if="contact.updated_at" class="mt-6 pt-6 border-t border-gray-200">
        <p class="text-xs text-gray-500">
          Last updated: {{ new Date(contact.updated_at).toLocaleString() }}
        </p>
      </div>
    </div>
  </div>
</template>
```

### 7. Add Routes

Update `frontend/src/router/index.ts`:

```typescript
{
  path: '/contacts',
  name: 'Contacts',
  component: () => import('@/views/Contacts.vue'),
  meta: { title: 'Contacts' },
},
```

### 8. Create Component Tests

Create `frontend/src/views/__tests__/Contacts.spec.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createMemoryHistory } from 'vue-router';
import Contacts from '../Contacts.vue';
import { contactsApi } from '@/api/contacts';

vi.mock('@/api/contacts');

describe('Contacts.vue', () => {
  let router: ReturnType<typeof createRouter>;

  beforeEach(() => {
    router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/contacts', component: Contacts }],
    });
    vi.clearAllMocks();
  });

  it('renders search bar', () => {
    const wrapper = mount(Contacts, {
      global: { plugins: [router] },
    });

    expect(wrapper.find('input[type="text"]').exists()).toBe(true);
    expect(wrapper.find('input[type="text"]').attributes('placeholder')).toContain('Search');
  });

  it('shows loading state', () => {
    vi.mocked(contactsApi.list).mockReturnValue(new Promise(() => {})); // Never resolves

    const wrapper = mount(Contacts, {
      global: { plugins: [router] },
    });

    expect(wrapper.find('.animate-spin').exists()).toBe(true);
  });

  it('displays contacts in grid view', async () => {
    vi.mocked(contactsApi.list).mockResolvedValue({
      contacts: [
        {
          id: '1',
          display_name: 'John Doe',
          phone_numbers: [],
          email_addresses: [],
        },
      ],
      total: 1,
      offset: 0,
      limit: 30,
      has_more: false,
    });

    vi.mocked(contactsApi.getStats).mockResolvedValue({
      total: 1,
      by_letter: { J: 1 },
    });

    const wrapper = mount(Contacts, {
      global: { plugins: [router] },
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 100));

    expect(wrapper.text()).toContain('John Doe');
  });

  it('switches between grid and list views', async () => {
    vi.mocked(contactsApi.list).mockResolvedValue({
      contacts: [
        {
          id: '1',
          display_name: 'John Doe',
          phone_numbers: [],
          email_addresses: [],
        },
      ],
      total: 1,
      offset: 0,
      limit: 30,
      has_more: false,
    });

    vi.mocked(contactsApi.getStats).mockResolvedValue({
      total: 1,
      by_letter: {},
    });

    const wrapper = mount(Contacts, {
      global: { plugins: [router] },
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 100));

    // Find view mode select
    const viewSelect = wrapper.find('select[class*="border-gray-300"]');
    
    // Switch to list view
    await viewSelect.setValue('list');
    await wrapper.vm.$nextTick();

    // Should show table
    expect(wrapper.find('table').exists()).toBe(true);
  });

  it('performs search when typing', async () => {
    vi.mocked(contactsApi.search).mockResolvedValue({
      results: [
        {
          id: '1',
          display_name: 'John Doe',
          phone_numbers: [],
          email_addresses: [],
          match_type: 'exact',
        },
      ],
      count: 1,
      query: 'John',
      elapsed_ms: 45.2,
    });

    const wrapper = mount(Contacts, {
      global: { plugins: [router] },
    });

    // Type in search box
    const searchInput = wrapper.find('input[type="text"]');
    await searchInput.setValue('John');

    // Wait for debounce
    await new Promise(resolve => setTimeout(resolve, 400));

    expect(contactsApi.search).toHaveBeenCalledWith('John', 50);
  });
});
```

## Verification

After completing this task:

1. **Install Dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Start Development Servers**:
   ```bash
   # Terminal 1: Backend
   uv run python -m google_contacts_cisco.main

   # Terminal 2: Frontend
   cd frontend && npm run dev
   ```

3. **Test Contacts Page**:
   - Visit http://localhost:5173/contacts
   - Should show search bar and contact cards/list

4. **Test Real-Time Search**:
   - Type in search box
   - Results should update after ~300ms
   - Highlighting should work

5. **Test Alphabetical Filtering**:
   - Click letter buttons (A, B, C, etc.)
   - Contacts should filter by first letter

6. **Test View Toggle**:
   - Switch between Grid and List views
   - Layout should change
   - Preference should persist (localStorage)

7. **Test Contact Modal**:
   - Click on any contact
   - Modal should open with full details
   - Click X or outside to close
   - Press Escape to close

8. **Test Pagination**:
   - If >30 contacts, pagination should appear
   - Click Next/Previous
   - Page should update

9. **Test Responsive**:
   - Resize browser
   - Mobile: 1 column, tablet: 2 columns, desktop: 3 columns

10. **Test TypeScript**:
    ```bash
    cd frontend
    npm run type-check
    ```

11. **Run Tests**:
    ```bash
    cd frontend
    npm run test:unit
    ```

## Notes

- **Integrated Search**: Search seamlessly integrated into main contacts view
- **Dual Mode**: Browse with filters OR search - smooth transition
- **Real-Time**: Debounced search prevents excessive API calls
- **Type-Safe**: Full TypeScript coverage
- **Performance**: Client-side caching, lazy loading
- **UX**: Loading states, empty states, error handling
- **Responsive**: Mobile-first design
- **Accessible**: Keyboard navigation, semantic HTML
- **Persist Preferences**: View mode saved to localStorage

## Common Issues

1. **Search Lag**: Adjust debounce delay if needed
2. **Type Errors**: Run `npm run type-check`
3. **Highlight Issues**: Escape special regex characters
4. **Modal Not Closing**: Check z-index and event handling
5. **CORS**: Ensure backend allows frontend origin

## Performance Optimization

For large contact lists (>1000):
1. Implement virtual scrolling (vue-virtual-scroller)
2. Add request cancellation for abandoned searches
3. Cache search results client-side
4. Lazy load images if added
5. Use Web Workers for filtering

## Related Documentation

- Vue 3 Composition API: https://vuejs.org/guide/extras/composition-api-faq.html
- TypeScript with Vue: https://vuejs.org/guide/typescript/overview.html
- Tailwind CSS: https://tailwindcss.com/docs
- Vitest: https://vitest.dev/

## Estimated Time

8-10 hours (combines old tasks 17 + 18)

