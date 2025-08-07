import { RouterProvider } from 'react-router-dom';
import { Toaster } from 'sonner';
import { AppProvider } from './app/providers/app-provider';
import { router } from './app/routes';

function App() {
  return (
    <AppProvider>
      <RouterProvider router={router} />
      <Toaster 
        theme="dark"
        position="top-right"
        toastOptions={{
          style: {
            background: 'rgb(30 41 59)',
            border: '1px solid rgb(71 85 105)',
            color: 'rgb(248 250 252)',
          },
        }}
      />
    </AppProvider>
  );
}

export default App;
