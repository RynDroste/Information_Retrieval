#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LaBSE Embedder
Generate semantic embeddings using LaBSE model for semantic search
"""

import os
import json
import numpy as np
from typing import List, Dict, Optional

try:
    from sentence_transformers import SentenceTransformer
    LABSE_AVAILABLE = True
except ImportError:
    LABSE_AVAILABLE = False
    # Only print warning when actually trying to use LaBSE, not on import
    pass

class LaBSEEmbedder:
    def __init__(self, model_name='sentence-transformers/LaBSE', cache_dir=None):
        """
        Initialize LaBSE embedder
        
        Args:
            model_name: Hugging Face model name
            cache_dir: Directory to cache the model
        """
        self.model = None
        self.model_name = model_name
        self.cache_dir = cache_dir
        
        if LABSE_AVAILABLE:
            try:
                print(f"Loading LaBSE model: {model_name}")
                print("Note: First run will download the model (~1.2GB)")
                self.model = SentenceTransformer(model_name, cache_folder=cache_dir)
                print("✓ LaBSE model loaded successfully")
            except Exception as e:
                print(f"✗ Failed to load LaBSE model: {e}")
                print("LaBSE features will be disabled")
                self.model = None
        else:
            print("Warning: sentence-transformers not installed. LaBSE features will be disabled.")
            print("Install with: pip3 install sentence-transformers")
            self.model = None
    
    def is_available(self):
        """Check if LaBSE is available"""
        return self.model is not None
    
    def generate_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Generate embedding for a single text
        
        Args:
            text: Input text string
            
        Returns:
            numpy array of embedding vector (768 dimensions) or None
        """
        if not self.is_available() or not text:
            return None
        
        try:
            embedding = self.model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
            return embedding
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None
    
    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 32) -> List[Optional[np.ndarray]]:
        """
        Generate embeddings for multiple texts (batch processing)
        
        Args:
            texts: List of input text strings
            batch_size: Batch size for processing
            
        Returns:
            List of numpy arrays (or None for failed embeddings)
        """
        if not self.is_available() or not texts:
            return [None] * len(texts)
        
        try:
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=True
            )
            return [emb for emb in embeddings]
        except Exception as e:
            print(f"Error generating batch embeddings: {e}")
            return [None] * len(texts)
    
    def generate_document_embedding(self, article: Dict) -> Optional[np.ndarray]:
        """
        Generate embedding for an article/document
        
        Args:
            article: Article dictionary with title, content, etc.
            
        Returns:
            numpy array of embedding vector or None
        """
        if not self.is_available():
            return None
        
        # Combine title and content for better semantic representation
        text_parts = []
        
        if article.get('title'):
            text_parts.append(article['title'])
        
        if article.get('menu_item') and article['menu_item'] != article.get('title'):
            text_parts.append(article['menu_item'])
        
        if article.get('content'):
            # Use first 500 characters of content to avoid too long text
            content = article['content'][:500]
            text_parts.append(content)
        
        if article.get('menu_category'):
            text_parts.append(article['menu_category'])
        
        combined_text = ' '.join(text_parts)
        
        if not combined_text.strip():
            return None
        
        return self.generate_embedding(combined_text)
    
    def save_embeddings(self, embeddings: Dict[str, np.ndarray], filepath: str):
        """
        Save embeddings to JSON file
        
        Args:
            embeddings: Dictionary mapping document IDs to embedding vectors
            filepath: Path to save the embeddings file
        """
        try:
            # Convert numpy arrays to lists for JSON serialization
            embeddings_dict = {
                doc_id: embedding.tolist() if embedding is not None else None
                for doc_id, embedding in embeddings.items()
            }
            
            os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else '.', exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(embeddings_dict, f, indent=2)
            
            print(f"✓ Saved {len(embeddings_dict)} embeddings to {filepath}")
            return True
        except Exception as e:
            print(f"✗ Failed to save embeddings: {e}")
            return False
    
    def load_embeddings(self, filepath: str) -> Dict[str, np.ndarray]:
        """
        Load embeddings from JSON file
        
        Args:
            filepath: Path to the embeddings file
            
        Returns:
            Dictionary mapping document IDs to embedding vectors
        """
        try:
            if not os.path.exists(filepath):
                print(f"Embeddings file not found: {filepath}")
                return {}
            
            with open(filepath, 'r', encoding='utf-8') as f:
                embeddings_dict = json.load(f)
            
            # Convert lists back to numpy arrays
            embeddings = {
                doc_id: np.array(embedding) if embedding is not None else None
                for doc_id, embedding in embeddings_dict.items()
            }
            
            print(f"✓ Loaded {len(embeddings)} embeddings from {filepath}")
            return embeddings
        except Exception as e:
            print(f"✗ Failed to load embeddings: {e}")
            return {}
    
    def compute_similarity(self, query_embedding: np.ndarray, doc_embedding: np.ndarray) -> float:
        """
        Compute cosine similarity between query and document embeddings
        
        Args:
            query_embedding: Query embedding vector
            doc_embedding: Document embedding vector
            
        Returns:
            Cosine similarity score (0-1)
        """
        if query_embedding is None or doc_embedding is None:
            return 0.0
        
        try:
            # Cosine similarity for normalized embeddings
            similarity = np.dot(query_embedding, doc_embedding)
            return float(similarity)
        except Exception as e:
            print(f"Error computing similarity: {e}")
            return 0.0

