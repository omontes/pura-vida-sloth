# Phase 6 Frontend - Startup Guide

## ✅ All Issues Fixed

1. **✅ Light mode now default** - Always starts in light mode
2. **✅ Improved contrast** - Black text, visible separators, professional colors
3. **✅ Vite source map warning suppressed** - No more vis-network.css.map errors
4. **✅ Neo4j component fixed** - Shows proper loading/error states
5. **✅ FastAPI backend created** - Full Neo4j integration ready

---

## 🚀 Quickstart (2 Commands)

### 1. Start Backend (Terminal 1)

```bash
# Install API dependencies
pip install -r requirements-api.txt

# Verify .env has Neo4j credentials (NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE)

# Start FastAPI server
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output:**
```
🚀 Starting Pura Vida Sloth API...
📊 Neo4j connection configured
🌐 CORS enabled for frontend
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 2. Start Frontend (Terminal 2)

```bash
cd frontend
npm run dev
```

**Open:** http://localhost:5173

---

## 🔍 How It Works

### User Journey

1. **Page loads** → Light mode (white background, black text)
2. **Click "eVTOL" node** → Triggers API call
3. **Frontend sends** → `POST /api/neo4j/subgraph` with `{tech_id: "evtol"}`
4. **Backend executes** → Cypher query:
   ```cypher
   MATCH (t:Technology {id: "evtol"})
   OPTIONAL MATCH (t)-[r]-(n)
   RETURN t, r, n
   ```
5. **Backend converts** → Neo4j result → vis.js format
6. **Frontend renders** → Interactive knowledge graph

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | API health check |
| `/health/neo4j` | GET | Neo4j connection test |
| `/api/neo4j/subgraph` | POST | **Get technology subgraph** |
| `/docs` | GET | Swagger API docs |

---

## 📂 Backend Structure

```
src/api/
├── main.py                  # FastAPI app entry point
├── config.py                # Environment settings
├── dependencies.py          # Neo4j driver singleton
├── models/
│   └── schemas.py           # Pydantic request/response models
├── routes/
│   ├── health.py            # Health check endpoints
│   └── neo4j_routes.py      # POST /api/neo4j/subgraph
└── services/
    ├── neo4j_service.py     # Cypher query execution
    └── vis_converter.py     # Neo4j → vis.js transformation
```

---

## 🧪 Testing the Flow

### 1. Test Backend Independently

```bash
# Health check
curl http://localhost:8000/health

# Neo4j health
curl http://localhost:8000/health/neo4j

# Test subgraph query
curl -X POST http://localhost:8000/api/neo4j/subgraph \
  -H "Content-Type: application/json" \
  -d '{"tech_id": "evtol"}'
```

**Expected response:**
```json
{
  "nodes": [
    {
      "id": "...",
      "label": "eVTOL",
      "color": "#4e79a7",
      "group": "Technology",
      "title": "...",
      "size": 40
    }
    // ... more nodes
  ],
  "edges": [
    {
      "from": "...",
      "to": "...",
      "label": "MENTIONED_IN",
      "title": "MENTIONED_IN | Role: invented",
      "arrows": "to"
    }
    // ... more edges
  ]
}
```

### 2. Test Frontend

1. Open http://localhost:5173
2. Verify **light mode** (white background)
3. Click any technology node (e.g., "eVTOL")
4. Observe:
   - "Querying Neo4j..." loading indicator
   - Interactive vis.js graph appears
   - Node colors match categories
   - Relationships show labels
   - Click nodes to see properties

---

## 🔧 Troubleshooting

### Issue: "Failed to load graph - HTTP 404"

**Cause:** Backend not running

**Fix:**
```bash
cd src/api
python -m uvicorn main:app --reload --port 8000
```

### Issue: "Neo4j connection failed"

**Cause:** .env missing or invalid credentials

**Fix:** Verify .env has:
```bash
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
NEO4J_DATABASE=neo4j
```

### Issue: "Technology 'evtol' not found"

**Cause:** Neo4j Aura doesn't have test data with that ID

**Fix:**
1. Run Phase 3 ingestion: `python src/cli/ingest.py --industry evtol`
2. Or use a different tech_id from `data/catalog/technologies.json`

### Issue: Still seeing dark mode

**Cause:** Browser cached old localStorage

**Fix:**
```javascript
// Open browser console, run:
localStorage.clear();
// Refresh page
```

---

## 🎯 What Changed

### Frontend Changes

| File | Change |
|------|--------|
| `src/contexts/ThemeContext.tsx` | Force light mode as default (ignore localStorage) |
| `src/config/theme.ts` | Improved light mode colors (black text, darker separators) |
| `vite.config.ts` | Suppress vis-network source map warnings |
| `components/graph/Neo4jGraphViz.tsx` | Call real API instead of mock file |

### Backend Created

All files in `src/api/` (11 files total):
- ✅ FastAPI app with CORS
- ✅ Neo4j async driver
- ✅ Cypher query: `MATCH (t:Technology {id: $tech_id}) OPTIONAL MATCH (t)-[r]-(n) RETURN t, r, n`
- ✅ Neo4j → vis.js converter
- ✅ REST API endpoint

---

## 🔗 Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│ Browser (localhost:5173)                                │
│                                                         │
│  1. User clicks "eVTOL" node in Hype Cycle            │
│  2. React sends: POST /api/neo4j/subgraph              │
│     Body: {tech_id: "evtol"}                           │
└──────────────────┬──────────────────────────────────────┘
                   │
                   │ Vite proxy forwards to localhost:8000
                   ↓
┌─────────────────────────────────────────────────────────┐
│ FastAPI Backend (localhost:8000)                        │
│                                                         │
│  3. neo4j_routes.py receives request                   │
│  4. neo4j_service.py executes Cypher:                  │
│     MATCH (t:Technology {id: "evtol"})                 │
│     OPTIONAL MATCH (t)-[r]-(n)                         │
│     RETURN t, r, n                                     │
└──────────────────┬──────────────────────────────────────┘
                   │
                   │ Neo4j async driver
                   ↓
┌─────────────────────────────────────────────────────────┐
│ Neo4j Aura (cloud)                                      │
│                                                         │
│  5. Execute query on graph database                    │
│  6. Return nodes: Technology, Patents, Companies, etc. │
│  7. Return relationships: MENTIONED_IN, etc.           │
└──────────────────┬──────────────────────────────────────┘
                   │
                   │ Query results
                   ↓
┌─────────────────────────────────────────────────────────┐
│ FastAPI Backend                                         │
│                                                         │
│  8. vis_converter.py transforms to vis.js format       │
│  9. Return JSON: {nodes: [...], edges: [...]}          │
└──────────────────┬──────────────────────────────────────┘
                   │
                   │ HTTP Response
                   ↓
┌─────────────────────────────────────────────────────────┐
│ Browser                                                 │
│                                                         │
│  10. Neo4jGraphViz.tsx receives vis.js data            │
│  11. vis-network-react renders interactive graph       │
│  12. User explores technology relationships            │
└─────────────────────────────────────────────────────────┘
```

---

## ✨ Next Steps

1. **Start both servers** (backend + frontend)
2. **Test clicking nodes** - Verify Neo4j graph loads
3. **Check light mode** - Should be default
4. **Explore relationships** - Drag nodes, zoom, pan
5. **View evidence** (future enhancement) - Click to see top documents

Happy exploring! 🦥
