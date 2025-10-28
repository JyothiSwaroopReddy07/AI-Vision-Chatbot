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
  sendMessage: async (message: string, sessionId?: string, searchType: string = 'pubmed') => {
    return api.post('/chat/message', {
      message,
      session_id: sessionId,
      search_type: searchType,
    })
  },

  getSessions: async (params?: any) => {
    return api.get('/chat/sessions', { params })
  },

  getSession: async (sessionId: string) => {
    return api.get(`/chat/session/${sessionId}`)
  },

  getHistory: async (sessionId: string) => {
    return api.get(`/chat/history/${sessionId}`)
  },

  deleteSession: async (sessionId: string) => {
    return api.delete(`/chat/history/${sessionId}`)
  },
}

// Bookmarks API
export const bookmarksApi = {
  getFolders: async () => {
    return api.get('/bookmarks/folders')
  },

  createFolder: async (name: string, description?: string, color?: string, icon?: string) => {
    return api.post('/bookmarks/folders', { name, description, color, icon })
  },

  updateFolder: async (folderId: string, updates: any) => {
    return api.put(`/bookmarks/folders/${folderId}`, updates)
  },

  deleteFolder: async (folderId: string) => {
    return api.delete(`/bookmarks/folders/${folderId}`)
  },

  addChatToFolder: async (folderId: string, sessionId: string, notes?: string) => {
    return api.post(`/bookmarks/folders/${folderId}/chats`, { session_id: sessionId, notes })
  },

  removeChatFromFolder: async (folderId: string, sessionId: string) => {
    return api.delete(`/bookmarks/folders/${folderId}/chats/${sessionId}`)
  },

  getFolderChats: async (folderId: string, limit = 50, offset = 0) => {
    return api.get(`/bookmarks/folders/${folderId}/chats`, { params: { limit, offset } })
  },

  getSessionFolders: async (sessionId: string) => {
    return api.get(`/bookmarks/sessions/${sessionId}/folders`)
  },
}

// Starred messages API
export const starredApi = {
  starMessage: async (messageId: string, notes?: string, tags?: string) => {
    return api.post('/starred/star', { message_id: messageId, notes, tags })
  },

  unstarMessage: async (messageId: string) => {
    return api.delete(`/starred/star/${messageId}`)
  },

  getStarStatus: async (messageId: string) => {
    return api.get(`/starred/star/${messageId}/status`)
  },

  getStarredMessages: async (tag?: string, limit = 100, offset = 0) => {
    return api.get('/starred/starred', { params: { tag, limit, offset } })
  },

  updateStarredMessage: async (starredId: string, notes?: string, tags?: string) => {
    return api.put(`/starred/starred/${starredId}`, { notes, tags })
  },

  searchStarredMessages: async (query: string, limit = 50) => {
    return api.get('/starred/starred/search', { params: { query, limit } })
  },

  getStarredCount: async () => {
    return api.get('/starred/starred/count')
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

// MSigDB API
export const msigdbAPI = {
  search: async (
    query: string,
    species: string = 'auto',
    searchType: string = 'exact',
    collections: string[] | null = null
  ) => {
    return api.post('/msigdb/search', {
      query,
      species,
      search_type: searchType,
      collections,
    })
  },

  getGeneSet: async (geneSetName: string, species: string = 'human') => {
    return api.get(`/msigdb/gene-set/${geneSetName}`, {
      params: { species },
    })
  },

  getCollections: async () => {
    return api.get('/msigdb/collections')
  },

  getHistory: async (limit: number = 50) => {
    return api.get('/msigdb/history', {
      params: { limit },
    })
  },
}

// Backward compatibility exports
export const chatAPI = chatApi

