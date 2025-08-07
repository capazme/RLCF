import { Outlet } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { useUIStore } from '../../app/store/ui';
import { cn } from '../../lib/utils';

export function Layout() {
  const { sidebarCollapsed } = useUIStore();

  return (
    <div className="flex h-screen overflow-hidden bg-slate-950">
      {/* Sidebar */}
      <Sidebar />
      
      {/* Main Content */}
      <div 
        className={cn(
          'flex flex-1 flex-col overflow-hidden transition-all duration-300',
          sidebarCollapsed ? 'ml-16' : 'ml-64'
        )}
      >
        {/* Header */}
        <Header />
        
        {/* Page Content */}
        <motion.main
          className="flex-1 overflow-y-auto bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <div className="mx-auto max-w-7xl">
            <Outlet />
          </div>
        </motion.main>
      </div>
    </div>
  );
}