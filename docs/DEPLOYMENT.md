# Deployment Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Docker Hub Setup](#docker-hub-setup)
3. [GitHub Setup](#github-setup)
4. [Railway Deployment](#railway-deployment)
5. [Verification](#verification)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

**Required Accounts**:
- GitHub account
- Docker Hub account (free tier)
- Railway account (free tier, no credit card)

**Local Requirements**:
- Docker installed
- Git installed
- Python 3.11+

---

## Docker Hub Setup

### 1. Create Docker Hub Account
1. Go to https://hub.docker.com
2. Sign up for free account
3. Verify email

### 2. Create Repository
1. Click "Create Repository"
2. Name: `moderation-api`
3. Visibility: Public (for free tier)
4. Click "Create"

### 3. Generate Access Token
1. Go to Account Settings > Security
2. Click "New Access Token"
3. Description: `github-actions-ci-cd`
4. Access permissions: Read, Write, Delete
5. Copy token (save it securely, shown only once)

---

## GitHub Setup

### 1. Create GitHub Repository

```bash
# On GitHub.com
1. Click "New repository"
2. Name: moderation-api
3. Description: Production-ready ML moderation API
4. Public or Private (your choice)
5. Do NOT initialize with README (we have one)
6. Click "Create repository"
```

### 2. Add GitHub Secrets

```bash
# On GitHub.com, go to your repository
1. Settings > Secrets and variables > Actions
2. Click "New repository secret"

Add these secrets:
- Name: DOCKERHUB_USERNAME
  Value: your-dockerhub-username

- Name: DOCKERHUB_TOKEN
  Value: your-access-token-from-step-above
```

### 3. Push Code to GitHub

```bash
cd /Users/kelvinnyadzayo/test-moderation

# Initialize git (if not already)
git init

# Add all files
git add .

# First commit
git commit -m "Initial commit: Production-ready moderation API"

# Add remote
git remote add origin https://github.com/YOUR_USERNAME/moderation-api.git

# Push to main
git branch -M main
git push -u origin main
```

### 4. Verify CI/CD Pipeline

```bash
# On GitHub.com
1. Go to Actions tab
2. You should see workflow running
3. Wait for it to complete (3-5 minutes)
4. All jobs should be green checkmarks
```

**Pipeline stages**:
- Test: Runs all 22 tests
- Build: Creates Docker image
- Push: Uploads to Docker Hub
- Deploy: Triggers Railway deployment

---

## Railway Deployment

### 1. Create Railway Account
1. Go to https://railway.app
2. Sign up with GitHub (easiest)
3. No credit card required for free tier

### 2. Create New Project

```bash
# On Railway dashboard
1. Click "New Project"
2. Select "Deploy from Docker Hub"
3. Image: YOUR_DOCKERHUB_USERNAME/moderation-api:latest
4. Click "Deploy"
```

### 3. Add Redis Service

```bash
# In your Railway project
1. Click "New"
2. Select "Database"
3. Choose "Redis"
4. Click "Add Redis"
# Railway automatically sets REDIS_URL environment variable
```

### 4. Configure Environment Variables

```bash
# In Railway project > moderation-api service
1. Click on your service
2. Go to "Variables" tab
3. Add these variables:

ENV=production
API_VERSION=1.0.0
LOG_LEVEL=INFO

DEFAULT_MODEL=unitary/toxic-bert
MODEL_CACHE_DIR=./models_cache
LAZY_LOAD_MODEL=true

# Redis (Railway provides REDIS_URL, but we need individual vars)
REDIS_HOST=${{Redis.RAILWAY_PRIVATE_DOMAIN}}
REDIS_PORT=${{Redis.RAILWAY_TCP_PORT}}
REDIS_DB=0
REDIS_PASSWORD=
REDIS_MAX_CONNECTIONS=50

RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=60

CACHE_ENABLED=true
CACHE_TTL_SECONDS=3600

THRESHOLD_HARASSMENT=0.7
THRESHOLD_HATE=0.7
THRESHOLD_PROFANITY=0.6
THRESHOLD_SEXUAL=0.7
THRESHOLD_SPAM=0.8
THRESHOLD_VIOLENCE=0.6

CORS_ORIGINS=["*"]
```

### 5. Expose Public URL

```bash
# In Railway project > moderation-api service
1. Go to "Settings" tab
2. Scroll to "Networking"
3. Click "Generate Domain"
4. Copy your public URL (e.g., https://moderation-api-production.up.railway.app)
```

### 6. Configure Health Checks

```bash
# In Settings > Health Checks
Path: /v1/health
Port: 8000
Interval: 30 seconds
Timeout: 10 seconds
```

---

## Verification

### 1. Check Deployment Status

```bash
# Railway dashboard
1. Service should show "Active"
2. Logs should show: "Application startup complete"
3. No error messages in logs
```

### 2. Test Health Endpoint

```bash
curl https://YOUR_RAILWAY_URL/v1/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2025-09-30T12:00:00.000Z",
  "uptime_seconds": 120.5,
  "components": {
    "api": {"status": "operational"},
    "redis": {"status": "operational", "latency_ms": 2},
    "model": {"status": "loaded", "name": "unitary/toxic-bert", "load_time_seconds": 12.3}
  },
  "version": "1.0.0"
}
```

### 3. Test Moderation Endpoint

```bash
curl -X POST "https://YOUR_RAILWAY_URL/v1/moderate" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [
      {"text": "Hello, this is a test message"}
    ],
    "return_scores": true
  }'

# Should return moderation results
```

### 4. View API Documentation

```bash
# Open in browser
https://YOUR_RAILWAY_URL/docs

# Interactive Swagger UI with all endpoints
```

---

## CI/CD Workflow

### Automatic Deployment Flow

```
1. Developer pushes code to GitHub main branch
   ↓
2. GitHub Actions triggered
   ↓
3. Run all tests (must pass)
   ↓
4. Build Docker image (multi-arch)
   ↓
5. Push to Docker Hub with tags: latest, branch, sha
   ↓
6. Railway detects new `latest` tag
   ↓
7. Railway pulls new image
   ↓
8. Railway deploys with zero downtime
   ↓
9. Health checks verify deployment
   ↓
10. New version live (2-3 minutes total)
```

### Manual Deployment

If you need to deploy manually:

```bash
# 1. Build locally
docker build -t YOUR_DOCKERHUB_USERNAME/moderation-api:latest .

# 2. Push to Docker Hub
docker push YOUR_DOCKERHUB_USERNAME/moderation-api:latest

# 3. Railway auto-detects and deploys
# Or force redeploy in Railway dashboard: Settings > Redeploy
```

---

## Troubleshooting

### Issue: Tests failing in CI/CD

**Symptoms**: GitHub Actions shows red X on test job

**Solution**:
```bash
# Run tests locally first
pytest tests/ -v

# Fix any failing tests
# Commit and push again
```

### Issue: Docker build failing

**Symptoms**: "Build" job fails in GitHub Actions

**Solutions**:
1. Check Dockerfile syntax
2. Verify requirements.txt has all dependencies
3. Test build locally:
```bash
docker build -t test-build .
```

### Issue: Railway deployment timeout

**Symptoms**: Railway shows "Build timeout" or "Deployment failed"

**Solutions**:
1. Check Railway logs for errors
2. Verify environment variables are set correctly
3. Model loading takes 10-15 seconds - increase health check timeout
4. Check Railway service plan limits

### Issue: API returns 503

**Symptoms**: Health check returns "unhealthy"

**Solutions**:
1. Check Redis connection:
```bash
# In Railway dashboard > Redis > Connect
# Copy connection details
```
2. Verify REDIS_HOST and REDIS_PORT in environment variables
3. Check logs for "Redis unavailable" warnings

### Issue: Moderation very slow (>1 second)

**Symptoms**: Requests taking too long

**Solutions**:
1. Check if caching is enabled: `CACHE_ENABLED=true`
2. Verify Redis is connected (check logs)
3. Model may be re-loading each time (check LAZY_LOAD_MODEL setting)
4. Consider upgrading Railway plan for better CPU

### Issue: Rate limiting not working

**Symptoms**: Can send unlimited requests

**Solutions**:
1. Verify `RATE_LIMIT_ENABLED=true`
2. Check Redis connection (rate limiting requires Redis)
3. Look for "Redis unavailable" in logs
4. Test with explicit IP:
```bash
# Multiple rapid requests should get 429
for i in {1..150}; do
  curl -X POST https://YOUR_URL/v1/moderate \
    -H "Content-Type: application/json" \
    -d '{"inputs":[{"text":"test"}]}'
done
```

---

## Rollback Procedure

### If new deployment has issues:

**Option 1: Railway Dashboard (Easiest)**
```bash
1. Go to Railway project
2. Click on service
3. Go to "Deployments" tab
4. Find previous working deployment
5. Click three dots > "Redeploy"
```

**Option 2: Docker Hub Tag**
```bash
# Find previous working image
docker pull YOUR_DOCKERHUB_USERNAME/moderation-api:main-abc123

# Push as latest
docker tag YOUR_DOCKERHUB_USERNAME/moderation-api:main-abc123 \
           YOUR_DOCKERHUB_USERNAME/moderation-api:latest
docker push YOUR_DOCKERHUB_USERNAME/moderation-api:latest

# Railway auto-deploys
```

**Option 3: Git Revert**
```bash
# Revert to previous commit
git revert HEAD
git push origin main

# CI/CD pipeline rebuilds and redeploys
```

---

## Monitoring in Production

### Logs

**Railway Dashboard**:
```bash
1. Click on service
2. Go to "Logs" tab
3. Real-time log streaming
4. Filter by level: INFO, WARNING, ERROR
```

**Important log patterns**:
- `[CACHE HIT]` - Cached requests (good performance)
- `[CACHE MISS]` - Processing new request
- `[RATE LIMIT]` - Rate limiting in action
- `ERROR` - Investigate immediately

### Metrics

**Check health endpoint regularly**:
```bash
# Monitor component status
curl https://YOUR_URL/v1/health | jq '.components'

# Check uptime
curl https://YOUR_URL/v1/health | jq '.uptime_seconds'
```

### Alerts

**Set up monitoring**:
1. Use UptimeRobot (free) to ping /v1/health
2. Alert if health check fails
3. Check every 5 minutes
4. Email/SMS notifications

---

## Cost Estimation

### Free Tier (Development/Demo)
- **Railway**: Free tier includes:
  - $5 credit per month
  - Enough for 1 service + Redis
  - ~500 hours of runtime
- **Docker Hub**: Free public repositories
- **GitHub Actions**: Free for public repos (2000 min/month)

**Total Cost**: $0/month (within free limits)

### Production Tier (Real Users)
- **Railway Pro**: ~$20/month
  - Better performance
  - More resources
  - No sleep after inactivity
- **Docker Hub**: Free (public repo)
- **GitHub Actions**: Free (public repo)

**Total Cost**: ~$20-30/month

### Scale (1M requests/month)
- **Railway**: ~$100-200/month (10 instances)
- **Redis**: Included in Railway or $15/month (separate)
- **Monitoring**: $50/month (Datadog/New Relic)

**Total Cost**: ~$150-300/month

---

## Next Steps After Deployment

1. **Custom Domain** (Optional)
   - Add your domain in Railway settings
   - Update DNS records
   - Automatic HTTPS with Let's Encrypt

2. **Monitoring**
   - Set up UptimeRobot or similar
   - Add Prometheus metrics (code changes needed)
   - Set up Grafana dashboard

3. **Analytics**
   - Track request volumes
   - Monitor moderation trends
   - A/B test different models

4. **Performance**
   - Enable CDN (Cloudflare)
   - Add geographic load balancing
   - Implement request queuing for spikes

---

## Security Checklist

Before going to production:

- [ ] Change CORS_ORIGINS from ["*"] to specific domains
- [ ] Add authentication (API keys or OAuth)
- [ ] Enable HTTPS (Railway does this automatically)
- [ ] Set up secret rotation schedule
- [ ] Review and audit dependencies
- [ ] Set up security scanning (Snyk/Dependabot)
- [ ] Implement request logging (but not sensitive data)
- [ ] Add rate limiting per API key (not just IP)
- [ ] Set up WAF (Web Application Firewall) if needed
- [ ] Regular security updates

---

**Need Help?**
- Railway Docs: https://docs.railway.app
- GitHub Actions Docs: https://docs.github.com/actions
- Docker Hub Docs: https://docs.docker.com/docker-hub
