import { create } from 'zustand';
import type { DashboardMode } from '../../types/index';
import { UserRole } from '../../types/index';

interface UIState {
  // Dashboard
  dashboardMode: keyof DashboardMode;
  sidebarCollapsed: boolean;
  
  // Modals and overlays
  modals: {
    taskCreation: boolean;
    userProfile: boolean;
    settings: boolean;
    help: boolean;
  };
  
  // Loading states
  globalLoading: boolean;
  loadingStates: Record<string, boolean>;
  
  // Theme
  theme: 'dark' | 'light';
  
  // Notifications
  notifications: Notification[];
  
  // Filters and search
  taskFilters: {
    status: string[];
    taskType: string[];
    dateRange: [Date | null, Date | null];
    search: string;
  };
  
  // Views
  currentView: string;
  viewPreferences: Record<string, any>;
}

interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
  action?: {
    label: string;
    onClick: () => void;
  };
}

interface UIActions {
  // Dashboard
  setDashboardMode: (mode: keyof DashboardMode) => void;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  
  // Modals
  openModal: (modal: keyof UIState['modals']) => void;
  closeModal: (modal: keyof UIState['modals']) => void;
  closeAllModals: () => void;
  
  // Loading
  setGlobalLoading: (loading: boolean) => void;
  setLoadingState: (key: string, loading: boolean) => void;
  
  // Theme
  setTheme: (theme: 'dark' | 'light') => void;
  toggleTheme: () => void;
  
  // Notifications
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => void;
  removeNotification: (id: string) => void;
  markNotificationRead: (id: string) => void;
  clearNotifications: () => void;
  
  // Filters
  setTaskFilters: (filters: Partial<UIState['taskFilters']>) => void;
  resetTaskFilters: () => void;
  
  // Views
  setCurrentView: (view: string) => void;
  setViewPreference: (view: string, preferences: any) => void;
  
  // Utility
  reset: () => void;
}

type UIStore = UIState & UIActions;

const initialTaskFilters = {
  status: [],
  taskType: [],
  dateRange: [null, null] as [Date | null, Date | null],
  search: '',
};

const initialState: UIState = {
  dashboardMode: 'evaluator',
  sidebarCollapsed: false,
  modals: {
    taskCreation: false,
    userProfile: false,
    settings: false,
    help: false,
  },
  globalLoading: false,
  loadingStates: {},
  theme: 'dark',
  notifications: [],
  taskFilters: initialTaskFilters,
  currentView: 'dashboard',
  viewPreferences: {},
};

export const useUIStore = create<UIStore>((set, get) => ({
  ...initialState,

  // Dashboard
  setDashboardMode: (mode) => set({ dashboardMode: mode }),
  
  toggleSidebar: () => {
    const state = get();
    set({ sidebarCollapsed: !state.sidebarCollapsed });
  },
  
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),

  // Modals
  openModal: (modal) => {
    const state = get();
    set({
      modals: { ...state.modals, [modal]: true },
    });
  },
  
  closeModal: (modal) => {
    const state = get();
    set({
      modals: { ...state.modals, [modal]: false },
    });
  },
  
  closeAllModals: () => {
    set({
      modals: {
        taskCreation: false,
        userProfile: false,
        settings: false,
        help: false,
      },
    });
  },

  // Loading
  setGlobalLoading: (loading) => set({ globalLoading: loading }),
  
  setLoadingState: (key, loading) => {
    const state = get();
    set({
      loadingStates: { ...state.loadingStates, [key]: loading },
    });
  },

  // Theme
  setTheme: (theme) => {
    set({ theme });
    if (typeof document !== 'undefined') {
      document.documentElement.classList.toggle('dark', theme === 'dark');
    }
  },
  
  toggleTheme: () => {
    const state = get();
    const newTheme = state.theme === 'dark' ? 'light' : 'dark';
    get().setTheme(newTheme);
  },

  // Notifications
  addNotification: (notification) => {
    const state = get();
    const newNotification: Notification = {
      ...notification,
      id: Date.now().toString() + Math.random().toString(36),
      timestamp: new Date(),
      read: false,
    };
    
    set({
      notifications: [newNotification, ...state.notifications.slice(0, 49)], // Keep max 50
    });
  },
  
  removeNotification: (id) => {
    const state = get();
    set({
      notifications: state.notifications.filter(n => n.id !== id),
    });
  },
  
  markNotificationRead: (id) => {
    const state = get();
    set({
      notifications: state.notifications.map(n =>
        n.id === id ? { ...n, read: true } : n
      ),
    });
  },
  
  clearNotifications: () => set({ notifications: [] }),

  // Filters
  setTaskFilters: (filters) => {
    const state = get();
    set({
      taskFilters: { ...state.taskFilters, ...filters },
    });
  },
  
  resetTaskFilters: () => set({ taskFilters: initialTaskFilters }),

  // Views
  setCurrentView: (view) => set({ currentView: view }),
  
  setViewPreference: (view, preferences) => {
    const state = get();
    set({
      viewPreferences: {
        ...state.viewPreferences,
        [view]: { ...state.viewPreferences[view], ...preferences },
      },
    });
  },

  // Utility
  reset: () => set(initialState),
}));

// Helper to get dashboard mode configuration
export const getDashboardModeConfig = (role: UserRole): keyof DashboardMode => {
  switch (role) {
    case UserRole.ADMIN:
      return 'admin';
    case UserRole.EVALUATOR:
      return 'evaluator';
    default:
      return 'viewer';
  }
};

// Auto-sync with localStorage for theme
if (typeof window !== 'undefined') {
  const savedTheme = localStorage.getItem('theme') as 'dark' | 'light' | null;
  if (savedTheme) {
    useUIStore.getState().setTheme(savedTheme);
  }
  
  useUIStore.subscribe(
    (state) => state.theme,
    (theme) => {
      localStorage.setItem('theme', theme);
    }
  );
}