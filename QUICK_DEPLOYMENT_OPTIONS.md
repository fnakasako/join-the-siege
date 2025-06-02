# Quick Deployment Options: Get Live in Minutes, Not Days

## 1. **Railway** (Recommended - Fastest)

### Why Railway?
- **Deploy in 5 minutes** from GitHub
- **Zero configuration** - just connect your repo
- **Built-in databases** (PostgreSQL, Redis)
- **Auto-scaling** included
- **$5-20/month** to start

### Deployment Steps:
```bash
# 1. Push your code to GitHub (2 minutes)
git add .
git commit -m "Ready for Railway deployment"
git push origin main

# 2. Connect to Railway (1 minute)
# - Go to railway.app
# - Connect GitHub repo
# - Select "join-the-siege" repo

# 3. Add services (2 minutes)
# Railway auto-detects:
# - Your Dockerfile
# - Need for PostgreSQL
# - Need for Redis

# 4. Set environment variables (1 minute)
OPENAI_API_KEY_1=your-key-1
OPENAI_API_KEY_2=your-key-2
OPENAI_API_KEY_3=your-key-3
DB_PASSWORD=auto-generated
REDIS_URL=auto-generated

# 5. Deploy (automatic)
# Railway builds and deploys automatically
```

### Railway Configuration:
```yaml
# railway.json (optional - Railway auto-detects most settings)
{
  "build": {
    "builder": "DOCKERFILE"
  },
  "deploy": {
    "startCommand": "gunicorn -w 4 -b 0.0.0.0:$PORT src.app:app",
    "healthcheckPath": "/health"
  }
}
```

### Cost: $5-50/month for 100k-300k requests

---

## 2. **Render** (Second Choice - Very Fast)

### Why Render?
- **Deploy in 10 minutes**
- **Free tier available**
- **Auto-scaling** built-in
- **Managed databases**
- **Simple pricing**

### Deployment Steps:
```bash
# 1. Create render.yaml in your repo
# 2. Connect GitHub to Render
# 3. Deploy automatically

# render.yaml
services:
  - type: web
    name: document-classifier
    env: docker
    plan: starter  # $7/month
    dockerfilePath: ./Dockerfile
    envVars:
      - key: OPENAI_API_KEY
        sync: false
      - key: DATABASE_URL
        fromDatabase:
          name: classifier-db
          property: connectionString
      - key: REDIS_URL
        fromService:
          type: redis
          name: classifier-redis
          property: connectionString

  - type: redis
    name: classifier-redis
    plan: starter  # $7/month

databases:
  - name: classifier-db
    plan: starter  # $7/month
```

### Cost: $21/month to start (3 services)

---

## 3. **DigitalOcean App Platform** (Good Balance)

### Why DigitalOcean?
- **Deploy in 15 minutes**
- **Predictable pricing**
- **Good performance**
- **Simple scaling**

### Deployment:
```yaml
# .do/app.yaml
name: document-classifier
services:
- name: api
  source_dir: /
  github:
    repo: your-username/join-the-siege
    branch: main
  run_command: gunicorn -w 4 -b 0.0.0.0:8080 src.app:app
  environment_slug: python
  instance_count: 2
  instance_size_slug: basic-xxs  # $5/month each
  
- name: worker
  source_dir: /
  github:
    repo: your-username/join-the-siege
    branch: main
  run_command: celery -A src.async_classifier.celery_app worker
  environment_slug: python
  instance_count: 2
  instance_size_slug: basic-xxs

databases:
- name: classifier-db
  engine: PG
  size: db-s-1vcpu-1gb  # $15/month

- name: classifier-redis
  engine: REDIS
  size: db-s-1vcpu-1gb  # $15/month
```

### Cost: $55/month (2 API + 2 workers + DB + Redis)

---

## 4. **Fly.io** (Developer Friendly)

### Why Fly.io?
- **Deploy in 10 minutes**
- **Global edge deployment**
- **Great for Docker**
- **Generous free tier**

### Deployment:
```bash
# 1. Install flyctl
curl -L https://fly.io/install.sh | sh

# 2. Login and launch
fly auth login
fly launch

# 3. Fly auto-generates fly.toml
# 4. Deploy
fly deploy
```

### Auto-generated fly.toml:
```toml
app = "document-classifier"

[build]
  dockerfile = "Dockerfile"

[[services]]
  http_checks = []
  internal_port = 5000
  processes = ["app"]
  protocol = "tcp"
  script_checks = []

  [services.concurrency]
    hard_limit = 25
    soft_limit = 20
    type = "connections"

  [[services.ports]]
    force_https = true
    handlers = ["http"]
    port = 80

  [[services.ports]]
    handlers = ["tls", "http"]
    port = 443

  [[services.tcp_checks]]
    grace_period = "1s"
    interval = "15s"
    restart_limit = 0
    timeout = "2s"
```

### Cost: $0-30/month to start

---

## 5. **Heroku** (Easiest but Expensive)

### Why Heroku?
- **Deploy in 5 minutes**
- **Zero configuration**
- **Huge ecosystem**
- **But expensive at scale**

### Deployment:
```bash
# 1. Install Heroku CLI
# 2. Login
heroku login

# 3. Create app
heroku create your-classifier-api

# 4. Add services
heroku addons:create heroku-postgresql:mini  # $5/month
heroku addons:create heroku-redis:mini       # $3/month

# 5. Set config
heroku config:set OPENAI_API_KEY=your-key

# 6. Deploy
git push heroku main
```

### Cost: $25-100/month (but simple)

---

## **Recommendation: Railway for Speed**

For your use case, I'd recommend **Railway** because:

### ✅ **Fastest to Deploy (5 minutes)**
1. Connect GitHub repo
2. Railway auto-detects everything
3. Add environment variables
4. Deploy automatically

### ✅ **Auto-Scaling Built-in**
- Handles traffic spikes automatically
- No configuration needed
- Scales down when idle

### ✅ **Managed Services**
- PostgreSQL and Redis included
- Automatic backups
- No server management

### ✅ **Cost Effective**
```
Starter: $5/month (good for testing)
Pro: $20/month (handles 100k+ requests)
Scale: $50/month (handles 500k+ requests)
```

### ✅ **Simple Scaling**
When you need more capacity:
1. Increase instance size (1 click)
2. Add more instances (1 click)
3. No infrastructure changes needed

## Quick Start with Railway

```bash
# 1. Prepare your repo (1 minute)
echo "web: gunicorn -w 4 -b 0.0.0.0:\$PORT src.app:app" > Procfile
echo "worker: celery -A src.async_classifier.celery_app worker" >> Procfile

# 2. Push to GitHub (1 minute)
git add .
git commit -m "Railway deployment ready"
git push origin main

# 3. Deploy on Railway (3 minutes)
# - Go to railway.app
# - Connect GitHub
# - Add PostgreSQL service
# - Add Redis service
# - Set OPENAI_API_KEY environment variable
# - Deploy automatically happens

# 4. Test (1 minute)
curl https://your-app.railway.app/health
```

**Total time: 6 minutes from code to live API**

This gets you a production-ready, auto-scaling API without any AWS complexity!
