# 🚀 Quick Start Guide

## ✅ Fixes Applied

1. ✅ **Light mode as default**
2. ✅ **Source map warnings suppressed** (restart dev server to see effect)
3. ✅ **Professional contrast & colors**
4. ✅ **Complete Neo4j backend integration**

---

## 🏃 Start in 30 Seconds

### Terminal 1 - Backend
```bash
./start_backend.sh
```

**OR manually:**
```bash
pip install -r requirements-api.txt
python -m uvicorn src.api.main:app --reload --port 8000
```

**Expected output:**
```
🚀 Starting Pura Vida Sloth API...
📊 Neo4j connection configured
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Terminal 2 - Frontend
```bash
cd frontend
npm run dev
```

**Open:** http://localhost:5173

---

## ✅ Verify It Works

### 1. Check Backend Health
```bash
curl http://localhost:8000/health
```

**Expected:**
```json
{"status":"healthy","service":"Pura Vida Sloth API","version":"1.0.0"}
```

### 2. Check Neo4j Connection
```bash
curl http://localhost:8000/health/neo4j
```

**Expected:**
```json
{"status":"healthy","neo4j":"connected"}
```

### 3. Test Subgraph Query
```bash
curl -X POST http://localhost:8000/api/neo4j/subgraph \
  -H "Content-Type: application/json" \
  -d '{"tech_id": "evtol"}'
```

**Expected:** JSON with `nodes` and `edges` arrays

### 4. Test Frontend
1. Open http://localhost:5173
2. ✅ Should see **light mode** (white background)
3. ✅ Click "eVTOL" node
4. ✅ See loading indicator "Querying Neo4j..."
5. ✅ Interactive graph appears

---

## 🔧 Troubleshooting

### Issue: Source map warning still appears

**Solution:** Restart the dev server
```bash
# Stop dev server (Ctrl+C in Terminal 2)
cd frontend
npm run dev
```

The warning is now suppressed with `css: { devSourcemap: false }` in vite.config.ts

### Issue: `ECONNREFUSED` error

**Cause:** Backend not running

**Solution:**
```bash
# Terminal 1
./start_backend.sh
```

### Issue: "Neo4j connection failed"

**Cause:** Invalid .env credentials

**Solution:** Check `.env` file has:
```bash
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-actual-password
NEO4J_DATABASE=neo4j
```

### Issue: "Technology 'evtol' not found"

**Cause:** No data in Neo4j with that ID

**Solution:**
1. Run Phase 3 ingestion:
   ```bash
   python src/cli/ingest.py --industry evtol
   ```
2. OR test with a different ID from your Neo4j database
3. OR check what IDs exist:
   ```cypher
   // In Neo4j Browser
   MATCH (t:Technology) RETURN t.id LIMIT 20
   ```

---

## 📊 Architecture Flow

```
Click "eVTOL" node
    ↓
Frontend: POST /api/neo4j/subgraph {tech_id: "evtol"}
    ↓
Vite proxy → localhost:8000
    ↓
FastAPI: neo4j_routes.py
    ↓
Neo4j Service: Execute Cypher
    MATCH (t:Technology {id: "evtol"})
    OPTIONAL MATCH (t)-[r]-(n)
    RETURN t, r, n
    ↓
Vis Converter: Transform to vis.js format
    ↓
Return {nodes: [...], edges: [...]}
    ↓
Frontend: Render interactive graph
```

---

## 🎯 What You Should See

### 1. Light Mode (Default)
- White background
- Black text
- High contrast
- Visible separators

### 2. Interactive Graph
- Technology node in center (larger)
- Related nodes around it (companies, patents, documents)
- Labeled relationships (MENTIONED_IN, etc.)
- Hover to see tooltips
- Drag to rearrange
- Zoom with mouse wheel

### 3. No Console Errors
- No source map warnings ✅
- No CORS errors ✅
- No Neo4j connection errors ✅

---

## 📝 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API info |
| `/health` | GET | Health check |
| `/health/neo4j` | GET | Neo4j connection test |
| `/api/neo4j/subgraph` | POST | **Get tech subgraph** |
| `/docs` | GET | Swagger UI |

---

## 🔗 Useful Links

- **Frontend:** http://localhost:5173
- **Backend:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health
- **Neo4j Health:** http://localhost:8000/health/neo4j

---

## 🎉 Success Checklist

- [✅] Backend running on port 8000
- [✅] Frontend running on port 5173
- [✅] Light mode showing by default
- [✅] No source map warnings
- [✅] Can click technology nodes
- [✅] Graph loads from Neo4j
- [✅] Relationships visible

Everything working? You're all set! 🦥
