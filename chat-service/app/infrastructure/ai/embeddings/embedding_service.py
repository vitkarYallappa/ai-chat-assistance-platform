from typing import Dict, List, Any, Optional, Union
import numpy as np
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
import os
import json

class EmbeddingService:
    """
    Service for generating text embeddings and performing vector operations.
    Supports multiple embedding model backends.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the embedding service with configuration.
        
        Args:
            config: Dictionary containing embedding service configuration
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.model_type = config.get("model_type", "openai")  # openai, huggingface, custom
        self.model_name = config.get("model_name", "text-embedding-ada-002")
        self.embedding_dim = config.get("embedding_dim", 1536)  # Default for OpenAI ada-002
        self.client = None
        self.cache_dir = config.get("cache_dir")
        self.use_cache = config.get("use_cache", False)
        self.cache = {}
        
        # Initialize client based on model type
        self._initialize_client()
        
        # Load cache if enabled
        if self.use_cache and self.cache_dir:
            self._load_cache()
        
        self.logger.info(f"Initialized Embedding Service with model: {self.model_name}")
    
    def _initialize_client(self):
        """Initialize the appropriate client based on model type"""
        if self.model_type == "openai":
            import openai
            self.client = openai.OpenAI(
                api_key=self.config.get("api_key"),
                organization=self.config.get("organization")
            )
        elif self.model_type == "huggingface":
            try:
                from sentence_transformers import SentenceTransformer
                self.client = SentenceTransformer(self.model_name)
            except ImportError:
                self.logger.error("sentence-transformers package not installed")
        elif self.model_type == "custom":
            # For custom embedding model implementation
            self.client = self.config.get("custom_client")
    
    def _load_cache(self):
        """Load embedding cache from disk if available"""
        cache_file = os.path.join(self.cache_dir, "embedding_cache.json")
        try:
            if os.path.exists(cache_file):
                with open(cache_file, "r") as f:
                    cache_data = json.load(f)
                
                # Convert string keys back to embeddings
                for text, vector_str in cache_data.items():
                    self.cache[text] = np.array(json.loads(vector_str))
                
                self.logger.info(f"Loaded {len(self.cache)} embeddings from cache")
        except Exception as e:
            self.logger.error(f"Error loading embedding cache: {str(e)}")
            self.cache = {}
    
    def _save_cache(self):
        """Save embedding cache to disk if caching is enabled"""
        if not self.use_cache or not self.cache_dir:
            return
            
        cache_file = os.path.join(self.cache_dir, "embedding_cache.json")
        try:
            # Ensure cache directory exists
            os.makedirs(self.cache_dir, exist_ok=True)
            
            # Convert numpy arrays to lists for JSON serialization
            serializable_cache = {}
            for text, vector in self.cache.items():
                serializable_cache[text] = json.dumps(vector.tolist())
            
            with open(cache_file, "w") as f:
                json.dump(serializable_cache, f)
                
            self.logger.info(f"Saved {len(self.cache)} embeddings to cache")
        except Exception as e:
            self.logger.error(f"Error saving embedding cache: {str(e)}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def embed_text(self, text: str) -> np.ndarray:
        """
        Create a vector embedding from text.
        
        Args:
            text: Input text to embed
            
        Returns:
            Numpy array containing the embedding vector
        """
        if not text:
            # Return zero vector for empty text
            return np.zeros(self.embedding_dim)
        
        # Check cache first if enabled
        if self.use_cache and text in self.cache:
            return self.cache[text]
        
        try:
            if self.model_type == "openai":
                response = self.client.embeddings.create(
                    model=self.model_name,
                    input=text,
                    encoding_format="float"
                )
                embedding = np.array(response.data[0].embedding)
            
            elif self.model_type == "huggingface":
                embedding = self.client.encode(text)
                
            elif self.model_type == "custom" and self.client:
                # Call custom embedding function through client
                embedding = self.client.embed(text)
                
            else:
                self.logger.error(f"Unsupported model type: {self.model_type}")
                return np.zeros(self.embedding_dim)
            
            # Store in cache if enabled
            if self.use_cache:
                self.cache[text] = embedding
                
                # Periodically save cache
                if len(self.cache) % 100 == 0:
                    self._save_cache()
            
            return embedding
            
        except Exception as e:
            self.logger.error(f"Error generating embedding: {str(e)}")
            return np.zeros(self.embedding_dim)
    
    def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """
        Create embeddings for a batch of texts.
        
        Args:
            texts: List of input texts to embed
            
        Returns:
            List of numpy arrays containing embedding vectors
        """
        # Filter out empty texts
        valid_texts = [text for text in texts if text]
        
        # Check which texts are already in cache
        if self.use_cache:
            cached_embeddings = {text: self.cache[text] for text in valid_texts if text in self.cache}
            texts_to_embed = [text for text in valid_texts if text not in self.cache]
        else:
            cached_embeddings = {}
            texts_to_embed = valid_texts
        
        # If all texts are in cache, return cached embeddings
        if not texts_to_embed:
            return [cached_embeddings[text] for text in valid_texts]
        
        try:
            if self.model_type == "openai":
                # OpenAI supports batch embedding
                response = self.client.embeddings.create(
                    model=self.model_name,
                    input=texts_to_embed,
                    encoding_format="float"
                )
                new_embeddings = [np.array(item.embedding) for item in response.data]
                
            elif self.model_type == "huggingface":
                # HuggingFace supports batch encoding
                new_embeddings = self.client.encode(texts_to_embed)
                # Convert to list of numpy arrays if not already
                if isinstance(new_embeddings, np.ndarray) and len(new_embeddings.shape) == 2:
                    new_embeddings = [new_embeddings[i] for i in range(new_embeddings.shape[0])]
                
            elif self.model_type == "custom" and self.client:
                # Call custom batch embedding function
                new_embeddings = self.client.embed_batch(texts_to_embed)
                
            else:
                self.logger.error(f"Unsupported model type: {self.model_type}")
                new_embeddings = [np.zeros(self.embedding_dim) for _ in texts_to_embed]
            
            # Store new embeddings in cache
            if self.use_cache:
                for text, embedding in zip(texts_to_embed, new_embeddings):
                    self.cache[text] = embedding
                
                # Save cache after significant updates
                if len(texts_to_embed) > 10:
                    self._save_cache()
            
            # Combine cached and new embeddings in original order
            result = []
            for text in valid_texts:
                if text in cached_embeddings:
                    result.append(cached_embeddings[text])
                else:
                    # Find index in texts_to_embed
                    idx = texts_to_embed.index(text)
                    result.append(new_embeddings[idx])
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error generating batch embeddings: {str(e)}")
            return [np.zeros(self.embedding_dim) for _ in valid_texts]
    
    def cosine_similarity(self, vector1: np.ndarray, vector2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vector1: First embedding vector
            vector2: Second embedding vector
            
        Returns:
            Cosine similarity score (0-1)
        """
        if np.all(vector1 == 0) or np.all(vector2 == 0):
            return 0.0
            
        try:
            # Normalize vectors to unit length
            vector1_normalized = self.normalize_vector(vector1)
            vector2_normalized = self.normalize_vector(vector2)
            
            # Calculate dot product (cosine similarity for unit vectors)
            similarity = np.dot(vector1_normalized, vector2_normalized)
            
            # Ensure result is in valid range [0, 1]
            return float(max(0.0, min(1.0, similarity)))
            
        except Exception as e:
            self.logger.error(f"Error calculating cosine similarity: {str(e)}")
            return 0.0
    
    def normalize_vector(self, vector: np.ndarray) -> np.ndarray:
        """
        Normalize vector to unit length (L2 norm).
        
        Args:
            vector: Input vector
            
        Returns:
            Normalized vector with unit length
        """
        if np.all(vector == 0):
            return vector
            
        try:
            norm = np.linalg.norm(vector)
            if norm > 0:
                return vector / norm
            return vector
            
        except Exception as e:
            self.logger.error(f"Error normalizing vector: {str(e)}")
            return vector
    
    def find_most_similar(self, query_embedding: np.ndarray, 
                          embeddings: List[np.ndarray], 
                          top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Find the most similar embeddings to a query embedding.
        
        Args:
            query_embedding: Query embedding vector
            embeddings: List of embedding vectors to search
            top_k: Number of most similar embeddings to return
            
        Returns:
            List of dictionaries with index and similarity score
        """
        if not embeddings:
            return []
            
        try:
            # Calculate similarities
            similarities = [self.cosine_similarity(query_embedding, emb) for emb in embeddings]
            
            # Sort by similarity (descending) and get top_k
            indexed_similarities = list(enumerate(similarities))
            top_indices = sorted(indexed_similarities, key=lambda x: x[1], reverse=True)[:top_k]
            
            # Format results
            results = [
                {"index": idx, "similarity": float(score)} 
                for idx, score in top_indices
            ]
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error finding most similar embeddings: {str(e)}")
            return []