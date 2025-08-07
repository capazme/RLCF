import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { User } from '../../types/index';
import { UserRole } from '../../types/index';
import { apiClient } from '../../lib/api';

interface AuthState {
  user: User | null;
  token: string | null;
  role: UserRole;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

interface AuthActions {
  login: (credentials: { email: string; password: string }) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  updateUser: (updates: Partial<User>) => void;
  clearError: () => void;
  setRole: (role: UserRole) => void;
}

type AuthStore = AuthState & AuthActions;

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      token: null,
      role: UserRole.VIEWER,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // Actions
      login: async (credentials) => {
        set({ isLoading: true, error: null });
        
        try {
          // Mock authentication since RLCF backend doesn't have auth endpoints yet
          await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate network delay
          
          // Create mock user based on credentials
          let mockUser: User;
          let role: UserRole;
          
          if (credentials.email === 'admin@rlcf.ai' && credentials.password === 'admin123') {
            mockUser = {
              id: 1,
              username: 'admin',
              email: 'admin@rlcf.ai',
              authority_score: 0.95,
              track_record_score: 0.9,
              baseline_credential_score: 0.8
            };
            role = UserRole.ADMIN;
          } else if (credentials.email === 'evaluator@rlcf.ai' && credentials.password === 'eval123') {
            mockUser = {
              id: 2,
              username: 'evaluator',
              email: 'evaluator@rlcf.ai',
              authority_score: 0.75,
              track_record_score: 0.7,
              baseline_credential_score: 0.6
            };
            role = UserRole.EVALUATOR;
          } else if (credentials.email === 'viewer@rlcf.ai' && credentials.password === 'view123') {
            mockUser = {
              id: 3,
              username: 'viewer',
              email: 'viewer@rlcf.ai',
              authority_score: 0.3,
              track_record_score: 0.2,
              baseline_credential_score: 0.1
            };
            role = UserRole.VIEWER;
          } else {
            throw new Error('Invalid credentials');
          }
          
          const token = 'supersecretkey'; // Use RLCF API key
          localStorage.setItem('auth_token', token);
          
          set({
            user: mockUser,
            token,
            isAuthenticated: true,
            isLoading: false,
            error: null,
            role,
          });
        } catch (error: any) {
          const errorMessage = error?.message || 'Login failed';
          set({
            isLoading: false,
            error: errorMessage,
            isAuthenticated: false,
            user: null,
            token: null,
          });
          throw error;
        }
      },

      logout: () => {
        localStorage.removeItem('auth_token');
        
        set({
          user: null,
          token: null,
          isAuthenticated: false,
          role: UserRole.VIEWER,
          error: null,
        });
      },

      refreshUser: async () => {
        const token = localStorage.getItem('auth_token');
        if (!token || token !== 'supersecretkey') {
          get().logout();
          return;
        }

        // For now, just keep the user logged in if token exists
        // In a real implementation, we'd verify the token with the backend
        if (!get().user) {
          // If no user in state but valid token, restore default admin user
          set({
            user: {
              id: 1,
              username: 'admin',
              email: 'admin@rlcf.ai',
              authority_score: 0.95,
              track_record_score: 0.9,
              baseline_credential_score: 0.8
            },
            token,
            isAuthenticated: true,
            isLoading: false,
            role: UserRole.ADMIN,
          });
        }
      },

      updateUser: (updates) => {
        const currentUser = get().user;
        if (currentUser) {
          const updatedUser = { ...currentUser, ...updates };
          set({ 
            user: updatedUser,
            role: determineUserRole(updatedUser),
          });
        }
      },

      clearError: () => set({ error: null }),

      setRole: (role) => set({ role }),
    }),
    {
      name: 'auth-store',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        token: state.token,
        role: state.role,
      }),
    }
  )
);

// Helper function to determine user role based on authority score and credentials
function determineUserRole(user: User): UserRole {
  // This is a simplified role determination - adjust based on your needs
  if (user.credentials?.admin === true) {
    return UserRole.ADMIN;
  }
  
  if (user.authority_score > 0.7) {
    return UserRole.EVALUATOR;
  }
  
  return UserRole.VIEWER;
}

// Initialize auth state on app load
export const initializeAuth = () => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    useAuthStore.getState().refreshUser();
  }
};