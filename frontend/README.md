# RLCF Framework - React Frontend

Modern React/TypeScript frontend for the Reinforcement Learning from Community Feedback (RLCF) framework, designed for legal AI research and validation.

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm
- RLCF Backend running on `http://localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

The application will be available at `http://localhost:3000`

## 🏗️ Tech Stack

- **React 18** - UI library with concurrent features
- **TypeScript** - Type safety and developer experience
- **Vite** - Fast build tool and development server
- **TanStack Query** - Data fetching and caching
- **Zustand** - Lightweight state management
- **React Router v6** - Client-side routing
- **Tailwind CSS** - Utility-first styling
- **Framer Motion** - Smooth animations

## 📁 Project Structure

```
src/
├── app/              # App-level configuration
│   ├── routes/       # Route definitions
│   ├── providers/    # Context providers
│   └── store/        # Zustand stores
├── features/         # Feature-based modules
│   ├── auth/         # Authentication
│   ├── tasks/        # Task management
│   ├── evaluation/   # Feedback evaluation
│   ├── analytics/    # Data visualization
│   └── admin/        # Admin controls
├── components/       # UI components
│   ├── ui/           # Base components
│   ├── layouts/      # Layout components
│   └── shared/       # Shared components
├── hooks/            # Custom React hooks
├── lib/              # Utilities & API client
└── types/            # TypeScript definitions
```

## ✅ Implemented Features

### Core Infrastructure
- React/Vite project with TypeScript
- Tailwind CSS with custom RLCF theme
- React Router v6 routing
- TanStack Query for API data fetching
- Zustand state management
- WebSocket integration for real-time updates

### Authentication & Authorization
- JWT-based authentication
- Role-based access control (Admin/Evaluator/Viewer)
- Auth guards for protected routes
- Persistent login state

### UI Components
- TaskCard with legal theme styling
- AuthorityScoreCard with animated progress
- Modern sidebar navigation
- Responsive header
- Glass morphism design elements

### Dashboard
- Unified dashboard with role-based views
- System metrics overview
- Available tasks display
- Authority score visualization
- Recent activity feed

## 🎯 User Roles

- **Admin**: Full system access, configuration management
- **Evaluator**: Task evaluation, performance tracking
- **Viewer**: Read-only access to public stats and leaderboard

## 🔌 API Integration

- Complete REST API client for RLCF backend
- Real-time WebSocket connections
- Error handling with toast notifications
- Optimistic updates and cache management
- Proxy configuration for development

## 🎨 Design System

### Color Palette
- **Authority**: Violet/Purple gradients
- **Consensus**: Pink/Red gradients  
- **Uncertainty**: Blue/Cyan gradients
- **Background**: Dark slate theme

### Components
- Glass morphism cards
- Animated progress indicators
- Gradient accent elements
- Responsive layouts

## 🧪 Demo Credentials

```
Admin:     admin@rlcf.ai     / admin123
Evaluator: evaluator@rlcf.ai / eval123  
Viewer:    viewer@rlcf.ai    / view123
```

## 🚀 Development

```bash
npm run dev      # Start development server
npm run build    # Build for production  
npm run preview  # Preview production build
npm run lint     # Run ESLint
```

## 📋 Next Steps

The foundation is complete! Priority features to implement:

1. **Task Evaluation Wizard** - Multi-step evaluation interface
2. **Advanced Analytics** - Charts and data visualizations  
3. **Configuration Management** - Live YAML editing
4. **Real-time Collaboration** - Multi-user evaluation
5. **Performance Monitoring** - User activity tracking

---

**Legal AI Research Framework** - Modern interface for distributed legal AI validation
