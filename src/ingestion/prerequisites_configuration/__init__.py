"""
Graph Prerequisites Configuration
===================================

Scripts to setup all Neo4j graph prerequisites before running multi-agent system.

Workflow:
1. 01_create_indexes.py - Create temporal and composite indexes (fast, free)
2. 02_generate_embeddings.py - Generate OpenAI embeddings (10-15 min, $0.20-1.00)
3. 03_create_fulltext_index.py - Create BM25 full-text index (fast, free)
4. 04_create_vector_index.py - Create vector similarity index (fast, free)
5. 05_compute_communities.py - Compute 6 community detection variants (5-10 min, free)
6. 06_compute_graph_algorithms.py - Compute PageRank and centrality (5-10 min, free)
7. 07_validate_prerequisites.py - Validate all prerequisites (fast, free)

Master orchestrator:
- run_all_prerequisites.py - Run all scripts in order with approval prompts

Usage:
    python graph/prerequisites_configuration/01_create_indexes.py
    python graph/prerequisites_configuration/02_generate_embeddings.py
    ...
    python graph/prerequisites_configuration/run_all_prerequisites.py
"""
