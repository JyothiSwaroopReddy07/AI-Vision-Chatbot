'use client'

import { useState, useEffect } from 'react'
import ChatInterface from '@/components/ChatInterface'
import LoginForm from '@/components/LoginForm'
import { useAuthStore } from '@/lib/store'

export default function Home() {
  const { isAuthenticated, checkAuth } = useAuthStore()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    checkAuth()
    setLoading(false)
  }, [checkAuth])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
        <div className="text-center">
          <div className="relative mb-8">
            <div className="w-24 h-24 mx-auto rounded-3xl bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center shadow-2xl animate-pulse">
              <span className="text-5xl">👁️</span>
            </div>
            <div className="absolute inset-0 w-24 h-24 mx-auto rounded-3xl bg-gradient-to-br from-blue-600 to-indigo-600 animate-ping opacity-20"></div>
          </div>
          <h2 className="text-2xl font-bold gradient-text mb-3">Vision AI</h2>
          <div className="flex items-center justify-center gap-2">
            <div className="loading-dot"></div>
            <div className="loading-dot"></div>
            <div className="loading-dot"></div>
          </div>
          <p className="mt-4 text-gray-600">Initializing research assistant...</p>
        </div>
      </div>
    )
  }

  return (
    <main className="min-h-screen">
      {isAuthenticated ? <ChatInterface /> : <LoginForm />}
    </main>
  )
}
