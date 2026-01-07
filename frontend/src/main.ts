/**
 * Main application entry point.
 * Initializes Vue app with router and global styles.
 */
import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'

// Create and mount the Vue application
const app = createApp(App)

// Install Vue Router
app.use(router)

// Mount the app
app.mount('#app')
