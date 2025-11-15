#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Semantic Search Module
Hybrid search combining Solr keyword search with LaBSE semantic search
"""

import json
import os
import numpy as np
from typing import List, Dict, Tuple, Optional

try:
    from labse_embedder import LaBSEEmbedder
    LABSE_AVAILABLE = True
except ImportError:
    LABSE_AVAILABLE = False

class SemanticSearch:
    def __init__(self, embeddings_file='data/embeddings.json'):
        """
        Initialize semantic search
        
        Args:
            embeddings_file: Path to embeddings JSON file
        """
        self.embeddings_file = embeddings_file
        self.embeddings = {}
        self.labse_embedder = None
        self.load_embeddings()
        
        if LABSE_AVAILABLE:
            self.labse_embedder = LaBSEEmbedder()
    
    def load_embeddings(self):
        """Load pre-computed embeddings"""
        if not os.path.exists(self.embeddings_file):
            print(f"⚠ Embeddings file not found: {self.embeddings_file}")
            print("Run indexing with --use-labse to generate embeddings")
            return
        
        try:
            with open(self.embeddings_file, 'r', encoding='utf-8') as f:
                embeddings_dict = json.load(f)
            
            # Convert lists back to numpy arrays
            self.embeddings = {
                doc_id: np.array(embedding) if embedding is not None else None
                for doc_id, embedding in embeddings_dict.items()
            }
            
            print(f"✓ Loaded {len(self.embeddings)} embeddings")
        except Exception as e:
            print(f"✗ Failed to load embeddings: {e}")
            self.embeddings = {}
    
    def is_available(self):
        """Check if semantic search is available"""
        return len(self.embeddings) > 0 and self.labse_embedder is not None and self.labse_embedder.is_available()
    
    def search(self, query: str, solr_results: List[Dict], top_k: int = 10, 
               keyword_weight: float = 0.6, semantic_weight: float = 0.4) -> List[Dict]:
        """
        Hybrid search: combine Solr keyword results with semantic search
        
        Args:
            query: Search query string
            solr_results: Results from Solr keyword search
            top_k: Number of results to return
            keyword_weight: Weight for keyword search scores (0-1)
            semantic_weight: Weight for semantic search scores (0-1)
            
        Returns:
            List of re-ranked documents with combined scores
        """
        if not self.is_available():
            return solr_results[:top_k]
        
        # Generate query embedding
        query_embedding = self.labse_embedder.generate_embedding(query)
        if query_embedding is None:
            return solr_results[:top_k]
        
        # Compute semantic similarities
        doc_scores = {}
        for doc in solr_results:
            doc_id = doc.get('id')
            # Get Solr score and normalize (always compute keyword_score for all docs)
            # Handle both numeric and string score values
            solr_score = doc.get('score', 0)
            if isinstance(solr_score, str):
                try:
                    solr_score = float(solr_score)
                except (ValueError, TypeError):
                    solr_score = 0
            elif not isinstance(solr_score, (int, float)):
                solr_score = 0
            
            # Normalize Solr score (assuming max score is around 10, adjust as needed)
            # If score is very large, use a different normalization
            if solr_score > 100:
                normalized_solr_score = min(1.0, solr_score / 100.0)
            else:
                normalized_solr_score = min(1.0, solr_score / 10.0) if solr_score > 0 else 0
            
            if doc_id and doc_id in self.embeddings:
                doc_embedding = self.embeddings[doc_id]
                if doc_embedding is not None:
                    semantic_score = self.labse_embedder.compute_similarity(query_embedding, doc_embedding)
                    # Normalize semantic score to 0-1 range (cosine similarity is already -1 to 1, but normalized embeddings give 0-1)
                    semantic_score = max(0, semantic_score)  # Ensure non-negative
                    
                    # Combine scores
                    combined_score = (keyword_weight * normalized_solr_score) + (semantic_weight * semantic_score)
                    doc_scores[doc_id] = {
                        'doc': doc,
                        'keyword_score': normalized_solr_score,
                        'semantic_score': semantic_score,
                        'combined_score': combined_score
                    }
            else:
                # Document without embedding - use keyword score only
                doc_scores[doc_id or f"doc_{len(doc_scores)}"] = {
                    'doc': doc,
                    'keyword_score': normalized_solr_score,
                    'semantic_score': 0.0,
                    'combined_score': normalized_solr_score  # Use keyword score as combined score
                }
        
        # Sort by combined score
        ranked_docs = sorted(
            doc_scores.values(),
            key=lambda x: x['combined_score'],
            reverse=True
        )
        
        # Update documents with combined scores
        results = []
        for item in ranked_docs[:top_k]:
            doc = item['doc'].copy()
            doc['score'] = item['combined_score']
            doc['keyword_score'] = item['keyword_score']
            doc['semantic_score'] = item['semantic_score']
            results.append(doc)
        
        return results[:top_k]
    
    def rerank(self, query: str, candidates: List[Dict], top_k: int = 10) -> List[Dict]:
        """
        Re-rank candidate documents using semantic similarity
        
        Args:
            query: Search query string
            candidates: Candidate documents from initial search
            top_k: Number of results to return
            
        Returns:
            Re-ranked documents
        """
        return self.search(query, candidates, top_k, keyword_weight=0.3, semantic_weight=0.7)

