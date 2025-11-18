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

interface Citation {
  source_type: string
  source_id: string
  title: string
  authors?: string
  journal?: string
  url?: string
  excerpt?: string
  relevance_score?: number
}

interface SpellCorrection {
  original: string
  corrected: string
  type: string
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  timestamp: string
  is_starred?: boolean
  spell_corrections?: SpellCorrection[]
  original_query?: string
}

interface ChatSession {
  id: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
  is_archived?: boolean
}

interface ChatState {
  messages: Message[]
  sessionId: string | null
  isLoading: boolean
  sessions: ChatSession[]
  searchQuery: string
  dateFilter: { start: string | null; end: string | null }
  addMessage: (message: Message) => void
  setMessages: (messages: Message[]) => void
  setSessionId: (id: string | null) => void
  setLoading: (loading: boolean) => void
  clearMessages: () => void
  setSessions: (sessions: ChatSession[]) => void
  setSearchQuery: (query: string) => void
  setDateFilter: (start: string | null, end: string | null) => void
  updateMessageStarStatus: (messageId: string, isStarred: boolean) => void
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  sessionId: typeof window !== 'undefined' ? localStorage.getItem('sessionId') : null,
  isLoading: false,
  sessions: [],
  searchQuery: '',
  dateFilter: { start: null, end: null },

  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message]
  })),

  setMessages: (messages) => set({ messages }),

  setSessionId: (id) => {
    if (typeof window !== 'undefined') {
      if (id) {
        localStorage.setItem('sessionId', id)
      } else {
        localStorage.removeItem('sessionId')
      }
    }
    set({ sessionId: id })
  },

  setLoading: (loading) => set({ isLoading: loading }),

  clearMessages: () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('sessionId')
    }
    set({ messages: [], sessionId: null })
  },

  setSessions: (sessions) => set({ sessions }),

  setSearchQuery: (query) => set({ searchQuery: query }),

  setDateFilter: (start, end) => set({ dateFilter: { start, end } }),

  updateMessageStarStatus: (messageId, isStarred) => set((state) => ({
    messages: state.messages.map(msg =>
      msg.id === messageId ? { ...msg, is_starred: isStarred } : msg
    )
  })),
}))

// Bookmark store
interface BookmarkFolder {
  id: string
  name: string
  description?: string
  color: string
  icon: string
  created_at: string
  updated_at: string
  bookmark_count?: number
}

interface BookmarkState {
  folders: BookmarkFolder[]
  selectedFolderId: string | null
  isLoading: boolean
  setFolders: (folders: BookmarkFolder[]) => void
  addFolder: (folder: BookmarkFolder) => void
  updateFolder: (id: string, updates: Partial<BookmarkFolder>) => void
  deleteFolder: (id: string) => void
  setSelectedFolder: (id: string | null) => void
  setLoading: (loading: boolean) => void
}

export const useBookmarkStore = create<BookmarkState>((set) => ({
  folders: [],
  selectedFolderId: null,
  isLoading: false,

  setFolders: (folders) => set({ folders }),

  addFolder: (folder) => set((state) => ({
    folders: [...state.folders, folder]
  })),

  updateFolder: (id, updates) => set((state) => ({
    folders: state.folders.map(f => f.id === id ? { ...f, ...updates } : f)
  })),

  deleteFolder: (id) => set((state) => ({
    folders: state.folders.filter(f => f.id !== id),
    selectedFolderId: state.selectedFolderId === id ? null : state.selectedFolderId
  })),

  setSelectedFolder: (id) => set({ selectedFolderId: id }),

  setLoading: (loading) => set({ isLoading: loading }),
}))

// Starred messages store
interface StarredMessage {
  id: string
  message_id: string
  session_id: string
  session_title: string
  question: string | null
  answer: string
  notes?: string
  tags: string[]
  starred_at: string
  updated_at: string
}

interface StarredState {
  starredMessages: StarredMessage[]
  isLoading: boolean
  searchQuery: string
  setStarredMessages: (messages: StarredMessage[]) => void
  addStarredMessage: (message: StarredMessage) => void
  removeStarredMessage: (messageId: string) => void
  updateStarredMessage: (id: string, updates: Partial<StarredMessage>) => void
  setLoading: (loading: boolean) => void
  setSearchQuery: (query: string) => void
}

export const useStarredStore = create<StarredState>((set) => ({
  starredMessages: [],
  isLoading: false,
  searchQuery: '',

  setStarredMessages: (messages) => set({ starredMessages: messages }),

  addStarredMessage: (message) => set((state) => ({
    starredMessages: [message, ...state.starredMessages]
  })),

  removeStarredMessage: (messageId) => set((state) => ({
    starredMessages: state.starredMessages.filter(m => m.message_id !== messageId)
  })),

  updateStarredMessage: (id, updates) => set((state) => ({
    starredMessages: state.starredMessages.map(m =>
      m.id === id ? { ...m, ...updates } : m
    )
  })),

  setLoading: (loading) => set({ isLoading: loading }),

  setSearchQuery: (query) => set({ searchQuery: query }),
}))

// MSigDB store
interface GeneSetResult {
  gene_set_id: string
  gene_set_name: string
  collection: string
  sub_collection: string | null
  description: string | null
  species: string
  gene_set_size: number
  overlap_count: number
  overlap_percentage: number
  p_value: number
  adjusted_p_value: number
  odds_ratio: number
  matched_genes: string[]
  all_genes?: string[]  // All genes in the gene set
  msigdb_url: string | null
  external_url: string | null
  rank: number
  match_type?: string
}

interface MSigDBState {
  searchType: 'none' | 'pubmed' | 'msigdb'
  currentResults: GeneSetResult[] | null
  selectedGeneSet: GeneSetResult | null
  showResultsPanel: boolean
  isLoading: boolean
  queryGenes: string[]
  species: string
  numResults: number
  setSearchType: (type: 'none' | 'pubmed' | 'msigdb') => void
  setResults: (results: GeneSetResult[] | null, genes?: string[], species?: string, numResults?: number) => void
  setSelectedGeneSet: (geneSet: GeneSetResult | null) => void
  setShowResultsPanel: (show: boolean) => void
  setLoading: (loading: boolean) => void
  clearResults: () => void
}

export const useMSigDBStore = create<MSigDBState>((set) => ({
  searchType: 'none',
  currentResults: null,
  selectedGeneSet: null,
  showResultsPanel: false,
  isLoading: false,
  queryGenes: [],
  species: 'auto',
  numResults: 0,

  setSearchType: (type) => set({ searchType: type }),

  setResults: (results, genes = [], species = 'auto', numResults = 0) => set({
    currentResults: results ? [...results] : null, // Create new array reference
    queryGenes: [...genes], // Create new array reference
    species,
    numResults,
    showResultsPanel: results !== null && results.length > 0,
    isLoading: false  // Turn off loading when results are set
  }),

  setSelectedGeneSet: (geneSet) => set({ selectedGeneSet: geneSet }),

  setShowResultsPanel: (show) => set({ showResultsPanel: show }),

  setLoading: (loading) => set({ isLoading: loading }),

  clearResults: () => set({
    currentResults: null,
    selectedGeneSet: null,
    showResultsPanel: false,
    queryGenes: [],
    numResults: 0
  }),
}))

