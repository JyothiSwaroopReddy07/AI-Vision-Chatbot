import { create } from 'zustand'
import { api } from './api'

interface User {
  id: string
  email: string
  username: string
}

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, username: string, password: string, fullName?: string) => Promise<void>
  logout: () => void
  checkAuth: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isAuthenticated: false,

  login: async (email: string, password: string) => {
    const response = await api.post('/auth/login', { email, password })
    const { access_token, user_id, username } = response.data
    
    localStorage.setItem('token', access_token)
    localStorage.setItem('user', JSON.stringify({ id: user_id, email, username }))
    
    set({
      token: access_token,
      user: { id: user_id, email, username },
      isAuthenticated: true,
    })
  },

  register: async (email: string, username: string, password: string, fullName?: string) => {
    const response = await api.post('/auth/register', {
      email,
      username,
      password,
      full_name: fullName,
    })
    const { access_token, user_id } = response.data
    
    localStorage.setItem('token', access_token)
    localStorage.setItem('user', JSON.stringify({ id: user_id, email, username }))
    
    set({
      token: access_token,
      user: { id: user_id, email, username },
      isAuthenticated: true,
    })
  },

  logout: () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    
    set({
      token: null,
      user: null,
      isAuthenticated: false,
    })
  },

  checkAuth: () => {
    const token = localStorage.getItem('token')
    const userStr = localStorage.getItem('user')
    
    if (token && userStr) {
      const user = JSON.parse(userStr)
      set({
        token,
        user,
        isAuthenticated: true,
      })
    } else {
      set({
        token: null,
        user: null,
        isAuthenticated: false,
      })
    }
  },
}))

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: any[]
  timestamp: string
}

interface ChatState {
  messages: Message[]
  sessionId: string | null
  isLoading: boolean
  addMessage: (message: Message) => void
  setMessages: (messages: Message[]) => void
  setSessionId: (id: string | null) => void
  setLoading: (loading: boolean) => void
  clearMessages: () => void
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  sessionId: null,
  isLoading: false,

  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message]
  })),

  setMessages: (messages) => set({ messages }),

  setSessionId: (id) => set({ sessionId: id }),

  setLoading: (loading) => set({ isLoading: loading }),

  clearMessages: () => set({ messages: [], sessionId: null }),
}))

