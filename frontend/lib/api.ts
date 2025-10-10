import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/'
    }
    return Promise.reject(error)
  }
)

// Authentication API
export const authAPI = {
  login: async (email: string, password: string) => {
    const response = await api.post('/auth/login', { email, password })
    return response.data
  },

  register: async (email: string, password: string, username: string, fullName: string) => {
    const response = await api.post('/auth/register', {
      email,
      password,
      username,
      full_name: fullName,
    })
    return response.data
  },

  logout: async () => {
    const response = await api.post('/auth/logout')
    return response.data
  },

  refreshToken: async (refreshToken: string) => {
    const response = await api.post('/auth/refresh', { refresh_token: refreshToken })
    return response.data
  },
}

export const chatApi = {
  sendMessage: async (message: string, sessionId?: string) => {
    return api.post('/chat/message', {
      message,
      session_id: sessionId,
    })
  },

  getSessions: async () => {
    return api.get('/chat/sessions')
  },

  getHistory: async (sessionId: string) => {
    return api.get(`/chat/history/${sessionId}`)
  },

  deleteSession: async (sessionId: string) => {
    return api.delete(`/chat/history/${sessionId}`)
  },
}

export const pathwayApi = {
  analyzeGenes: async (genes: string[]) => {
    return api.post('/pathway/analyze', { genes })
  },

  getResults: async (jobId: string) => {
    return api.get(`/pathway/results/${jobId}`)
  },
}

export const uploadApi = {
  uploadFile: async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    
    return api.post('/upload/file', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },

  uploadImage: async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    
    return api.post('/upload/image', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },
}

// Backward compatibility exports
export const chatAPI = chatApi

