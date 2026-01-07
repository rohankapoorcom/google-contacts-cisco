/**
 * Vue Router configuration.
 * Defines application routes and navigation structure.
 */
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/HomeView.vue'),
    meta: {
      title: 'Home',
      description: 'Google Contacts Directory Dashboard',
    },
  },
  {
    path: '/contacts',
    name: 'Contacts',
    component: () => import('@/views/ContactsView.vue'),
    meta: {
      title: 'Contacts',
      description: 'Browse and search your contacts',
    },
  },
  {
    path: '/search',
    name: 'Search',
    component: () => import('@/views/SearchView.vue'),
    meta: {
      title: 'Search',
      description: 'Search contacts by name or phone number',
    },
  },
  {
    path: '/sync',
    name: 'Sync',
    component: () => import('@/views/SyncView.vue'),
    meta: {
      title: 'Sync Management',
      description: 'Manage contact synchronization',
    },
  },
  {
    path: '/oauth/setup',
    name: 'OAuthSetup',
    component: () => import('@/views/OAuthSetupView.vue'),
    meta: {
      title: 'OAuth Setup',
      description: 'Configure Google OAuth authentication',
    },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFoundView.vue'),
    meta: {
      title: '404 - Not Found',
      description: 'Page not found',
    },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(_to, _from, savedPosition) {
    // Return to saved position on back navigation
    if (savedPosition) {
      return savedPosition
    }
    // Scroll to top on new navigation
    return { top: 0 }
  },
})

// Update document title on navigation
router.beforeEach((to, _from, next) => {
  const title = to.meta.title as string | undefined
  if (title) {
    document.title = `${title} | Google Contacts Directory`
  } else {
    document.title = 'Google Contacts Directory'
  }
  next()
})

export default router

