"""
Wrapper to run embeddings generation with automatic approval.
"""
import sys
import builtins

# Mock input to always return 'yes'
original_input = builtins.input
builtins.input = lambda prompt: 'yes'

try:
    # Import and run the embeddings script
    from graph.prerequisites_configuration import generate_embeddings as gen_emb
    gen_emb.generate_embeddings()
finally:
    # Restore original input
    builtins.input = original_input
