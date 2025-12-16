# Task 6.2: OAuth Setup Interface (Vue 3 + TypeScript)

## Overview

Create a Vue 3 component for setting up Google OAuth authentication. This interface will guide users through the OAuth flow, handle the callback, and display the current authentication status using modern reactive patterns with TypeScript.

## Priority

**P0 (Critical)** - Required for initial setup

## Dependencies

- Task 1.3: Configuration Management
- Task 2.2: OAuth Implementation  
- Task 6.1: Frontend Framework Setup (Vue 3 + Vite + TypeScript)

## Objectives

1. Create OAuth setup Vue component
2. Display current OAuth status reactively
3. Implement "Connect Google" button with proper UX
4. Handle OAuth callback with Vue Router
5. Show token expiry information with auto-refresh
6. Add token refresh functionality
7. Handle errors gracefully with user-friendly messages
8. Type-safe API integration with TypeScript
9. Test OAuth flow end-to-end

## Technical Context

### OAuth Flow with Vue
1. User clicks "Connect Google" button in Vue component
2. Redirected to Google OAuth consent screen (external)
3. User authorizes application
4. Redirected back to Vue app callback route
5. Vue component processes callback, saves OAuth tokens
6. Reactive state updates show success

### Architecture
- **Component**: `OAuthSetup.vue` - Main OAuth setup page
- **API Client**: TypeScript-typed Axios calls
- **Router**: Vue Router handles `/oauth/setup` and `/oauth/callback` routes
- **State**: Reactive refs for OAuth status, loading, errors

### Security
- CSRF protection via state parameter
- HTTPS required for production
- Secure token storage (backend handles)
- No sensitive data in frontend state

## Acceptance Criteria

- [ ] OAuth setup page displays current status reactively
- [ ] "Connect Google" button initiates OAuth flow
- [ ] Callback route displays success/error message
- [ ] Token expiry is shown and updates
- [ ] Refresh button works and shows loading state
- [ ] Error messages are user-friendly with retry options
- [ ] TypeScript types cover all API responses
- [ ] Component tests cover OAuth flow
- [ ] Works with real Google consent screen

## Implementation Steps

### 1. Define TypeScript Types

Create `frontend/src/types/oauth.ts`:

```typescript
/**
 * OAuth-related TypeScript types
 */

export interface OAuthTokenInfo {
  valid: boolean;
  expired: boolean;
  expiry: string | null;
  scopes: string[];
}

export interface OAuthStatus {
  authenticated: boolean;
  token_info: OAuthTokenInfo | null;
}

export interface OAuthStatusResponse {
  authenticated: boolean;
  token_info?: OAuthTokenInfo;
}

export interface ApiResponse<T = unknown> {
  message?: string;
  detail?: string;
  data?: T;
}

export interface ApiError {
  detail: string;
  status?: number;
}
```

### 2. Create OAuth API Client

Create `frontend/src/api/oauth.ts`:

```typescript
/**
 * OAuth API client with TypeScript
 */
import { apiClient } from './client';
import type { OAuthStatusResponse, ApiResponse } from '@/types/oauth';

export const oauthApi = {
  /**
   * Get current OAuth status
   */
  async getStatus(): Promise<OAuthStatusResponse> {
    const response = await apiClient.get<OAuthStatusResponse>('/auth/status');
    return response.data;
  },

  /**
   * Refresh OAuth token
   */
  async refreshToken(): Promise<ApiResponse> {
    const response = await apiClient.post<ApiResponse>('/auth/refresh');
    return response.data;
  },

  /**
   * Disconnect OAuth (delete tokens)
   */
  async disconnect(): Promise<ApiResponse> {
    const response = await apiClient.post<ApiResponse>('/auth/disconnect');
    return response.data;
  },

  /**
   * Get Google OAuth authorization URL
   * Note: This redirects, doesn't return data
   */
  getAuthUrl(): string {
    return `${import.meta.env.VITE_API_URL}/auth/google`;
  },
};
```

### 3. Create OAuth Setup Component

Create `frontend/src/views/OAuthSetup.vue`:

```vue
<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { oauthApi } from '@/api/oauth';
import type { OAuthStatus, ApiError } from '@/types/oauth';

const router = useRouter();
const route = useRoute();

// Reactive state
const loading = ref(true);
const oauthStatus = ref<OAuthStatus | null>(null);
const error = ref<string | null>(null);
const isRefreshing = ref(false);

// Computed properties
const isAuthenticated = computed(() => oauthStatus.value?.authenticated ?? false);
const tokenInfo = computed(() => oauthStatus.value?.token_info);
const tokenValid = computed(() => tokenInfo.value?.valid ?? false);
const tokenExpiry = computed(() => {
  if (!tokenInfo.value?.expiry) return null;
  return new Date(tokenInfo.value.expiry);
});
const expiryFormatted = computed(() => {
  if (!tokenExpiry.value) return null;
  return tokenExpiry.value.toLocaleString();
});

/**
 * Load OAuth status from API
 */
async function loadOAuthStatus(): Promise<void> {
  loading.value = true;
  error.value = null;

  try {
    const status = await oauthApi.getStatus();
    oauthStatus.value = {
      authenticated: status.authenticated,
      token_info: status.token_info || null,
    };
  } catch (err) {
    const apiError = err as ApiError;
    error.value = apiError.detail || 'Failed to load OAuth status';
    console.error('OAuth status error:', err);
  } finally {
    loading.value = false;
  }
}

/**
 * Initiate OAuth flow - redirect to Google
 */
function connectGoogle(): void {
  window.location.href = oauthApi.getAuthUrl();
}

/**
 * Refresh OAuth token
 */
async function refreshToken(): Promise<void> {
  isRefreshing.value = true;
  error.value = null;

  try {
    await oauthApi.refreshToken();
    
    // Show success message
    showToast('Token refreshed successfully', 'success');
    
    // Reload status
    await loadOAuthStatus();
  } catch (err) {
    const apiError = err as ApiError;
    error.value = apiError.detail || 'Failed to refresh token';
    showToast('Failed to refresh token', 'error');
    console.error('Token refresh error:', err);
  } finally {
    isRefreshing.value = false;
  }
}

/**
 * Disconnect OAuth
 */
async function disconnect(): Promise<void> {
  if (!confirm('Are you sure you want to disconnect? You will need to re-authorize to sync contacts.')) {
    return;
  }

  try {
    await oauthApi.disconnect();
    showToast('Disconnected successfully', 'success');
    await loadOAuthStatus();
  } catch (err) {
    const apiError = err as ApiError;
    error.value = apiError.detail || 'Failed to disconnect';
    showToast('Failed to disconnect', 'error');
    console.error('Disconnect error:', err);
  }
}

/**
 * Simple toast notification helper
 */
function showToast(message: string, type: 'success' | 'error'): void {
  // TODO: Implement with a proper toast library or custom component
  alert(`[${type.toUpperCase()}] ${message}`);
}

// Load status on mount
onMounted(() => {
  loadOAuthStatus();
});
</script>

<template>
  <div class="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8">
    <div class="rounded-lg bg-white p-8 shadow">
      <h1 class="text-2xl font-bold text-gray-900 mb-6">
        Google OAuth Setup
      </h1>

      <!-- Loading State -->
      <div v-if="loading" class="flex items-center justify-center py-8">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="rounded-md bg-red-50 p-4 mb-6">
        <div class="flex">
          <div class="flex-shrink-0">
            <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
            </svg>
          </div>
          <div class="ml-3">
            <h3 class="text-sm font-medium text-red-800">Error</h3>
            <div class="mt-2 text-sm text-red-700">
              <p>{{ error }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Not Authenticated -->
      <div v-else-if="!isAuthenticated">
        <!-- Instructions -->
        <div class="mb-8 space-y-4">
          <h2 class="text-lg font-semibold text-gray-900">Setup Instructions</h2>
          <ol class="list-decimal list-inside space-y-2 text-sm text-gray-600">
            <li>Click the "Connect Google Account" button below</li>
            <li>Sign in to your Google account if prompted</li>
            <li>Review and authorize the requested permissions</li>
            <li>You'll be redirected back to this application</li>
            <li>Once connected, your contacts will sync automatically</li>
          </ol>

          <div class="rounded-md bg-blue-50 p-4">
            <div class="flex">
              <div class="flex-shrink-0">
                <svg class="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
                </svg>
              </div>
              <div class="ml-3">
                <h3 class="text-sm font-medium text-blue-800">Permissions Required</h3>
                <div class="mt-2 text-sm text-blue-700">
                  <p>This application requires read-only access to your Google Contacts.</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Connect Button -->
        <button
          @click="connectGoogle"
          class="inline-flex items-center justify-center rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
        >
          <svg class="mr-2 h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12.545,10.239v3.821h5.445c-0.712,2.315-2.647,3.972-5.445,3.972c-3.332,0-6.033-2.701-6.033-6.032s2.701-6.032,6.033-6.032c1.498,0,2.866,0.549,3.921,1.453l2.814-2.814C17.503,2.988,15.139,2,12.545,2C7.021,2,2.543,6.477,2.543,12s4.478,10,10.002,10c8.396,0,10.249-7.85,9.426-11.748L12.545,10.239z"/>
          </svg>
          Connect Google Account
        </button>
      </div>

      <!-- Authenticated -->
      <div v-else class="space-y-6">
        <div class="rounded-md bg-green-50 p-4">
          <div class="flex">
            <div class="flex-shrink-0">
              <svg class="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
              </svg>
            </div>
            <div class="ml-3">
              <h3 class="text-sm font-medium text-green-800">Connected to Google</h3>
              <div class="mt-2 text-sm text-green-700">
                <p>Your Google account is connected and authorized.</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Token Info -->
        <div v-if="tokenInfo" class="border-t border-gray-200 pt-4">
          <dl class="divide-y divide-gray-200">
            <div class="py-3 flex justify-between">
              <dt class="text-sm font-medium text-gray-500">Status</dt>
              <dd class="text-sm text-gray-900">
                <span
                  v-if="tokenValid"
                  class="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800"
                >
                  Valid
                </span>
                <span
                  v-else
                  class="inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800"
                >
                  Expired
                </span>
              </dd>
            </div>
            <div v-if="expiryFormatted" class="py-3 flex justify-between">
              <dt class="text-sm font-medium text-gray-500">Expires</dt>
              <dd class="text-sm text-gray-900">{{ expiryFormatted }}</dd>
            </div>
          </dl>
        </div>

        <!-- Actions -->
        <div class="flex gap-4">
          <button
            @click="refreshToken"
            :disabled="isRefreshing"
            class="inline-flex items-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg
              class="mr-2 h-4 w-4"
              :class="{ 'animate-spin': isRefreshing }"
              fill="none"
              viewBox="0 0 24 24"
              stroke-width="1.5"
              stroke="currentColor"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
            </svg>
            {{ isRefreshing ? 'Refreshing...' : 'Refresh Token' }}
          </button>

          <button
            @click="disconnect"
            class="inline-flex items-center rounded-md bg-red-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-red-500"
          >
            <svg class="mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5.636 5.636a9 9 0 1012.728 0M12 3v9" />
            </svg>
            Disconnect
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Component-specific styles if needed */
</style>
```

### 4. Create OAuth Callback Component

Create `frontend/src/views/OAuthCallback.vue`:

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';

const router = useRouter();
const route = useRoute();

const success = ref(false);
const loading = ref(true);
const errorMessage = ref<string | null>(null);

onMounted(() => {
  // Check for error in URL
  const error = route.query.error as string | undefined;
  if (error) {
    success.value = false;
    errorMessage.value = `Authorization error: ${error}`;
    loading.value = false;
    return;
  }

  // Check for authorization code
  const code = route.query.code as string | undefined;
  if (!code) {
    success.value = false;
    errorMessage.value = 'No authorization code received';
    loading.value = false;
    return;
  }

  // Success - backend will handle the code exchange
  success.value = true;
  loading.value = false;
});

function goToSetup(): void {
  router.push('/oauth/setup');
}

function goToSync(): void {
  router.push('/sync');
}

function goToHome(): void {
  router.push('/');
}
</script>

<template>
  <div class="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8">
    <div class="rounded-lg bg-white p-8 shadow text-center">
      <!-- Loading -->
      <div v-if="loading" class="flex items-center justify-center py-8">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>

      <!-- Success -->
      <div v-else-if="success">
        <div class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
          <svg class="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
          </svg>
        </div>

        <h1 class="mt-4 text-2xl font-bold text-gray-900">
          Successfully Connected!
        </h1>

        <p class="mt-2 text-sm text-gray-600">
          Your Google account has been connected successfully.
        </p>

        <div class="mt-6 flex gap-4 justify-center">
          <button
            @click="goToSync"
            class="inline-flex items-center rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500"
          >
            Start Sync
          </button>
          <button
            @click="goToHome"
            class="inline-flex items-center rounded-md bg-white px-4 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
          >
            Go to Home
          </button>
        </div>
      </div>

      <!-- Error -->
      <div v-else>
        <div class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
          <svg class="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>

        <h1 class="mt-4 text-2xl font-bold text-gray-900">
          Connection Failed
        </h1>

        <p class="mt-2 text-sm text-gray-600">
          {{ errorMessage }}
        </p>

        <div class="mt-6">
          <button
            @click="goToSetup"
            class="inline-flex items-center rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500"
          >
            Try Again
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
```

### 5. Add Routes to Vue Router

Update `frontend/src/router/index.ts`:

```typescript
import { createRouter, createWebHistory } from 'vue-router';
import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
  },
  {
    path: '/oauth/setup',
    name: 'OAuthSetup',
    component: () => import('@/views/OAuthSetup.vue'),
    meta: { title: 'OAuth Setup' },
  },
  {
    path: '/oauth/callback',
    name: 'OAuthCallback',
    component: () => import('@/views/OAuthCallback.vue'),
    meta: { title: 'OAuth Callback' },
  },
  // ... other routes
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
});

// Set page title
router.beforeEach((to, _from, next) => {
  const title = to.meta.title as string | undefined;
  if (title) {
    document.title = `${title} - Google Contacts Directory`;
  }
  next();
});

export default router;
```

### 6. Create Component Tests

Create `frontend/src/views/__tests__/OAuthSetup.spec.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createMemoryHistory } from 'vue-router';
import OAuthSetup from '../OAuthSetup.vue';
import { oauthApi } from '@/api/oauth';
import type { OAuthStatusResponse } from '@/types/oauth';

// Mock the OAuth API
vi.mock('@/api/oauth', () => ({
  oauthApi: {
    getStatus: vi.fn(),
    refreshToken: vi.fn(),
    disconnect: vi.fn(),
    getAuthUrl: vi.fn(() => 'http://localhost:8000/auth/google'),
  },
}));

describe('OAuthSetup.vue', () => {
  let router: ReturnType<typeof createRouter>;

  beforeEach(() => {
    router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/oauth/setup', component: OAuthSetup }],
    });
    vi.clearAllMocks();
  });

  it('renders loading state initially', () => {
    const wrapper = mount(OAuthSetup, {
      global: { plugins: [router] },
    });

    expect(wrapper.find('.animate-spin').exists()).toBe(true);
  });

  it('renders not authenticated state', async () => {
    vi.mocked(oauthApi.getStatus).mockResolvedValue({
      authenticated: false,
      token_info: null,
    });

    const wrapper = mount(OAuthSetup, {
      global: { plugins: [router] },
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 100));

    expect(wrapper.text()).toContain('Setup Instructions');
    expect(wrapper.text()).toContain('Connect Google Account');
  });

  it('renders authenticated state with token info', async () => {
    vi.mocked(oauthApi.getStatus).mockResolvedValue({
      authenticated: true,
      token_info: {
        valid: true,
        expired: false,
        expiry: '2024-12-31T23:59:59Z',
        scopes: ['https://www.googleapis.com/auth/contacts.readonly'],
      },
    });

    const wrapper = mount(OAuthSetup, {
      global: { plugins: [router] },
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 100));

    expect(wrapper.text()).toContain('Connected to Google');
    expect(wrapper.text()).toContain('Valid');
    expect(wrapper.find('button').text()).toContain('Refresh Token');
  });

  it('handles refresh token action', async () => {
    vi.mocked(oauthApi.getStatus).mockResolvedValue({
      authenticated: true,
      token_info: {
        valid: true,
        expired: false,
        expiry: '2024-12-31T23:59:59Z',
        scopes: [],
      },
    });
    vi.mocked(oauthApi.refreshToken).mockResolvedValue({ message: 'success' });

    const wrapper = mount(OAuthSetup, {
      global: { plugins: [router] },
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 100));

    const refreshButton = wrapper.findAll('button')[0];
    await refreshButton.trigger('click');

    expect(oauthApi.refreshToken).toHaveBeenCalled();
  });

  it('shows error state when API fails', async () => {
    vi.mocked(oauthApi.getStatus).mockRejectedValue({
      detail: 'API Error',
    });

    const wrapper = mount(OAuthSetup, {
      global: { plugins: [router] },
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 100));

    expect(wrapper.text()).toContain('Error');
    expect(wrapper.text()).toContain('API Error');
  });
});
```


## Testing Requirements

**⚠️ Critical**: This task is not complete until comprehensive unit tests are written and passing.

### Test Coverage Requirements
- All functions and methods must have tests
- Both success and failure paths must be covered
- Edge cases and boundary conditions must be tested
- **Minimum coverage: 80% for this module**
- **Target coverage: 85%+ for services, 90%+ for utilities**

### Test Files to Create
Create test file(s) in `tests/unit/` matching your implementation structure:

```
Implementation File              →  Test File
─────────────────────────────────────────────────────────────
[implementation path]            →  tests/unit/[same structure]/test_[filename].py
```

### Test Structure Template
```python
"""Test [module name].

This module tests the [feature] implementation from this task.
"""
import pytest
from google_contacts_cisco.[module] import [Component]


class Test[FeatureName]:
    """Test [feature] functionality."""
    
    def test_typical_use_case(self):
        """Test the main success path."""
        # Arrange
        input_data = ...
        
        # Act
        result = component.method(input_data)
        
        # Assert
        assert result == expected
    
    def test_handles_invalid_input(self):
        """Test error handling for invalid input."""
        with pytest.raises(ValueError):
            component.method(invalid_input)
    
    def test_edge_case_empty_data(self):
        """Test behavior with empty/null data."""
        result = component.method([])
        assert result == []
    
    def test_edge_case_boundary_values(self):
        """Test boundary conditions."""
        ...
```

### What to Test
- ✅ **Success paths**: Typical use cases and expected inputs
- ✅ **Error paths**: Invalid inputs, exceptions, error conditions
- ✅ **Edge cases**: Empty data, null values, boundary conditions, large datasets
- ✅ **Side effects**: Database changes, file operations, API calls
- ✅ **Return values**: Correct types, formats, and values
- ✅ **State changes**: Object state, system state

### Testing Best Practices
- Use descriptive test names that explain what is being tested
- Follow Arrange-Act-Assert pattern
- Use fixtures from `tests/conftest.py` for common test data
- Mock external dependencies (APIs, databases, file system)
- Keep tests independent (no shared state)
- Make tests fast (< 5 seconds per test file)
- Test behavior, not implementation details

### Running Your Tests
```bash
# Run tests for this specific module
uv run pytest tests/unit/[your_test_file].py -v

# Run with coverage report
uv run pytest tests/unit/[your_test_file].py \
    --cov=google_contacts_cisco.[your_module] \
    --cov-report=term-missing

# Run in watch mode (re-run on file changes)
uv run pytest-watch tests/unit/[your_directory]/ -v
```

### Acceptance Criteria Additions
- [ ] All new code has corresponding tests
- [ ] Tests cover success cases, error cases, and edge cases
- [ ] All tests pass (`pytest tests/unit/[module]/ -v`)
- [ ] Coverage is >80% for this module
- [ ] Tests are independent and can run in any order
- [ ] External dependencies are properly mocked
- [ ] Test names clearly describe what is being tested

### Example Test Scenarios for This Task
- Test OAuthSetup component renders
- Test OAuth status display (connected/not connected)
- Test connect button triggers OAuth flow
- Test token refresh functionality
- Test disconnect functionality
- Test error state display


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

3. **Test OAuth Setup Page**:
   - Visit http://localhost:5173/oauth/setup
   - Should show "Setup Instructions" if not authenticated
   - Should show "Connected" status if authenticated

4. **Test OAuth Flow**:
   - Click "Connect Google Account"
   - Should redirect to Google consent screen
   - After authorization, redirected to callback page
   - Should show success message

5. **Test Token Refresh**:
   - After connecting, click "Refresh Token"
   - Should show loading spinner
   - Should update token info

6. **Test Disconnect**:
   - Click "Disconnect"
   - Should show confirmation dialog
   - After confirmation, status should change

7. **Test TypeScript Compilation**:
   ```bash
   cd frontend
   npm run type-check
   # Should complete without errors
   ```

8. **Run Component Tests**:
   ```bash
   cd frontend
   npm run test:unit
   ```

## Notes

- **Reactive**: Uses Vue 3 Composition API with `ref` and `computed`
- **Type-Safe**: Full TypeScript coverage for API calls and component props
- **Error Handling**: Comprehensive error states with user-friendly messages
- **Loading States**: Loading spinners and disabled buttons during async operations
- **Vue Router**: Proper integration with client-side routing
- **Composables**: Could extract OAuth logic into a composable for reuse
- **No Jinja2**: Pure Vue SFC, no server-side templates needed

## Common Issues

1. **CORS Errors**: Ensure backend CORS allows frontend origin
2. **Type Errors**: Run `npm run type-check` to catch TypeScript issues
3. **API URL**: Check `VITE_API_URL` in `.env` file
4. **Router Issues**: Ensure routes are registered in router/index.ts
5. **Redirect URI**: Must match Google Console configuration

## Related Documentation

- Vue 3 Composition API: https://vuejs.org/guide/extras/composition-api-faq.html
- Vue Router: https://router.vuejs.org/
- TypeScript with Vue: https://vuejs.org/guide/typescript/overview.html
- Vitest: https://vitest.dev/

## Estimated Time

4-5 hours

