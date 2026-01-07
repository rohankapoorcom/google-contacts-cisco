# Google Contacts Cisco Directory - Frontend

A modern Vue 3 + TypeScript frontend for the Google Contacts Cisco Directory application. This web interface provides contact management, synchronization monitoring, and OAuth configuration for syncing Google Contacts with Cisco IP Phones.

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm
- Backend server running (see main project README)

### Development Setup

```bash
# Install dependencies
npm install

# Start development server (runs on http://localhost:5173)
npm run dev

# API calls are automatically proxied to backend on http://localhost:8000
```

### Build for Production

```bash
# Type check and build
npm run build

# Output goes to ../google_contacts_cisco/static/dist/
# Served by FastAPI backend
```

## 📋 Available Scripts

- `npm run dev` - Start Vite development server with HMR
- `npm run build` - Type check and build for production
- `npm run preview` - Preview production build locally
- `npm run type-check` - Run TypeScript type checking

## 🏗️ Project Structure

```
src/
├── components/          # Reusable Vue components
│   ├── BaseLayout.vue   # Main app layout with navigation
│   └── ...
├── views/               # Page components (routes)
│   ├── HomeView.vue     # Dashboard with system status
│   ├── ContactsView.vue # Contact directory (Task 17)
│   ├── SearchView.vue   # Search interface (Task 17)
│   ├── SyncView.vue     # Sync management (Task 19)
│   └── ...
├── api/                 # API client and types
│   ├── client.ts        # Axios-based API client
│   └── index.ts         # Exports
├── types/               # TypeScript type definitions
│   └── api.ts           # API response types
├── router/              # Vue Router configuration
│   └── index.ts         # Route definitions
├── style.css            # Global styles and Tailwind imports
└── main.ts              # Vue app entry point
```

## 🔗 Integration with Backend

### Development
- Vite proxy forwards API calls to FastAPI backend
- CORS enabled for frontend origin
- Hot module replacement for instant feedback

### Production
- Built assets served by FastAPI static files
- Single-page application (SPA) routing handled by frontend
- Same-origin deployment eliminates CORS needs

### API Endpoints
- `/api/contacts` - Contact operations
- `/api/search` - Full-text search
- `/api/sync` - Synchronization management
- `/auth` - OAuth authentication

## 🎨 Design System

Built with Tailwind CSS featuring:
- Custom brand colors (indigo/purple gradient)
- Consistent component styles (buttons, cards, badges)
- Dark mode support (future enhancement)
- Responsive design for mobile/tablet/desktop

## 🛠️ Technology Stack

- **Vue 3** - Composition API with `<script setup>`
- **TypeScript** - Strict type checking
- **Vite** - Fast build tool with HMR
- **Vue Router 4** - Client-side routing
- **Axios** - HTTP client for API calls
- **Tailwind CSS** - Utility-first styling

## 📝 Development Notes

- TypeScript strict mode enabled for type safety
- Path aliases configured (`@/` maps to `src/`)
- ESLint rules enforced via TypeScript compiler
- All API calls are typed with generated interfaces

## 🔄 Upcoming Features

- **Task 16**: OAuth Setup Interface
- **Task 17**: Contacts Directory with Integrated Search
- **Task 19**: Sync Management Interface

---

Built as part of the Google Contacts Cisco Directory project.
