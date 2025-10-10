# Vision ChatBot Agent - Project Summary

## 🎯 Project Overview

**Vision ChatBot Agent** is a comprehensive AI-powered platform designed specifically for vision domain research. It enables researchers to interact with scientific literature, analyze gene sets, and access pathway information through an intelligent conversational interface.

### Key Features

✅ **RAG-Powered Q&A**: Retrieval-Augmented Generation using PubMed literature
✅ **Multi-Modal Input**: Support for text, PDF, and image (OCR) uploads  
✅ **Pathway Analysis**: Gene set enrichment analysis with KEGG, Reactome, and GO databases
✅ **Citation Tracking**: Every answer includes source references with PubMed links
✅ **Chat History**: Persistent conversation memory across sessions
✅ **Modern UI**: Responsive React-based chat interface
✅ **Scalable Architecture**: Dockerized microservices with async task processing

---

## 📁 Project Structure

```
vision-chatbot-agent/
├── backend/                    # FastAPI backend application
│   ├── app/
│   │   ├── api/               # API endpoints (auth, chat, upload, pathway, pubmed, user)
│   │   ├── core/              # Core configs (database, security, redis)
│   │   ├── models/            # SQLAlchemy database models
│   │   ├── services/          # Business logic services
│   │   ├── rag/               # RAG pipeline (LangChain, ChromaDB)
│   │   ├── tasks/             # Celery async tasks
│   │   └── main.py            # FastAPI application entry point
│   ├── alembic/               # Database migrations
│   ├── requirements.txt       # Python dependencies
│   └── Dockerfile             # Backend container configuration
│
├── frontend/                   # Next.js frontend application
│   ├── app/                   # Next.js app directory
│   ├── components/            # React components (Chat, Login, etc.)
│   ├── lib/                   # Utilities (API client, state management)
│   ├── package.json           # Node dependencies
│   └── Dockerfile             # Frontend container configuration
│
├── nginx/                      # Nginx reverse proxy
│   └── nginx.conf             # Nginx configuration
│
├── monitoring/                 # Monitoring stack
│   └── prometheus.yml         # Prometheus configuration
│
├── data/                       # Persistent data volumes
│   ├── uploads/               # User uploaded files
│   ├── pubmed_pdfs/          # Downloaded PubMed articles
│   ├── chromadb/             # Vector database storage
│   └── logs/                  # Application logs
│
├── docker-compose.yml         # Docker orchestration
├── .env.example               # Environment variables template
├── README.md                  # User documentation
├── ARCHITECTURE.md            # System architecture documentation
├── DEPLOYMENT.md              # Deployment guide
└── PROJECT_SUMMARY.md         # This file
```

---

## 🏗️ Architecture Overview

### Technology Stack

**Backend:**
- **Framework**: FastAPI 0.104+
- **Language**: Python 3.10+
- **AI/ML**: LangChain, OpenAI/Local LLMs, Sentence Transformers
- **Databases**: PostgreSQL (relational), ChromaDB (vector), Redis (cache)
- **Task Queue**: Celery with Redis broker
- **Bioinformatics**: GSEApy, Biopython, NetworkX

**Frontend:**
- **Framework**: Next.js 14+ with React 18+
- **State Management**: Zustand
- **Styling**: Tailwind CSS
- **UI Components**: Custom components with Radix UI
- **Markdown**: React Markdown for formatted responses

**Infrastructure:**
- **Containerization**: Docker & Docker Compose
- **Reverse Proxy**: Nginx
- **Monitoring**: Prometheus + Grafana
- **Logging**: Structured JSON logs

### System Components

```
┌─────────────────────────────────────────────────┐
│                   Frontend (Next.js)             │
│  - Chat Interface                                │
│  - File Upload UI                                │
│  - Authentication                                │
└─────────────────────┬───────────────────────────┘
                      │ HTTP/WebSocket
┌─────────────────────▼───────────────────────────┐
│              Nginx (Reverse Proxy)               │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│              Backend (FastAPI)                   │
│  ┌──────────────────────────────────────────┐   │
│  │ API Layer                                 │   │
│  │ - Authentication & Authorization          │   │
│  │ - Chat Endpoints                          │   │
│  │ - File Upload                             │   │
│  │ - Pathway Analysis                        │   │
│  │ - PubMed Indexing                        │   │
│  └──────────────────┬───────────────────────┘   │
│                     │                             │
│  ┌──────────────────▼───────────────────────┐   │
│  │ RAG Pipeline (LangChain)                 │   │
│  │ - Document Processing                     │   │
│  │ - Vector Retrieval                        │   │
│  │ - LLM Generation                          │   │
│  │ - Citation Extraction                     │   │
│  └──────────────────┬───────────────────────┘   │
│                     │                             │
│  ┌──────────────────▼───────────────────────┐   │
│  │ Service Layer                            │   │
│  │ - Chat Service                            │   │
│  │ - PubMed Service                          │   │
│  │ - Pathway Service                         │   │
│  │ - File Service                            │   │
│  │ - User Service                            │   │
│  └───────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
┌───────▼──────┐ ┌───▼────┐ ┌─────▼──────┐
│  PostgreSQL  │ │ ChromaDB│ │   Redis    │
│  (User Data  │ │ (Vector │ │  (Cache &  │
│   Chat Hist) │ │  Store) │ │   Queue)   │
└──────────────┘ └─────────┘ └────────────┘
```

---

## 🚀 Key Features Implementation

### 1. RAG System

**Components:**
- **Document Processor**: Handles PDF, TXT, DOCX, and images (OCR)
- **Embeddings**: Sentence Transformers or OpenAI embeddings
- **Vector Store**: ChromaDB for similarity search
- **Retriever**: Multiple strategies (basic, MMR, hybrid)
- **LLM**: OpenAI GPT-4 or local models (Mistral, Llama)
- **Memory**: Conversation buffer with context management

**Files:**
- `backend/app/rag/embeddings.py` - Embedding management
- `backend/app/rag/vector_store.py` - ChromaDB integration
- `backend/app/rag/document_processor.py` - Document processing
- `backend/app/rag/retriever.py` - Retrieval strategies
- `backend/app/rag/chain.py` - RAG chain implementation

### 2. PubMed Integration

**Features:**
- Automated article search and extraction
- Metadata parsing (title, abstract, authors, journal)
- Full-text PDF download capability
- Batch processing with rate limiting
- Embedding and indexing in vector store

**Files:**
- `backend/app/services/pubmed_service.py` - PubMed API integration
- `backend/app/models/pubmed.py` - Article data model
- `backend/app/api/pubmed.py` - Admin endpoints for indexing

### 3. Pathway Analysis

**Features:**
- Gene set enrichment analysis
- Support for multiple databases (KEGG, Reactome, GO)
- Statistical testing with FDR correction
- Network graph generation
- Interactive visualizations

**Files:**
- `backend/app/services/pathway_service.py` - Pathway analysis logic
- `backend/app/models/pathway.py` - Job data model
- `backend/app/api/pathway.py` - Analysis endpoints

### 4. Multi-Modal Input

**Supported formats:**
- **Text**: Direct input via chat interface
- **PDF**: Automated text extraction and indexing
- **Images**: OCR processing with Tesseract
- **Documents**: DOCX, TXT file support

**Files:**
- `backend/app/services/file_service.py` - File handling
- `backend/app/rag/document_processor.py` - Multi-format processing
- `backend/app/api/upload.py` - Upload endpoints

### 5. Citation System

**Features:**
- Automatic source extraction from retrieved documents
- PubMed citation formatting
- Relevance scoring
- Interactive citation cards in UI
- Direct links to sources

**Files:**
- `backend/app/models/citation.py` - Citation data model
- `backend/app/rag/chain.py` - Citation extraction logic
- `frontend/components/ChatInterface.tsx` - Citation display

### 6. Chat Management

**Features:**
- Session-based conversations
- Message history persistence
- Context-aware responses
- Session archiving and deletion
- Multi-session support per user

**Files:**
- `backend/app/services/chat_service.py` - Chat logic
- `backend/app/models/chat.py` - Session and message models
- `backend/app/api/chat.py` - Chat endpoints

---

## 🔐 Security Features

1. **Authentication**: JWT-based token authentication
2. **Authorization**: Role-based access control (user, admin)
3. **Password Hashing**: Bcrypt with salt
4. **API Rate Limiting**: Configurable per endpoint
5. **CORS**: Configurable allowed origins
6. **Input Validation**: Pydantic models for all inputs
7. **SQL Injection Prevention**: SQLAlchemy ORM
8. **File Upload Validation**: Type and size checks

---

## 📊 Database Schema

### Core Tables

1. **users**: User accounts and profiles
2. **chat_sessions**: Conversation sessions
3. **chat_messages**: Individual messages
4. **citations**: Source references
5. **uploaded_files**: User file uploads
6. **pathway_jobs**: Pathway analysis tasks
7. **pubmed_articles**: Indexed PubMed articles
8. **user_preferences**: User settings

### Relationships

```
users (1) ─── (N) chat_sessions
chat_sessions (1) ─── (N) chat_messages  
chat_messages (1) ─── (N) citations
users (1) ─── (N) uploaded_files
users (1) ─── (N) pathway_jobs
users (1) ─── (1) user_preferences
```

---

## 🛠️ API Endpoints

### Authentication (`/api/v1/auth`)
- `POST /register` - User registration
- `POST /login` - User login

### Chat (`/api/v1/chat`)
- `POST /message` - Send message and get AI response
- `GET /sessions` - List user's chat sessions
- `GET /history/{session_id}` - Get chat history
- `DELETE /history/{session_id}` - Delete session

### Upload (`/api/v1/upload`)
- `POST /file` - Upload document
- `POST /image` - Upload image (OCR)
- `GET /status/{file_id}` - Check processing status
- `GET /files` - List uploaded files

### Pathway (`/api/v1/pathway`)
- `POST /analyze` - Start pathway analysis
- `GET /results/{job_id}` - Get analysis results
- `GET /export/{job_id}` - Export results
- `GET /jobs` - List user's jobs

### PubMed (`/api/v1/pubmed`) [Admin Only]
- `POST /index` - Trigger indexing
- `GET /stats` - Get indexing statistics

### User (`/api/v1/user`)
- `GET /profile` - Get user profile
- `PUT /preferences` - Update preferences

---

## 🎨 Frontend Components

### Main Components

1. **LoginForm** (`components/LoginForm.tsx`)
   - User authentication
   - Registration form
   - Modern gradient design

2. **ChatInterface** (`components/ChatInterface.tsx`)
   - Message display with markdown
   - File upload functionality
   - Citation cards
   - Loading states

3. **Store** (`lib/store.ts`)
   - Zustand state management
   - Auth state
   - Chat state

4. **API Client** (`lib/api.ts`)
   - Axios HTTP client
   - Token management
   - Error handling

---

## 📈 Monitoring & Logging

### Monitoring Stack

1. **Prometheus**: Metrics collection
   - System metrics
   - Application metrics
   - Database metrics

2. **Grafana**: Visualization dashboards
   - Service health
   - Performance metrics
   - Resource usage

### Logging

- Structured JSON logs
- Log rotation configured
- Centralized logging to `/data/logs`
- Different log levels per environment

---

## 🚢 Deployment Options

### Docker Deployment (Recommended)

```bash
# Clone and setup
git clone https://github.com/yourusername/vision-chatbot-agent.git
cd vision-chatbot-agent
cp .env.example .env

# Configure environment
nano .env

# Deploy
docker-compose up -d
```

### Manual Deployment

See `DEPLOYMENT.md` for detailed manual installation instructions.

---

## 📦 Dependencies

### Backend (Python)

**Core:**
- fastapi 0.104.1
- uvicorn 0.24.0
- sqlalchemy 2.0.23
- alembic 1.12.1

**AI/ML:**
- langchain 0.1.0
- openai 1.6.1
- sentence-transformers 2.2.2
- chromadb 0.4.18

**Bioinformatics:**
- gseapy 1.1.2
- biopython 1.81
- networkx 3.2.1

**Document Processing:**
- pypdf2 3.0.1
- python-docx 1.1.0
- pytesseract 0.3.10

### Frontend (Node.js)

**Core:**
- next 14.0.4
- react 18.2.0
- typescript 5.3.3

**UI:**
- tailwindcss 3.3.6
- lucide-react 0.294.0
- react-markdown 9.0.1

**State & Data:**
- zustand 4.4.7
- axios 1.6.2

---

## 🔧 Configuration

### Environment Variables

**Required:**
- `DATABASE_URL` - PostgreSQL connection
- `SECRET_KEY` - Application secret
- `JWT_SECRET_KEY` - JWT signing key
- `REDIS_URL` - Redis connection
- `CHROMA_HOST` - ChromaDB host
- `OPENAI_API_KEY` - OpenAI key (if using OpenAI)

**Optional:**
- `PUBMED_API_KEY` - NCBI API key
- `EMBEDDING_MODEL` - Custom embedding model
- `LLM_PROVIDER` - LLM provider choice
- `SENTRY_DSN` - Error tracking

See `.env.example` for complete list with defaults.

---

## 🧪 Testing

### Backend Tests

```bash
cd backend
pytest tests/ -v --cov=app
```

### Frontend Tests

```bash
cd frontend
npm test
```

### Integration Tests

```bash
cd backend
pytest tests/integration/ -v
```

---

## 📚 Documentation

1. **README.md**: User guide and quick start
2. **ARCHITECTURE.md**: Detailed system architecture
3. **DEPLOYMENT.md**: Deployment and operations guide
4. **API Documentation**: Auto-generated at `/docs` (Swagger UI)

---

## 🎯 Use Cases

### For Researchers

1. **Literature Review**: "What are the latest findings on retinal degeneration?"
2. **Gene Analysis**: Upload gene lists for pathway enrichment analysis
3. **Paper Understanding**: Upload PDFs and ask questions about them
4. **Cross-Reference**: Find connections between different research areas

### For Clinicians

1. **Disease Information**: "Explain the pathophysiology of glaucoma"
2. **Treatment Research**: "What are emerging treatments for AMD?"
3. **Genetic Counseling**: Pathway analysis for patient genetic data

### For Students

1. **Learning**: Ask questions about vision biology
2. **Research Preparation**: Explore literature before starting projects
3. **Concept Clarification**: Get explanations with cited sources

---

## 🔮 Future Enhancements

1. **Advanced Features**
   - Multi-modal vision model integration
   - Automated literature review generation
   - Real-time collaboration features
   - Mobile applications

2. **AI Improvements**
   - Fine-tuned vision-domain LLM
   - Active learning from user feedback
   - Multi-agent reasoning
   - Automated hypothesis generation

3. **Integration**
   - Galaxy workflow integration
   - R/Bioconductor packages
   - Jupyter notebook extension
   - API for external tools

---

## 📞 Support & Contribution

### Getting Help

- **Documentation**: Read ARCHITECTURE.md and DEPLOYMENT.md
- **Issues**: Open GitHub issues for bugs
- **Email**: support@visionchatbot.com

### Contributing

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Submit pull request

---

## 📄 License

This project is licensed under the MIT License.

---

## 👥 Team

Developed for the vision research community to advance eye genomics and biology research.

---

## 🌟 Acknowledgments

- Hugging Face for Transformers
- LangChain for RAG framework
- NCBI for PubMed access
- KEGG, Reactome, and GO for pathway databases
- The open-source community

---

**Built with ❤️ for Vision Research**

Version 1.0.0 | Last Updated: 2024

