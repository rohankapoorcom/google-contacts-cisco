# Task 6.1: Frontend Framework Setup (Vue 3 + Vite + TypeScript)

## Overview

Set up a modern frontend framework using Vue 3 with Vite and TypeScript, integrated with FastAPI backend. This provides reactive data binding, component architecture, and type safety for building a maintainable web interface.

## Priority

**P1 (High)** - Required for MVP web interface

## Dependencies

- Task 1.1: Environment Setup

## Objectives

1. Set up Vite with Vue 3 and TypeScript
2. Configure Tailwind CSS with PostCSS
3. Set up Vue Router for client-side routing
4. Create base layout and components
5. Configure API client with TypeScript types
6. Set up development and production builds
7. Integrate with FastAPI static file serving
8. Test hot module replacement (HMR)

## Technical Context

### Technology Stack
- **Vue 3**: Composition API with `<script setup>` syntax
- **Vite**: Fast dev server and optimized builds
- **TypeScript**: Type safety and better DX
- **Vue Router**: Client-side routing
- **Tailwind CSS**: Utility-first CSS framework
- **Pinia** (optional): State management if needed

### Project Structure
```
frontend/
├── src/
│   ├── assets/          # Static assets (images, fonts)
│   ├── components/      # Reusable Vue components
│   ├── views/           # Page components
│   ├── router/          # Vue Router configuration
│   ├── api/             # API client and types
│   ├── types/           # TypeScript type definitions
│   ├── App.vue          # Root component
│   └── main.ts          # Entry point
├── public/              # Public static files
├── index.html           # HTML entry point
├── package.json         # Node dependencies
├── tsconfig.json        # TypeScript config
├── vite.config.ts       # Vite configuration
└── tailwind.config.js   # Tailwind configuration
```

### Integration with FastAPI
- Vite dev server runs on port 5173 (development)
- Production builds to `dist/` folder
- FastAPI serves built files from `/static`
- CORS configured for development

## Acceptance Criteria

- [ ] Vite dev server runs with HMR
- [ ] TypeScript compilation works without errors
- [ ] Tailwind CSS is configured and working
- [ ] Vue Router handles navigation
- [ ] API client connects to FastAPI backend
- [ ] Production build generates optimized files
- [ ] FastAPI serves the Vue app
- [ ] Types are defined for API responses
- [ ] Components are properly typed
- [ ] Tests run successfully

## Implementation Steps

### 1. Create Frontend Project Structure

```bash
# Create frontend directory
mkdir -p frontend
cd frontend

# Initialize Vite project with Vue + TypeScript
npm create vite@latest . -- --template vue-ts

# Install dependencies
npm install

# Install additional dependencies
npm install -D tailwindcss postcss autoprefixer
npm install vue-router@4
npm install axios

# Initialize Tailwind
npx tailwindcss init -p
```

### 2. Configure Vite

Create `frontend/vite.config.ts`:

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/directory': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/auth': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: '../google_contacts_cisco/static/dist',
    emptyOutDir: true,
  },
})
```

### 3. Configure TypeScript

Update `frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "module": "ESNext",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,

    /* Bundler mode */
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "preserve",

    /* Linting */
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    
    /* Path aliases */
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src/**/*.ts", "src/**/*.d.ts", "src/**/*.tsx", "src/**/*.vue"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

### 4. Configure Tailwind CSS

Update `frontend/tailwind.config.js`:

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

Create `frontend/src/style.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

/* Custom styles */
@layer components {
  .btn-primary {
    @apply rounded-md bg-indigo-600 px-3.5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600;
  }
  
  .btn-secondary {
    @apply rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50;
  }
  
  .spinner {
    @apply border-4 border-gray-200 border-t-indigo-600 rounded-full w-8 h-8 animate-spin;
  }
}
```

### 5. Set Up TypeScript Types

Create `frontend/src/types/api.ts`:

```typescript
/**
 * API type definitions
 */

export interface PhoneNumber {
  id: string
  value: string
  display_value: string
  type: string
  primary: boolean
}

export interface EmailAddress {
  id: string
  value: string
  type: string
  primary: boolean
}

export interface Contact {
  id: string
  display_name: string
  given_name?: string
  family_name?: string
  phone_numbers: PhoneNumber[]
  email_addresses: EmailAddress[]
  updated_at?: string
}

export interface ContactListResponse {
  contacts: Contact[]
  total: number
  offset: number
  limit: number
  has_more: boolean
}

export interface SearchResult {
  id: string
  display_name: string
  given_name?: string
  family_name?: string
  phone_numbers: PhoneNumber[]
  email_addresses: EmailAddress[]
  match_type: 'exact' | 'prefix' | 'substring' | 'phone'
  match_field: string
}

export interface SearchResponse {
  results: SearchResult[]
  count: number
  query: string
  elapsed_ms: number
}

export interface SyncStatus {
  status: 'idle' | 'running' | 'completed' | 'error'
  progress: number
  current_operation: string
  stats: {
    added: number
    updated: number
    deleted: number
  }
  started_at?: string
  completed_at?: string
  error?: string
}

export interface OAuthStatus {
  authenticated: boolean
  token_info?: {
    valid: boolean
    expired: boolean
    expiry?: string
    scopes: string[]
  }
}
```

### 6. Create API Client

Create `frontend/src/api/client.ts`:

```typescript
/**
 * API client for backend communication
 */
import axios, { AxiosInstance } from 'axios'
import type { 
  ContactListResponse, 
  Contact,
  SearchResponse, 
  SyncStatus,
  OAuthStatus 
} from '@/types/api'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: import.meta.env.DEV ? 'http://localhost:8000' : '',
      headers: {
        'Content-Type': 'application/json',
      },
    })
  }

  // Contacts
  async getContacts(params?: {
    limit?: number
    offset?: number
    sort?: 'name' | 'recent'
    group?: string
  }): Promise<ContactListResponse> {
    const response = await this.client.get<ContactListResponse>('/api/contacts', { params })
    return response.data
  }

  async getContact(id: string): Promise<Contact> {
    const response = await this.client.get<Contact>(`/api/contacts/${id}`)
    return response.data
  }

  async getContactStats() {
    const response = await this.client.get('/api/contacts/stats')
    return response.data
  }

  // Search
  async search(query: string, limit?: number): Promise<SearchResponse> {
    const response = await this.client.get<SearchResponse>('/api/search', {
      params: { q: query, limit },
    })
    return response.data
  }

  // Sync
  async getSyncStatus(): Promise<SyncStatus> {
    const response = await this.client.get<SyncStatus>('/api/sync/status')
    return response.data
  }

  async triggerSync(forceFull: boolean = false): Promise<{ message: string }> {
    const response = await this.client.post('/api/sync/trigger', null, {
      params: { force_full: forceFull },
    })
    return response.data
  }

  async getSyncInfo() {
    const response = await this.client.get('/api/sync/info')
    return response.data
  }

  // OAuth
  async getOAuthStatus(): Promise<OAuthStatus> {
    const response = await this.client.get<OAuthStatus>('/auth/status')
    return response.data
  }

  async refreshToken(): Promise<{ message: string }> {
    const response = await this.client.post('/auth/refresh')
    return response.data
  }

  async disconnect(): Promise<{ message: string }> {
    const response = await this.client.post('/auth/disconnect')
    return response.data
  }
}

export const api = new ApiClient()
```

### 7. Set Up Vue Router

Create `frontend/src/router/index.ts`:

```typescript
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/HomeView.vue'),
  },
  {
    path: '/contacts',
    name: 'Contacts',
    component: () => import('@/views/ContactsView.vue'),
  },
  {
    path: '/search',
    name: 'Search',
    component: () => import('@/views/SearchView.vue'),
  },
  {
    path: '/sync',
    name: 'Sync',
    component: () => import('@/views/SyncView.vue'),
  },
  {
    path: '/oauth/setup',
    name: 'OAuthSetup',
    component: () => import('@/views/OAuthSetupView.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
```

### 8. Create Base Layout

Create `frontend/src/components/BaseLayout.vue`:

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()
const version = ref('0.1.0')

const navigation = [
  { name: 'Home', path: '/' },
  { name: 'Contacts', path: '/contacts' },
  { name: 'Search', path: '/search' },
  { name: 'Sync', path: '/sync' },
]

const isActive = (path: string) => {
  return route.path === path
}
</script>

<template>
  <div class="min-h-full">
    <!-- Navigation -->
    <nav class="bg-white shadow-sm">
      <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div class="flex h-16 justify-between">
          <div class="flex">
            <div class="flex flex-shrink-0 items-center">
              <router-link to="/" class="text-xl font-bold text-gray-900">
                Google Contacts Directory
              </router-link>
            </div>
            <div class="hidden sm:ml-6 sm:flex sm:space-x-8">
              <router-link
                v-for="item in navigation"
                :key="item.path"
                :to="item.path"
                :class="[
                  isActive(item.path)
                    ? 'border-indigo-500 text-gray-900'
                    : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700',
                  'inline-flex items-center border-b-2 px-1 pt-1 text-sm font-medium'
                ]"
              >
                {{ item.name }}
              </router-link>
            </div>
          </div>
          <div class="flex items-center">
            <span class="text-sm text-gray-500">v{{ version }}</span>
          </div>
        </div>
      </div>
    </nav>

    <!-- Main content -->
    <main>
      <slot />
    </main>

    <!-- Footer -->
    <footer class="bg-white mt-12">
      <div class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <p class="text-center text-sm text-gray-500">
          Google Contacts Cisco Directory &copy; 2024
        </p>
      </div>
    </footer>
  </div>
</template>
```

### 9. Create Root App Component

Update `frontend/src/App.vue`:

```vue
<script setup lang="ts">
import BaseLayout from '@/components/BaseLayout.vue'
</script>

<template>
  <BaseLayout>
    <router-view />
  </BaseLayout>
</template>

<style scoped>
/* Component-specific styles if needed */
</style>
```

### 10. Create Home View

Create `frontend/src/views/HomeView.vue`:

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '@/api/client'

interface SystemStatus {
  total_contacts: number
  last_sync?: string
  oauth_configured: boolean
}

const status = ref<SystemStatus | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    const [syncInfo, oauthStatus] = await Promise.all([
      api.getSyncInfo(),
      api.getOAuthStatus(),
    ])
    
    status.value = {
      total_contacts: syncInfo.total_contacts,
      last_sync: syncInfo.last_sync,
      oauth_configured: oauthStatus.authenticated,
    }
  } catch (e) {
    error.value = 'Failed to load system status'
    console.error(e)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
    <!-- Hero section -->
    <div class="text-center">
      <h1 class="text-4xl font-bold tracking-tight text-gray-900 sm:text-6xl">
        Google Contacts Directory
      </h1>
      <p class="mt-6 text-lg leading-8 text-gray-600">
        Access your Google Contacts on Cisco IP Phones with automatic synchronization
      </p>
      <div class="mt-10 flex items-center justify-center gap-x-6">
        <router-link to="/contacts" class="btn-primary">
          View Contacts
        </router-link>
        <router-link to="/sync" class="text-sm font-semibold leading-6 text-gray-900">
          Sync Now <span aria-hidden="true">→</span>
        </router-link>
      </div>
    </div>

    <!-- Features -->
    <div class="mt-16 grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
      <div class="rounded-lg bg-white p-6 shadow">
        <div class="mb-4">
          <svg class="h-8 w-8 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 1.5H8.25A2.25 2.25 0 006 3.75v16.5a2.25 2.25 0 002.25 2.25h7.5A2.25 2.25 0 0018 20.25V3.75a2.25 2.25 0 00-2.25-2.25H13.5m-3 0V3h3V1.5m-3 0h3m-3 18.75h3" />
          </svg>
        </div>
        <h3 class="text-lg font-semibold text-gray-900">Cisco Phone Support</h3>
        <p class="mt-2 text-sm text-gray-600">
          Access your contacts directly from Cisco IP Phone directory
        </p>
      </div>

      <div class="rounded-lg bg-white p-6 shadow">
        <div class="mb-4">
          <svg class="h-8 w-8 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
          </svg>
        </div>
        <h3 class="text-lg font-semibold text-gray-900">Auto Sync</h3>
        <p class="mt-2 text-sm text-gray-600">
          Automatic synchronization with Google Contacts
        </p>
      </div>

      <div class="rounded-lg bg-white p-6 shadow">
        <div class="mb-4">
          <svg class="h-8 w-8 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
          </svg>
        </div>
        <h3 class="text-lg font-semibold text-gray-900">Fast Search</h3>
        <p class="mt-2 text-sm text-gray-600">
          Quick full-text search by name or phone number
        </p>
      </div>
    </div>

    <!-- Status card -->
    <div class="mt-16 rounded-lg bg-white p-6 shadow">
      <h2 class="text-xl font-semibold text-gray-900 mb-4">System Status</h2>
      
      <div v-if="loading" class="flex justify-center py-8">
        <div class="spinner"></div>
      </div>
      
      <div v-else-if="error" class="text-center py-8 text-red-600">
        {{ error }}
      </div>
      
      <div v-else-if="status" class="space-y-2">
        <div class="flex justify-between">
          <span class="text-sm text-gray-600">Total Contacts:</span>
          <span class="text-sm font-medium text-gray-900">{{ status.total_contacts }}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-sm text-gray-600">Last Sync:</span>
          <span class="text-sm font-medium text-gray-900">
            {{ status.last_sync ? new Date(status.last_sync).toLocaleString() : 'Never' }}
          </span>
        </div>
        <div class="flex justify-between">
          <span class="text-sm text-gray-600">OAuth Status:</span>
          <span :class="[
            'text-sm font-medium',
            status.oauth_configured ? 'text-green-600' : 'text-red-600'
          ]">
            {{ status.oauth_configured ? 'Configured' : 'Not Configured' }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>
```

### 11. Update Main Entry Point

Update `frontend/src/main.ts`:

```typescript
import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(router)

app.mount('#app')
```

### 12. Update HTML Entry Point

Update `frontend/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Google Contacts Directory</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

### 13. Configure FastAPI to Serve Vue App

Update `google_contacts_cisco/main.py`:

```python
"""Main application entry point."""
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from google_contacts_cisco._version import __version__
from google_contacts_cisco.api import directory, search, contacts, sync, auth
from google_contacts_cisco.config import settings

# Get base directory
BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Google Contacts Cisco Directory",
    description="Web application for syncing Google Contacts to Cisco IP Phones",
    version=__version__
)

# CORS middleware (for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins if settings.environment == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(directory.router)
app.include_router(search.router)
app.include_router(contacts.router)
app.include_router(sync.router)
app.include_router(auth.router)

# Serve Vue static files (production)
if (BASE_DIR / "static" / "dist").exists():
    app.mount("/assets", StaticFiles(directory=str(BASE_DIR / "static" / "dist" / "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve Vue SPA for all non-API routes."""
        # Skip API routes
        if full_path.startswith(("api/", "directory/", "auth/")):
            return {"error": "Not found"}
        
        # Serve index.html for all other routes (SPA)
        index_file = BASE_DIR / "static" / "dist" / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        
        return {"error": "Frontend not built"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "version": __version__}
```

### 14. Update Package Scripts

Update `frontend/package.json`:

```json
{
  "name": "google-contacts-cisco-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc && vite build",
    "preview": "vite preview",
    "type-check": "vue-tsc --noEmit"
  },
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.2.5",
    "axios": "^1.6.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "@vue/tsconfig": "^0.5.0",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.32",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0",
    "vue-tsc": "^1.8.27"
  }
}
```

### 15. Create Development Scripts

Create `scripts/dev.sh`:

```bash
#!/bin/bash
# Development script to run both backend and frontend

# Start FastAPI backend in background
cd /workspaces/google-contacts-cisco
uv run python -m google_contacts_cisco.main &
BACKEND_PID=$!

# Start Vite frontend dev server
cd frontend
npm run dev &
FRONTEND_PID=$!

# Trap to kill both processes on exit
trap "kill $BACKEND_PID $FRONTEND_PID" EXIT

# Wait for both processes
wait
```

Create `scripts/build.sh`:

```bash
#!/bin/bash
# Production build script

echo "Building frontend..."
cd /workspaces/google-contacts-cisco/frontend
npm run build

echo "Frontend built to ../google_contacts_cisco/static/dist"
echo "Ready for production deployment"
```

## Verification

After completing this task:

### 1. Development Setup

```bash
# Install frontend dependencies
cd frontend
npm install

# Start backend (terminal 1)
cd /workspaces/google-contacts-cisco
uv run python -m google_contacts_cisco.main

# Start frontend dev server (terminal 2)
cd frontend
npm run dev
```

### 2. Test Development Server

- Open http://localhost:5173
- Should see Vue app with hot reload
- Navigation should work (Vue Router)
- Tailwind CSS should be applied
- API calls should proxy to backend

### 3. Test Type Checking

```bash
cd frontend
npm run type-check
# Should complete without errors
```

### 4. Test Production Build

```bash
cd frontend
npm run build
# Check that dist/ folder is created in google_contacts_cisco/static/

# Start backend and test production build
cd ..
uv run python -m google_contacts_cisco.main
# Open http://localhost:8000
# Should serve built Vue app
```

### 5. Test API Integration

- Open browser dev tools (Network tab)
- Navigate through the app
- Verify API calls are made correctly
- Check TypeScript types are working

### 6. Test HMR

- Edit a .vue file
- Save
- Changes should appear immediately without full reload

## Notes

- **Vite Proxy**: Development proxy forwards API calls to FastAPI backend
- **TypeScript**: Provides type safety for API responses and props
- **Vue Router**: Uses HTML5 history mode for clean URLs
- **Production Build**: Vite builds to `static/dist/` for FastAPI to serve
- **Hot Module Replacement**: Vite provides instant feedback during development
- **Composition API**: Modern Vue 3 approach with `<script setup>`
- **Path Aliases**: `@/` maps to `src/` for cleaner imports

## Common Issues

1. **Port Conflicts**: Change Vite port in `vite.config.ts` if 5173 is taken
2. **CORS Errors**: Ensure proxy is configured correctly in development
3. **Type Errors**: Run `npm run type-check` to find TypeScript issues
4. **Build Failures**: Check that all imports are correct and types are defined
5. **Routing Issues**: Ensure FastAPI serves `index.html` for SPA routes
6. **API 404s**: Verify proxy configuration matches FastAPI routes

## Performance Optimization

- Vite automatically code-splits routes
- Tree-shaking removes unused code
- Tailwind purges unused CSS in production
- Use `defineAsyncComponent` for lazy loading
- Enable Vite build compression plugin

## Future Enhancements

- Add Pinia for centralized state management
- Add Vue DevTools integration
- Add unit tests with Vitest
- Add E2E tests with Playwright
- Add PWA support with vite-plugin-pwa
- Add i18n for internationalization
- Add component library (Headless UI)

## Related Documentation

- Vue 3: https://vuejs.org/
- Vite: https://vitejs.dev/
- Vue Router: https://router.vuejs.org/
- TypeScript: https://www.typescriptlang.org/
- Tailwind CSS: https://tailwindcss.com/
- Composition API: https://vuejs.org/guide/extras/composition-api-faq.html

## Estimated Time

5-6 hours
