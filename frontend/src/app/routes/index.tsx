import { createBrowserRouter, Navigate } from 'react-router-dom';
import { Layout } from '../../components/layouts/Layout';
import { AuthGuard } from '../../components/shared/AuthGuard';
import { Dashboard } from '../../features/dashboard/Dashboard';
import { TaskEvaluation } from '../../features/evaluation/TaskEvaluation';
import { Analytics } from '../../features/analytics/Analytics';
import { Settings } from '../../features/admin/Settings';
import { UserProfile } from '../../features/auth/UserProfile';
import { Login } from '../../features/auth/Login';
import { TaskDetails } from '../../features/tasks/TaskDetails';
import { Leaderboard } from '../../features/analytics/Leaderboard';

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <Login />,
  },
  {
    path: '/',
    element: (
      <AuthGuard>
        <Layout />
      </AuthGuard>
    ),
    children: [
      {
        index: true,
        element: <Navigate to="/dashboard" replace />,
      },
      {
        path: 'dashboard',
        element: <Dashboard />,
      },
      {
        path: 'evaluation',
        children: [
          {
            index: true,
            element: <TaskEvaluation />,
          },
          {
            path: 'task/:taskId',
            element: <TaskDetails />,
          },
        ],
      },
      {
        path: 'analytics',
        children: [
          {
            index: true,
            element: <Analytics />,
          },
          {
            path: 'leaderboard',
            element: <Leaderboard />,
          },
        ],
      },
      {
        path: 'admin',
        children: [
          {
            path: 'settings',
            element: (
              <AuthGuard requiredRole="admin">
                <Settings />
              </AuthGuard>
            ),
          },
        ],
      },
      {
        path: 'profile',
        element: <UserProfile />,
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/dashboard" replace />,
  },
]);