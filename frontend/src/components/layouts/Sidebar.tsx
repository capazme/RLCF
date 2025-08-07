import { motion } from 'framer-motion';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  ClipboardCheck, 
  BarChart3, 
  Settings, 
  User, 
  ChevronLeft, 
  Trophy,
  Shield,
  Zap
} from 'lucide-react';
import { useUIStore } from '../../app/store/ui';
import { useAuthStore } from '../../app/store/auth';
import { cn } from '../../lib/utils';
import { UserRole } from '../../types/index';

const navigationItems = [
  {
    label: 'Dashboard',
    icon: LayoutDashboard,
    href: '/dashboard',
    roles: [UserRole.ADMIN, UserRole.EVALUATOR, UserRole.VIEWER]
  },
  {
    label: 'Evaluation',
    icon: ClipboardCheck,
    href: '/evaluation',
    roles: [UserRole.ADMIN, UserRole.EVALUATOR]
  },
  {
    label: 'Analytics',
    icon: BarChart3,
    href: '/analytics',
    roles: [UserRole.ADMIN, UserRole.EVALUATOR, UserRole.VIEWER]
  },
  {
    label: 'Leaderboard',
    icon: Trophy,
    href: '/analytics/leaderboard',
    roles: [UserRole.ADMIN, UserRole.EVALUATOR, UserRole.VIEWER]
  },
  {
    label: 'Settings',
    icon: Settings,
    href: '/admin/settings',
    roles: [UserRole.ADMIN]
  },
  {
    label: 'Profile',
    icon: User,
    href: '/profile',
    roles: [UserRole.ADMIN, UserRole.EVALUATOR, UserRole.VIEWER]
  },
];

export function Sidebar() {
  const { sidebarCollapsed, toggleSidebar } = useUIStore();
  const { user, role } = useAuthStore();

  const filteredNavigation = navigationItems.filter(item => 
    item.roles.includes(role)
  );

  const getRoleIcon = (role: UserRole) => {
    switch (role) {
      case UserRole.ADMIN:
        return <Shield className="h-4 w-4 text-red-400" />;
      case UserRole.EVALUATOR:
        return <Zap className="h-4 w-4 text-violet-400" />;
      default:
        return <User className="h-4 w-4 text-slate-400" />;
    }
  };

  return (
    <motion.div
      className="fixed left-0 top-0 z-40 h-full bg-slate-900 border-r border-slate-800"
      animate={{ width: sidebarCollapsed ? 64 : 256 }}
      transition={{ duration: 0.3, ease: 'easeInOut' }}
    >
      {/* Header */}
      <div className="flex h-16 items-center justify-between border-b border-slate-800 px-4">
        {!sidebarCollapsed && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex items-center space-x-2"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-violet-600 to-purple-600">
              <span className="text-lg font-bold text-white">⚖️</span>
            </div>
            <div>
              <h1 className="text-lg font-bold text-white">RLCF</h1>
              <p className="text-xs text-slate-400">Legal AI Framework</p>
            </div>
          </motion.div>
        )}
        
        <button
          onClick={toggleSidebar}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-slate-800 hover:text-slate-200"
        >
          <ChevronLeft 
            className={cn(
              'h-4 w-4 transition-transform duration-300',
              sidebarCollapsed && 'rotate-180'
            )}
          />
        </button>
      </div>

      {/* User Info */}
      {user && (
        <div className="border-b border-slate-800 p-4">
          <div className="flex items-center space-x-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-violet-500 to-purple-600 text-white font-semibold">
              {user.username.charAt(0).toUpperCase()}
            </div>
            
            {!sidebarCollapsed && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="min-w-0 flex-1"
              >
                <div className="flex items-center gap-2">
                  <p className="truncate text-sm font-medium text-white">
                    {user.username}
                  </p>
                  {getRoleIcon(role)}
                </div>
                <p className="truncate text-xs text-slate-400">{user.email}</p>
                <div className="mt-1 flex items-center gap-1 text-xs text-violet-400">
                  <span>Authority: {(user.authority_score || 0).toFixed(2)}</span>
                </div>
              </motion.div>
            )}
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 p-4">
        <div className="space-y-2">
          {filteredNavigation.map((item) => {
            const Icon = item.icon;
            
            return (
              <NavLink
                key={item.href}
                to={item.href}
                className={({ isActive }) =>
                  cn(
                    'flex items-center rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200',
                    isActive
                      ? 'bg-violet-600/20 text-violet-300 border-r-2 border-violet-500'
                      : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200',
                    sidebarCollapsed && 'justify-center px-2'
                  )
                }
              >
                <Icon className="h-5 w-5 flex-shrink-0" />
                {!sidebarCollapsed && (
                  <motion.span
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -10 }}
                    className="ml-3"
                  >
                    {item.label}
                  </motion.span>
                )}
              </NavLink>
            );
          })}
        </div>
      </nav>

      {/* Footer */}
      <div className="border-t border-slate-800 p-4">
        {!sidebarCollapsed && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="text-center"
          >
            <p className="text-xs text-slate-500">
              RLCF Framework v1.0
            </p>
            <p className="text-xs text-slate-600">
              Legal AI Research
            </p>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}