import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { ProtectedRoute } from '@/components/ProtectedRoute'
import { EmptyChatState } from '@/components/chat/EmptyChatState'
import { AppLayout } from '@/components/layout/AppLayout'
import { AuthProvider } from '@/lib/auth'
import { ThreadsProvider } from '@/lib/threads'
import { LoginPage } from '@/pages/LoginPage'
import { ChatPage } from '@/pages/chat/ChatPage'

export default function App() {
  return (
    <AuthProvider>
      <ThreadsProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              element={
                <ProtectedRoute>
                  <AppLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<EmptyChatState />} />
              <Route path="/thread/:threadId" element={<ChatPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </ThreadsProvider>
    </AuthProvider>
  )
}