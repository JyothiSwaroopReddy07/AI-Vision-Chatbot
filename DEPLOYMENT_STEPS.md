# Step-by-Step Deployment Instructions for UCI Server

Follow these exact steps to deploy the AI-Vision-Chatbot with a local 2B parameter LLM on the UCI server.

## Prerequisites

- Server: `eye.som.uci.edu`
- SSH Port: `22000`
- Username: `cvemired-admin`
- Password: `bwnxQznp2Dh6`

## Step 1: Connect to the Server

Open your terminal and connect to the server:

```bash
ssh -p 22000 cvemired-admin@eye.som.uci.edu
```

When prompted, enter password: `bwnxQznp2Dh6`

## Step 2: Clone the Repository

```bash
cd ~
git clone https://github.com/JyothiSwaroopReddy07/AI-Vision-Chatbot.git
cd AI-Vision-Chatbot
```

## Step 3: Create Environment File

```bash
# Copy the example environment file
cp deploy/env.production.example .env

# Edit the environment file
nano .env
```

### Required Changes in .env:

1. **Generate and set SECRET_KEY:**
   ```bash
   # In another terminal, generate a secret key:
   openssl rand -hex 32
   # Copy the output and paste it in .env as SECRET_KEY=<generated_key>
   ```

2. **Generate and set JWT_SECRET_KEY:**
   ```bash
   # Generate another secret key:
   openssl rand -hex 32
   # Copy the output and paste it in .env as JWT_SECRET_KEY=<generated_key>
   ```

3. **Set Hugging Face Token:**
   - Go to: https://huggingface.co/settings/tokens
   - Create a new token (read access is sufficient)
   - Copy the token
   - In .env, set: `HUGGINGFACE_TOKEN=hf_your_token_here`

4. **Verify LLM Settings:**
   Make sure these lines are set correctly:
   ```
   LLM_PROVIDER=local
   LOCAL_LLM_BASE_URL=http://llm:80
   LOCAL_LLM_MODEL=microsoft/phi-2
   ```

5. **Save and exit:**
   - Press `Ctrl + X`
   - Press `Y` to confirm
   - Press `Enter` to save

## Step 4: Check System Resources

```bash
# Check available memory
free -h

# Check disk space
df -h

# Check if GPU is available (optional but recommended)
nvidia-smi
```

**Note:** If GPU is not available, the LLM will use CPU (slower but works).

## Step 5: Install Docker and Docker Compose (if not installed)

```bash
# Check if Docker is installed
docker --version

# If not installed, run:
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Check if Docker Compose is installed
docker-compose --version

# If not installed, run:
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# If Docker was just installed, log out and log back in:
exit
# Then SSH back in
ssh -p 22000 cvemired-admin@eye.som.uci.edu
cd ~/AI-Vision-Chatbot
```

## Step 6: Deploy the Application

```bash
# Make the deployment script executable
chmod +x deploy/quick_deploy.sh

# Run the deployment
./deploy/quick_deploy.sh
```

**This will take 10-15 minutes** because it needs to:
- Download the Phi-2 model (~5GB)
- Build Docker containers
- Start all services

## Step 7: Monitor the Deployment

While the deployment is running, you can monitor progress in another terminal:

```bash
# Open a new terminal and SSH to the server
ssh -p 22000 cvemired-admin@eye.som.uci.edu
cd ~/AI-Vision-Chatbot

# Watch the LLM download progress
docker-compose -f docker-compose.prod.yml logs -f llm

# Wait for "Model loaded successfully" message
```

## Step 8: Verify Services are Running

```bash
# Check service status
docker-compose -f docker-compose.prod.yml ps

# All services should show "Up" or "Up (healthy)"
```

Expected output:
```
NAME                    STATUS
vision_backend          Up
vision_celery_beat      Up
vision_celery_worker    Up
vision_chromadb         Up
vision_frontend         Up
vision_grafana          Up
vision_llm              Up (healthy)
vision_nginx            Up
vision_postgres         Up (healthy)
vision_prometheus       Up
vision_redis            Up (healthy)
```

## Step 9: Test the LLM Service

```bash
# Test the LLM directly
curl -X POST http://localhost:8080/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is age-related macular degeneration?",
    "max_tokens": 100
  }'
```

You should get a JSON response with generated text.

## Step 10: Test the Backend API

```bash
# Check backend health
curl http://localhost:8000/health

# Should return: {"status":"healthy"}
```

## Step 11: Access the Application

Open your web browser and go to:

- **Frontend:** http://eye.som.uci.edu:3000
- **Backend API Docs:** http://eye.som.uci.edu:8000/docs
- **Nginx Proxy:** http://eye.som.uci.edu:8888

## Step 12: Create Your First User

1. Go to http://eye.som.uci.edu:3000
2. Click "Register" or "Sign Up"
3. Fill in your details:
   - Email: your_email@example.com
   - Username: your_username
   - Password: your_password
4. Click "Register"

## Step 13: Test the Chat

1. After logging in, you should see the chat interface
2. Type a question: "What is age-related macular degeneration?"
3. Press Enter or click Send
4. Wait for the response (may take 5-10 seconds on CPU, 1-2 seconds on GPU)
5. You should see an answer with citations from PubMed

## Troubleshooting

### If LLM Service Won't Start:

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs llm

# Common issues:
# 1. Out of memory - check: free -h
# 2. Missing Hugging Face token - check .env file
# 3. Model download failed - check internet connection
```

### If Backend Shows Errors:

```bash
# Check backend logs
docker-compose -f docker-compose.prod.yml logs backend

# Restart backend
docker-compose -f docker-compose.prod.yml restart backend
```

### If Frontend Won't Load:

```bash
# Check frontend logs
docker-compose -f docker-compose.prod.yml logs frontend

# Restart frontend
docker-compose -f docker-compose.prod.yml restart frontend
```

### If Getting "Out of Memory" Errors:

```bash
# Edit .env to use less memory
nano .env

# Change these values:
MAX_TOKENS=1000
RETRIEVAL_K=3
EMBEDDING_BATCH_SIZE=32

# Restart services
docker-compose -f docker-compose.prod.yml restart
```

## Useful Commands

### View Logs
```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f llm
docker-compose -f docker-compose.prod.yml logs -f backend
```

### Restart Services
```bash
# Restart all
docker-compose -f docker-compose.prod.yml restart

# Restart specific service
docker-compose -f docker-compose.prod.yml restart backend
```

### Stop Services
```bash
docker-compose -f docker-compose.prod.yml down
```

### Start Services Again
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Check Resource Usage
```bash
# Memory and CPU usage
docker stats

# GPU usage (if available)
watch -n 1 nvidia-smi
```

## Next Steps

### 1. Index PubMed Articles

To get actual research data, you need to index PubMed articles:

```bash
# First, get an access token by logging in to the frontend
# Then use that token in the API call

curl -X POST http://localhost:8000/api/v1/pubmed/index \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "search_terms": ["retina", "macular degeneration", "glaucoma"],
    "max_results": 1000
  }'
```

### 2. Set Up Monitoring

- Access Grafana: http://eye.som.uci.edu:3001
- Login: admin / admin
- Change the default password
- Explore the dashboards

### 3. Set Up Backups

```bash
# Create a backup script
cat > ~/backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d)
cd ~/AI-Vision-Chatbot
docker-compose -f docker-compose.prod.yml exec -T postgres pg_dump -U postgres visiondb > backup_$DATE.sql
tar -czf chromadb_backup_$DATE.tar.gz data/chromadb/
EOF

chmod +x ~/backup.sh

# Run backup manually
~/backup.sh

# Or set up a cron job for daily backups
crontab -e
# Add this line:
# 0 2 * * * /home/cvemired-admin/backup.sh
```

## Performance Optimization

### If Using GPU:
- Responses should be 1-2 seconds
- Monitor GPU: `watch -n 1 nvidia-smi`

### If Using CPU Only:
- Responses will be 5-10 seconds
- This is normal for CPU inference
- Consider using a smaller model if too slow

### To Use a Smaller/Faster Model:

```bash
# Edit .env
nano .env

# Change to a smaller model:
LOCAL_LLM_MODEL=TinyLlama/TinyLlama-1.1B-Chat-v1.0

# Restart LLM service
docker-compose -f docker-compose.prod.yml restart llm backend
```

## Support

If you encounter issues:

1. **Check logs first:**
   ```bash
   docker-compose -f docker-compose.prod.yml logs -f
   ```

2. **Check service status:**
   ```bash
   docker-compose -f docker-compose.prod.yml ps
   ```

3. **Review the deployment guide:**
   ```bash
   cat deploy/DEPLOYMENT_GUIDE.md
   ```

4. **Create a GitHub issue** with:
   - Error message
   - Relevant logs
   - System information (RAM, GPU, etc.)

## Summary

You now have:
- ✅ AI-Vision-Chatbot running on UCI server
- ✅ Local Phi-2 (2.7B) LLM for inference
- ✅ RAG pipeline with ChromaDB
- ✅ PostgreSQL for user data
- ✅ Redis for caching
- ✅ Celery for background tasks
- ✅ Monitoring with Grafana and Prometheus
- ✅ Nginx reverse proxy on port 8888

**Access Points:**
- Frontend: http://eye.som.uci.edu:3000
- Backend: http://eye.som.uci.edu:8000
- API Docs: http://eye.som.uci.edu:8000/docs
- Grafana: http://eye.som.uci.edu:3001

Enjoy your self-hosted AI chatbot! 🎉

