import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../../app/store/auth';
import { UserRole } from '../../types/index';

interface AuthGuardProps {
  children: React.ReactNode;
  requiredRole?: UserRole | UserRole[];
}

export function AuthGuard({ children, requiredRole }: AuthGuardProps) {
  const { isAuthenticated, user, role } = useAuthStore();

  // Not authenticated
  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }

  // Check role requirements
  if (requiredRole) {
    const requiredRoles = Array.isArray(requiredRole) ? requiredRole : [requiredRole];
    
    if (!requiredRoles.includes(role)) {
      return <Navigate to="/dashboard" replace />;
    }
  }

  return <>{children}</>;
}