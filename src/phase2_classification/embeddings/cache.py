"""SQLite-based embedding cache to avoid recomputing embeddings."""

import hashlib
import json
import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """
    SQLite-based cache for text embeddings.
    
    Key format: sha256(model_name + text)
    Value: JSON-serialized embedding vector
    """
    
    def __init__(self, db_path: str = "data/classified/embeddings.db"):
        """
        Initialize embedding cache.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info(f"EmbeddingCache initialized at {self.db_path}")
    
    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    text_hash TEXT PRIMARY KEY,
                    model_name TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    dimensions INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_model_name 
                ON embeddings(model_name)
            """)
            conn.commit()
    
    @staticmethod
    def compute_hash(model_name: str, text: str) -> str:
        """
        Compute cache key from model name and text.
        
        Args:
            model_name: Name of the embedding model
            text: Text to embed
        
        Returns:
            SHA256 hash string
        """
        content = f"{model_name}:{text}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def get(self, model_name: str, text: str) -> Optional[np.ndarray]:
        """
        Get cached embedding for text.
        
        Args:
            model_name: Name of the embedding model
            text: Text to look up
        
        Returns:
            Embedding vector as numpy array, or None if not cached
        """
        text_hash = self.compute_hash(model_name, text)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT embedding, dimensions FROM embeddings WHERE text_hash = ?",
                (text_hash,)
            )
            row = cursor.fetchone()
            
            if row:
                embedding_bytes, dimensions = row
                embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
                return embedding.reshape(-1)
            
            return None
    
    def set(self, model_name: str, text: str, embedding: np.ndarray) -> None:
        """
        Cache embedding for text.
        
        Args:
            model_name: Name of the embedding model
            text: Original text
            embedding: Embedding vector
        """
        text_hash = self.compute_hash(model_name, text)
        embedding_bytes = embedding.astype(np.float32).tobytes()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO embeddings 
                (text_hash, model_name, embedding, dimensions)
                VALUES (?, ?, ?, ?)
            """, (text_hash, model_name, embedding_bytes, len(embedding)))
            conn.commit()
    
    def batch_get(
        self, 
        model_name: str, 
        texts: List[str]
    ) -> Tuple[Dict[str, np.ndarray], List[str]]:
        """
        Get cached embeddings for multiple texts.
        
        Args:
            model_name: Name of the embedding model
            texts: List of texts to look up
        
        Returns:
            Tuple of (found dict mapping text->embedding, list of missing texts)
        """
        found = {}
        missing = []
        
        # Compute all hashes
        hash_to_text = {self.compute_hash(model_name, t): t for t in texts}
        hashes = list(hash_to_text.keys())
        
        with sqlite3.connect(self.db_path) as conn:
            # Query in batches of 500 (SQLite limit)
            for i in range(0, len(hashes), 500):
                batch_hashes = hashes[i:i + 500]
                placeholders = ','.join('?' * len(batch_hashes))
                
                cursor = conn.execute(f"""
                    SELECT text_hash, embedding, dimensions 
                    FROM embeddings 
                    WHERE text_hash IN ({placeholders})
                """, batch_hashes)
                
                for row in cursor:
                    text_hash, embedding_bytes, dimensions = row
                    embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
                    text = hash_to_text[text_hash]
                    found[text] = embedding.reshape(-1)
        
        # Find missing texts
        found_texts = set(found.keys())
        missing = [t for t in texts if t not in found_texts]
        
        logger.debug(f"Cache hit: {len(found)}/{len(texts)}, missing: {len(missing)}")
        return found, missing
    
    def batch_set(
        self, 
        model_name: str, 
        text_embeddings: Dict[str, np.ndarray]
    ) -> None:
        """
        Cache multiple embeddings.
        
        Args:
            model_name: Name of the embedding model
            text_embeddings: Dict mapping text -> embedding vector
        """
        with sqlite3.connect(self.db_path) as conn:
            for text, embedding in text_embeddings.items():
                text_hash = self.compute_hash(model_name, text)
                embedding_bytes = embedding.astype(np.float32).tobytes()
                
                conn.execute("""
                    INSERT OR REPLACE INTO embeddings 
                    (text_hash, model_name, embedding, dimensions)
                    VALUES (?, ?, ?, ?)
                """, (text_hash, model_name, embedding_bytes, len(embedding)))
            
            conn.commit()
        
        logger.debug(f"Cached {len(text_embeddings)} embeddings")
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM embeddings")
            total = cursor.fetchone()[0]
            
            cursor = conn.execute("""
                SELECT model_name, COUNT(*) 
                FROM embeddings 
                GROUP BY model_name
            """)
            by_model = dict(cursor.fetchall())
        
        return {"total": total, "by_model": by_model}
    
    def clear(self, model_name: Optional[str] = None) -> int:
        """
        Clear cached embeddings.
        
        Args:
            model_name: If specified, only clear embeddings for this model
        
        Returns:
            Number of entries deleted
        """
        with sqlite3.connect(self.db_path) as conn:
            if model_name:
                cursor = conn.execute(
                    "DELETE FROM embeddings WHERE model_name = ?",
                    (model_name,)
                )
            else:
                cursor = conn.execute("DELETE FROM embeddings")
            
            deleted = cursor.rowcount
            conn.commit()
        
        logger.info(f"Cleared {deleted} cached embeddings")
        return deleted

