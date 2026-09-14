import { createBrowserRouter } from 'react-router'
import { GuestOnly, RequireAuth } from './components/auth/RouteGuards.tsx'
import { Layout } from './components/Layout.tsx'
import { AccountPage } from './pages/AccountPage.tsx'
import { HistoryPage } from './pages/HistoryPage.tsx'
import { HomePage } from './pages/HomePage.tsx'
import { ScanPage } from './pages/ScanPage.tsx'
import { LoginPage } from './pages/LoginPage.tsx'
import { NotFoundPage } from './pages/NotFoundPage.tsx'
import { SignupPage } from './pages/SignupPage.tsx'

export const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { index: true, element: <HomePage /> },
      {
        path: 'login',
        element: (
          <GuestOnly>
            <LoginPage />
          </GuestOnly>
        ),
      },
      {
        path: 'signup',
        element: (
          <GuestOnly>
            <SignupPage />
          </GuestOnly>
        ),
      },
      {
        path: 'account',
        element: (
          <RequireAuth>
            <AccountPage />
          </RequireAuth>
        ),
      },
      {
        path: 'history',
        element: (
          <RequireAuth>
            <HistoryPage />
          </RequireAuth>
        ),
      },
      {
        path: 'history/:scanId',
        element: (
          <RequireAuth>
            <ScanPage />
          </RequireAuth>
        ),
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
