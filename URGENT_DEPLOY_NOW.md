# 🚨 URGENT: Deploy Redis Security Fix NOW

## ⚠️ Critical Security Issue
UCI OIT has identified a critical security vulnerability with your Redis server. **Network access will be cut if not fixed immediately.**

---

## 🚀 Quick Fix (5 Minutes)

### Option 1: Automated Script (Recommended)

SSH to the server and run:

```bash
ssh -p 22000 cvemired-admin@eye.som.uci.edu
# Password: bwnxQznp2Dh6

cd ~/AI-Vision-Chatbot
git pull origin main
bash deploy/fix_redis_security.sh
```

**That's it!** The script will:
- ✅ Generate a strong password
- ✅ Update your `.env` file
- ✅ Pull latest code
- ✅ Restart all services
- ✅ Verify the fix

---

### Option 2: Manual Steps

If the automated script doesn't work:

```bash
# 1. SSH to server
ssh -p 22000 cvemired-admin@eye.som.uci.edu

# 2. Navigate to project
cd ~/AI-Vision-Chatbot

# 3. Generate password
openssl rand -base64 32

# 4. Edit .env file
nano .env

# 5. Add this line (replace with your generated password):
REDIS_PASSWORD=your_generated_password_here

# 6. Save and exit (Ctrl+X, Y, Enter)

# 7. Pull latest code
git pull origin main

# 8. Restart services
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d

# 9. Verify
docker-compose -f docker-compose.prod.yml ps
```

---

## ✅ Verification

After deployment, verify Redis is secured:

```bash
# Should show "NOAUTH Authentication required"
docker exec vision_redis redis-cli ping

# Should show "PONG"
docker exec vision_redis redis-cli -a "YOUR_PASSWORD" ping
```

---

## 📞 After Deployment

1. **Test the application:** http://eye.som.uci.edu:8888
2. **Notify UCI IT (Pablo)** that the security issue is resolved
3. **Monitor logs:** `docker-compose -f docker-compose.prod.yml logs -f`

---

## 📚 More Information

See `REDIS_SECURITY_UPDATE.md` for detailed documentation.

---

**Priority:** 🔴 CRITICAL  
**Time Required:** ⏱️ 5 minutes  
**Status:** Ready to deploy

