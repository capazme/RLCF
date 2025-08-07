import { useEffect } from 'react';
import { QueryProvider } from './query-provider';
import { useAuthStore } from '../store/auth';
import { useUIStore } from '../store/ui';

interface AppProviderProps {
  children: React.ReactNode;
}

export function AppProvider({ children }: AppProviderProps) {
  const { refreshUser } = useAuthStore();
  const { setTheme } = useUIStore();

  useEffect(() => {
    // Initialize auth state
    refreshUser();
    
    // Initialize theme
    const savedTheme = localStorage.getItem('theme') as 'dark' | 'light' | null;
    if (savedTheme) {
      setTheme(savedTheme);
    } else {
      // Default to dark theme for legal app aesthetic
      setTheme('dark');
    }
    
    // Set up global error handler
    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      console.error('Unhandled promise rejection:', event.reason);
    };
    
    window.addEventListener('unhandledrejection', handleUnhandledRejection);
    
    return () => {
      window.removeEventListener('unhandledrejection', handleUnhandledRejection);
    };
  }, [refreshUser, setTheme]);

  return (
    <QueryProvider>
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
        {children}
      </div>
    </QueryProvider>
  );
}