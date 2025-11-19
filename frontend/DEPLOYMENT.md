# Canopy Intelligence - Deployment Guide

Complete guide for deploying Canopy Intelligence to free hosting platforms (Render + Vercel).

**Target Architecture:**
```
[Vercel] Frontend (React + Vite)
    ↓ HTTPS REST
[Render] Backend (FastAPI) - Demo Mode
    ↓ Cypher Queries
[Neo4j Aura] Graph Database
```

**Total Monthly Cost:** $0 (100% free tier)

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Backend Deployment (Render)](#backend-deployment-render)
3. [Frontend Deployment (Vercel)](#frontend-deployment-vercel)
4. [Testing Your Deployment](#testing-your-deployment)
5. [Troubleshooting](#troubleshooting)
6. [Maintenance](#maintenance)

---

## Prerequisites

Before you begin, ensure you have:

- ✅ **GitHub Account** - Your code must be in a GitHub repository
- ✅ **Neo4j Aura Free Instance** - Get yours at [neo4j.com/cloud/aura-free](https://neo4j.com/cloud/aura-free/)
- ✅ **Neo4j Credentials** - Save these during setup:
  - Connection URI (e.g., `neo4j+s://xxxxx.databases.neo4j.io`)
  - Username (usually `neo4j`)
  - Password (what you set during Neo4j creation)
- ✅ **Pre-generated Data** - Run the pipeline locally at least once to generate chart data

**No Credit Cards Required!** Both Render and Vercel offer generous free tiers without requiring payment information.

---

## Backend Deployment (Render)

Deploy the FastAPI backend in read-only demo mode (zero OpenAI costs).

### Step 1: Create Render Account

1. Go to [render.com](https://render.com)
2. Click **"Get Started for Free"**
3. Sign up with your **GitHub account** (easiest option)
4. Authorize Render to access your repositories

### Step 2: Create Web Service

1. In Render Dashboard, click **"New +"** → **"Web Service"**
2. **Connect Repository:**
   - Select your GitHub organization/account
   - Find and click **"pura-vida-sloth"** repository
   - Click **"Connect"**

3. **Configure Service:**

   | Setting | Value |
   |---------|-------|
   | **Name** | `canopy-intelligence-api` |
   | **Region** | Oregon (US West) - free tier |
   | **Branch** | `main` |
   | **Root Directory** | *Leave empty* |
   | **Runtime** | Python 3 |
   | **Build Command** | `pip install -r requirements.txt` |
   | **Start Command** | `uvicorn src.api.main:app --host 0.0.0.0 --port $PORT` |
   | **Instance Type** | **Free** ($0/month, 512 MB RAM) |

### Step 3: Add Environment Variables

Click **"Advanced"** → **"Add Environment Variable"** and add these:

| Key | Value | Notes |
|-----|-------|-------|
| `ENABLE_PIPELINE_EXECUTION` | `false` | Disables agents (demo mode) |
| `ENVIRONMENT` | `production` | Marks as production |
| `PYTHONUNBUFFERED` | `1` | Enables real-time logs |
| `NEO4J_URI` | `neo4j+s://xxxxx.databases.neo4j.io` | Your Neo4j Aura URI |
| `NEO4J_USERNAME` | `neo4j` | Usually 'neo4j' |
| `NEO4J_PASSWORD` | `your-password` | Your Neo4j password |
| `NEO4J_DATABASE` | `neo4j` | Usually 'neo4j' |

**⚠️ Important:** Click the 🔒 icon next to `NEO4J_PASSWORD` to mark it as a secret.

### Step 4: Deploy

1. Click **"Create Web Service"**
2. Render will start building your application (takes 2-3 minutes)
3. Watch the build logs - you should see:
   ```
   🚀 Starting Canopy Intelligence API...
   📊 Neo4j connection configured
   🌐 CORS enabled for frontend
   ⚙️  Configuration:
      - Environment: production
      - Pipeline execution: ❌ DISABLED (demo mode)
      - Neo4j connected: ✅
   📖 Read-only mode (zero costs, pre-generated data)
   ```

4. Once deployed, **copy your service URL**:
   ```
   https://canopy-intelligence-api.onrender.com
   ```
   *(Your actual URL will have a random hash)*

### Step 5: Test Backend

Test your endpoints:

```bash
# Health check
curl https://canopy-intelligence-api-xxxxx.onrender.com/health

# Expected response: {"status": "healthy", ...}

# Neo4j connection check
curl https://canopy-intelligence-api-xxxxx.onrender.com/health/neo4j

# Expected response: {"status": "healthy", "neo4j_connected": true}
```

✅ **Backend deployment complete!** Keep your service URL handy for the frontend setup.

---

## Frontend Deployment (Vercel)

Deploy the React frontend configured to connect to your Render backend.

### Step 1: Create Vercel Account

1. Go to [vercel.com](https://vercel.com)
2. Click **"Sign Up"**
3. Choose **"Continue with GitHub"** (easiest option)
4. Authorize Vercel to access your repositories

### Step 2: Import Project

1. In Vercel Dashboard, click **"Add New..."** → **"Project"**
2. **Import Repository:**
   - Find **"pura-vida-sloth"** in your repo list
   - Click **"Import"**

### Step 3: Configure Build Settings

**⚠️ CRITICAL:** Set these exactly as shown:

| Setting | Value | Notes |
|---------|-------|-------|
| **Project Name** | `canopy-intelligence` | Your choice |
| **Framework Preset** | **Vite** | Auto-detected |
| **Root Directory** | `frontend` | ⚠️ Must be set! |
| **Build Command** | `npm install --legacy-peer-deps && npm run build` | Already in vercel.json |
| **Output Directory** | `dist` | Already in vercel.json |
| **Install Command** | `npm install --legacy-peer-deps` | Already in vercel.json |

**How to Set Root Directory:**
1. Click **"Edit"** next to Root Directory
2. Select **"frontend"** from dropdown (or type it)
3. Verify it shows `frontend/` in the input

### Step 4: Add Environment Variables

Click **"Environment Variables"** section and add these **3 variables**:

| Name | Value | Environment |
|------|-------|-------------|
| `VITE_API_URL` | `https://canopy-intelligence.onrender.com` | Production |
| `VITE_ENABLE_PIPELINE_EXECUTION` | `false` | Production |
| `VITE_ENV` | `production` | Production |

**⚠️ Replace** `xxxxx` with your actual Render service hash from Step 2.4!

### Step 5: Deploy

1. Click **"Deploy"**
2. Vercel will:
   - Build your React app (~2-3 minutes)
   - Run TypeScript compilation
   - Bundle with Vite
   - Deploy to CDN

3. Watch the build logs - ensure no errors

4. Once deployed, **copy your deployment URL**:
   ```
   https://canopy-intelligence.vercel.app
   ```
   *(May have random hash initially)*

### Step 6: Test Frontend

1. Open your Vercel URL in a browser
2. You should see:
   - ✅ Blue banner: "📊 Demo Mode - Viewing pre-generated analysis"
   - ✅ Hype Cycle Chart loads
   - ✅ "Run Multi-Agent" button is grayed out
   - ✅ Technology cards display

3. **Test Interactive Graph:**
   - Click any technology bubble on the chart
   - Neo4j graph should load on the right side
   - Graph should display nodes and relationships

---

## Testing Your Deployment

### Complete Integration Test

Run through this checklist:

- [ ] **Frontend Loads:**
  - Open `https://canopy-intelligence.vercel.app`
  - Page loads without errors
  - Hype Cycle Chart renders

- [ ] **Demo Mode Banner:**
  - Blue banner appears at top
  - Says "Demo Mode - Viewing pre-generated analysis"
  - "Run locally →" link works

- [ ] **Run Pipeline Button:**
  - Button shows "Demo Mode" text
  - Button is grayed out/disabled
  - Tooltip explains demo mode

- [ ] **Neo4j Graph Interaction:**
  - Click any technology on chart
  - Right panel loads Neo4j graph
  - Graph displays nodes and edges
  - Nodes are clickable with details

- [ ] **Browser Console:**
  - Open DevTools (F12)
  - No CORS errors
  - API calls succeed (Network tab)
  - Check: `GET /api/pipeline/last-chart` → 200 OK
  - Check: `POST /api/neo4j/subgraph` → 200 OK

- [ ] **Backend Health:**
  - Visit `https://your-api.onrender.com/health`
  - Returns JSON with "healthy" status
  - Neo4j connection shows as connected

---

## Troubleshooting

### Common Issues & Solutions

#### Issue: Frontend Shows "Failed to fetch chart data"

**Cause:** Backend not responding or CORS misconfigured

**Solution:**
1. Check backend is running: `https://your-api.onrender.com/health`
2. If it takes 30+ seconds, backend was sleeping (cold start - normal)
3. Verify `VITE_API_URL` in Vercel matches your Render URL exactly
4. Check browser console for CORS errors

#### Issue: "CORS policy blocked" Error

**Cause:** Backend not allowing Vercel domain

**Solution:**
1. Check `src/api/main.py` includes your Vercel URL in CORS origins
2. Redeploy backend on Render (push to GitHub)
3. Should include: `https://canopy-intelligence.vercel.app`

#### Issue: Build Fails with TypeScript Errors

**Cause:** Missing Vite types or unused variables

**Solution:**
1. Ensure `frontend/src/vite-env.d.ts` exists
2. Check `frontend/tsconfig.json` has `"types": ["vite/client"]`
3. If still failing, set `noUnusedLocals: false` in tsconfig

#### Issue: Neo4j Graph Won't Load

**Cause:** Backend can't connect to Neo4j

**Solution:**
1. Test Neo4j health: `https://your-api.onrender.com/health/neo4j`
2. Verify Neo4j credentials in Render environment variables
3. Check Neo4j Aura instance is running (neo4j.com/cloud/aura)
4. Verify NEO4J_URI format: `neo4j+s://xxxxx.databases.neo4j.io`

#### Issue: Backend Takes 30 Seconds to Respond

**Cause:** Render free tier sleeps after 15 minutes of inactivity

**Solution (Optional):**
1. Set up UptimeRobot to ping `/health` every 5 minutes
2. Or accept cold starts (acceptable for demo)
3. First request wakes it up, subsequent requests are instant

#### Issue: Environment Variables Not Working

**Cause:** Vercel needs rebuild after adding env vars

**Solution:**
1. Go to Vercel Dashboard → Your Project
2. Click **"Deployments"** tab
3. Click **"Redeploy"** on latest deployment
4. Select **"Use existing Build Cache"**: **NO**

---

## Maintenance

### Updating Your Deployment

**To deploy code changes:**

1. Commit and push to GitHub:
   ```bash
   git add .
   git commit -m "Your changes"
   git push origin main
   ```

2. **Both Vercel and Render auto-deploy** from `main` branch

3. Monitor build logs in respective dashboards

### Updating Environment Variables

**Backend (Render):**
1. Render Dashboard → Service → Environment
2. Edit variable → Save
3. Service automatically restarts

**Frontend (Vercel):**
1. Vercel Dashboard → Project → Settings → Environment Variables
2. Edit variable → Save
3. **⚠️ Must redeploy** for changes to take effect

### Monitoring

**Render (Backend):**
- Dashboard → Your Service → Metrics
- View request count, response times, errors
- View logs in real-time
- Check sleep/wake cycles

**Vercel (Frontend):**
- Dashboard → Your Project → Analytics
- View page views, visitors, bandwidth
- Check deployment history
- View function invocations (if using)

### Free Tier Limits

**Render:**
- ✅ 750 hours/month (enough for 24/7 operation)
- ✅ 512 MB RAM (sufficient for FastAPI + Neo4j driver)
- ✅ 100 GB bandwidth/month
- ⚠️ Sleeps after 15 min inactivity (first request: 30s wake-up)

**Vercel:**
- ✅ 100 GB bandwidth/month
- ✅ 100 deployments/day
- ✅ 6000 build minutes/month
- ✅ Instant response (no cold starts for static assets)

**Neo4j Aura Free:**
- ✅ 1 GB storage
- ✅ 8 GB RAM
- ✅ Always on (no sleep)
- ⚠️ Connection limits: Check your plan

### Cost Monitoring

**Current Setup:** $0/month

**What if you exceed limits:**
- Render: Service stops (no charges possible)
- Vercel: Build/deploy queued (no charges without CC)
- Neo4j: Read-only mode (no charges without upgrade)

**To enable full features (agents):**
- Set `ENABLE_PIPELINE_EXECUTION=true` in Render
- Add `OPENAI_API_KEY` to Render environment
- Cost: ~$0.001-0.01 per technology analysis

---

## Optional: Prevent Cold Starts

Render's free tier sleeps after 15 minutes. To keep it awake:

### Option 1: UptimeRobot (Recommended)

1. Sign up at [uptimerobot.com](https://uptimerobot.com) (free, no CC)
2. Add New Monitor:
   - Type: HTTP(s)
   - URL: `https://your-api.onrender.com/health`
   - Monitoring Interval: 5 minutes
3. Your backend stays awake 24/7

### Option 2: GitHub Actions

Enable the workflow at `.github/workflows/keep-alive.yml`:

1. Verify file exists in repo
2. Update URL to match your Render service
3. Push to GitHub
4. GitHub Actions pings every 10 minutes automatically

### Option 3: Cron-Job.org

1. Sign up at [cron-job.org](https://cron-job.org) (free, no CC)
2. Create Cronjob:
   - URL: `https://your-api.onrender.com/health`
   - Interval: Every 10 minutes

---

## Support & Resources

### Official Documentation

- **Render:** [render.com/docs](https://render.com/docs)
- **Vercel:** [vercel.com/docs](https://vercel.com/docs)
- **Neo4j Aura:** [neo4j.com/docs/aura](https://neo4j.com/docs/aura)

### Project-Specific Resources

- **Main README:** [README.md](README.md)
- **Architecture Guide:** [ARCHITECTURE.md](ARCHITECTURE.md)
- **Issues:** [GitHub Issues](https://github.com/your-username/pura-vida-sloth/issues)

### Common Questions

**Q: Can I use a custom domain?**
A: Yes! Both Vercel and Render support custom domains on free tier.

**Q: How long do deployments take?**
A: Backend (Render): 2-3 minutes. Frontend (Vercel): 2-3 minutes.

**Q: Can I deploy multiple branches?**
A: Vercel: Yes (preview deployments). Render: Manual setup required.

**Q: What happens if I push broken code?**
A: Build fails, previous version stays live. Fix code and redeploy.

**Q: How do I roll back a deployment?**
A: Vercel: Dashboard → Deployments → Promote previous. Render: Redeploy from git commit.

---

## Summary Checklist

Use this checklist for your first deployment:

### Backend (Render):
- [ ] Create Render account with GitHub
- [ ] Create Web Service from repo
- [ ] Set Root Directory: *empty*
- [ ] Set Build Command: `pip install -r requirements.txt`
- [ ] Set Start Command: `uvicorn src.api.main:app --host 0.0.0.0 --port $PORT`
- [ ] Add 7 environment variables
- [ ] Mark NEO4J_PASSWORD as secret
- [ ] Deploy and wait for success
- [ ] Copy service URL
- [ ] Test `/health` endpoint

### Frontend (Vercel):
- [ ] Create Vercel account with GitHub
- [ ] Import pura-vida-sloth repository
- [ ] Set Root Directory: `frontend`
- [ ] Verify build commands (from vercel.json)
- [ ] Add 3 environment variables with Render URL
- [ ] Deploy and wait for success
- [ ] Test website loads
- [ ] Test Neo4j graph interaction
- [ ] Verify demo mode banner shows

### Final Verification:
- [ ] Click technology → graph loads
- [ ] Demo banner shows
- [ ] Pipeline button disabled
- [ ] No console errors
- [ ] Share link works!

---


Share your link: `https://canopy-intelligence.vercel.app`
