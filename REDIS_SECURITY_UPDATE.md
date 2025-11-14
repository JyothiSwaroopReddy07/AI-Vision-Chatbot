# 🚨 CRITICAL: Redis Security Update Required

## Overview
This update addresses a **critical security vulnerability** identified by UCI OIT. Redis is currently running without authentication, which poses a severe security risk.

**⚠️ URGENT: Network access will be cut if this is not resolved immediately.**

---

## What Changed

### 1. Redis Password Authentication
Redis now requires password authentication for all connections.

### 2. Updated Files
- `docker-compose.prod.yml` - Added password requirement to Redis service
- `deploy/env.production.example` - Added Redis password configuration
- All service environment variables updated to use authenticated Redis URLs

---

## 🚀 Deployment Instructions

### Step 1: Generate a Strong Password

On the server, run:
```bash
openssl rand -base64 32
```

This will generate a strong password like: `xK9mP2nQ8vL5wR7tY4uI6oP3aS1dF0gH2jK4lZ6xC8vB=`

### Step 2: Update `.env` File

SSH to the server:
```bash
ssh -p 22000 cvemired-admin@eye.som.uci.edu
cd ~/AI-Vision-Chatbot
```

Edit the `.env` file:
```bash
nano .env
```

Update the `REDIS_PASSWORD` line:
```bash
REDIS_PASSWORD=xK9mP2nQ8vL5wR7tY4uI6oP3aS1dF0gH2jK4lZ6xC8vB=
```

**Important:** Replace the example password above with the one you generated in Step 1.

Save and exit (Ctrl+X, then Y, then Enter).

### Step 3: Pull Latest Code

```bash
git pull origin main
```

### Step 4: Restart All Services

```bash
# Stop all services
docker-compose -f docker-compose.prod.yml down

# Remove old Redis data (optional, but recommended for clean start)
docker volume rm ai-vision-chatbot_redis_data

# Start all services with new configuration
docker-compose -f docker-compose.prod.yml up -d

# Check that all services are running
docker-compose -f docker-compose.prod.yml ps
```

### Step 5: Verify Redis Authentication

Test that Redis is now password-protected:
```bash
# This should FAIL (no password provided)
docker exec vision_redis redis-cli ping

# This should SUCCEED (password provided)
docker exec vision_redis redis-cli -a "YOUR_PASSWORD_HERE" ping
```

You should see:
- First command: `(error) NOAUTH Authentication required.`
- Second command: `PONG`

### Step 6: Check Application Logs

Verify that all services can connect to Redis:
```bash
# Check backend logs
docker-compose -f docker-compose.prod.yml logs --tail=50 backend

# Check Celery worker logs
docker-compose -f docker-compose.prod.yml logs --tail=50 celery_worker

# Check Celery beat logs
docker-compose -f docker-compose.prod.yml logs --tail=50 celery_beat
```

Look for successful connections and no authentication errors.

---

## 🔒 Security Best Practices

### Password Requirements
- **Minimum 32 characters** (use the `openssl rand -base64 32` command)
- **Mix of letters, numbers, and special characters**
- **Never commit passwords to Git**
- **Store securely** (e.g., password manager)

### Why This Matters
1. **Unauthorized Access**: Without authentication, anyone on the network can access Redis
2. **Data Theft**: Attackers can read all cached data (sessions, tokens, etc.)
3. **Data Manipulation**: Attackers can modify or delete cached data
4. **Remote Code Execution**: Redis can be exploited for RCE attacks
5. **Compliance**: UCI OIT requires all services to be properly secured

---

## 📋 Technical Details

### Changes Made

#### `docker-compose.prod.yml`

**Redis Service:**
```yaml
redis:
  command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
  healthcheck:
    test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
```

**Backend Service:**
```yaml
environment:
  - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
```

**Celery Worker Service:**
```yaml
environment:
  - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
  - CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@redis:6379/1
  - CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD}@redis:6379/2
```

**Celery Beat Service:**
```yaml
environment:
  - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
  - CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@redis:6379/1
  - CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD}@redis:6379/2
```

### Redis URL Format
The authenticated Redis URL format is:
```
redis://:<password>@<host>:<port>/<db>
```

Note the colon (`:`) before the password - this indicates an empty username (Redis uses password-only auth by default).

---

## 🆘 Troubleshooting

### Issue: Services can't connect to Redis
**Error:** `NOAUTH Authentication required`

**Solution:** Make sure the `REDIS_PASSWORD` environment variable is set in your `.env` file and matches the password configured in Redis.

### Issue: Redis healthcheck failing
**Error:** `unhealthy`

**Solution:** 
1. Check that `REDIS_PASSWORD` is set in `.env`
2. Restart Redis: `docker-compose -f docker-compose.prod.yml restart redis`
3. Check Redis logs: `docker-compose -f docker-compose.prod.yml logs redis`

### Issue: Backend/Celery connection errors
**Error:** `Error connecting to Redis`

**Solution:**
1. Verify Redis is running: `docker-compose -f docker-compose.prod.yml ps redis`
2. Check that all services use the same password
3. Restart affected services: `docker-compose -f docker-compose.prod.yml restart backend celery_worker celery_beat`

---

## 📞 Support

If you encounter any issues:
1. **Check logs:** `docker-compose -f docker-compose.prod.yml logs <service_name>`
2. **Contact UCI IT:** Pablo (mentioned in the security notice)
3. **GitHub Issues:** Create an issue in the repository

---

## ✅ Verification Checklist

- [ ] Generated strong password using `openssl rand -base64 32`
- [ ] Updated `REDIS_PASSWORD` in `.env` file
- [ ] Pulled latest code from GitHub
- [ ] Stopped all services
- [ ] Started all services with new configuration
- [ ] Verified Redis requires authentication
- [ ] Checked backend logs for successful connection
- [ ] Checked Celery worker logs for successful connection
- [ ] Checked Celery beat logs for successful connection
- [ ] Tested application functionality
- [ ] Notified UCI IT that the issue is resolved

---

**Last Updated:** November 14, 2025
**Priority:** CRITICAL
**Status:** Ready for Deployment

