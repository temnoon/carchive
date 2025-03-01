# carchive2/src/carchive2/embeddings/clustering.py

import numpy as np
from typing import List, Dict, Any, Tuple
from sklearn.cluster import KMeans, DBSCAN
from sklearn.metrics import silhouette_score
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import PCA
import uuid
import logging
import matplotlib.pyplot as plt
from sqlalchemy import func
from carchive.database.session import get_session
from carchive.database.models import Embedding, Message, Collection, CollectionItem
from carchive.collections.schemas import CollectionCreateSchema, CollectionItemSchema

logger = logging.getLogger(__name__)

class EmbeddingClusterer:
    """Manages clustering operations on embeddings."""
    
    @staticmethod
    def fetch_embeddings(limit: int = None) -> Tuple[List[np.ndarray], List[uuid.UUID], List[uuid.UUID]]:
        """
        Fetch embeddings from database.
        
        Returns:
            Tuple containing:
            - List of embedding vectors as numpy arrays
            - List of embedding IDs
            - List of message IDs (may contain None values)
        """
        with get_session() as session:
            logger.info("Checking for linked embeddings...")
            
            # First check if we have embeddings with parent_message_id
            count = session.query(Embedding).filter(
                Embedding.parent_message_id.isnot(None)
            ).count()
            
            logger.info(f"Found {count} embeddings with parent_message_id")
            
            if count > 0:
                # Use the direct parent_message_id approach
                query = session.query(
                    Embedding.vector,
                    Embedding.id,
                    Embedding.parent_message_id
                ).filter(
                    Embedding.parent_message_id.isnot(None)
                )
                
                if limit:
                    query = query.limit(limit)
                    
                results = query.all()
                
                vectors = [np.array(result[0]) for result in results]
                embedding_ids = [result[1] for result in results]
                message_ids = [result[2] for result in results]
            else:
                # Alternative approach: join with messages through meta_info
                # This is based on the observation that some systems may link embeddings to messages
                # via metadata rather than direct foreign keys
                logger.info("No direct parent_message_id links found. Looking for connections in metadata...")
                
                # Get all embeddings first
                embeddings_query = session.query(Embedding)
                
                if limit:
                    embeddings_query = embeddings_query.limit(limit)
                
                embeddings = embeddings_query.all()
                
                vectors = []
                embedding_ids = []
                message_ids = []
                
                # For each embedding, try to find a message ID in meta_info
                for emb in embeddings:
                    if emb.vector is not None and isinstance(emb.meta_info, dict):
                        # Check if meta_info has a message_id field
                        msg_id = emb.meta_info.get('message_id')
                        if msg_id:
                            vectors.append(np.array(emb.vector))
                            embedding_ids.append(emb.id)
                            message_ids.append(uuid.UUID(msg_id))
                
                logger.info(f"Found {len(vectors)} embeddings with message IDs in metadata")
                
                # If we still have no results, just use all embeddings and we'll create synthetic links
                if not vectors and embeddings:
                    logger.info("No metadata links found. Using embeddings only...")
                    # Use embeddings only without trying to link to messages
                    vectors = []
                    embedding_ids = []
                    message_ids = []
                    
                    for emb in embeddings:
                        if emb.vector is not None:
                            try:
                                # Convert to numpy array - handle potential serialization issues
                                vector = np.array(emb.vector)
                                if vector.size > 0:  # Only include non-empty vectors
                                    vectors.append(vector)
                                    embedding_ids.append(emb.id)
                                    message_ids.append(None)  # No message ID
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Skipping embedding {emb.id} due to vector conversion error: {e}")
            
            logger.info(f"Returning {len(vectors)} embeddings for clustering")
            return vectors, embedding_ids, message_ids
    
    @staticmethod
    def cluster_kmeans(
        vectors: List[np.ndarray],
        n_clusters: int = 10
    ) -> List[int]:
        """
        Cluster embeddings using KMeans.
        
        Args:
            vectors: List of embedding vectors
            n_clusters: Number of clusters to create
            
        Returns:
            List of cluster assignments
        """
        if not vectors:
            return []
            
        # Convert to numpy array
        X = np.vstack(vectors)
        
        # Apply KMeans clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        cluster_assignments = kmeans.fit_predict(X)
        
        # Evaluate clusters
        if n_clusters > 1 and len(X) > n_clusters:
            silhouette_avg = silhouette_score(X, cluster_assignments)
            logger.info(f"Silhouette score: {silhouette_avg:.4f}")
        
        return cluster_assignments.tolist()
    
    @staticmethod
    def cluster_dbscan(
        vectors: List[np.ndarray],
        eps: float = 0.5,
        min_samples: int = 5
    ) -> List[int]:
        """
        Cluster embeddings using DBSCAN.
        
        Args:
            vectors: List of embedding vectors
            eps: Maximum distance between samples
            min_samples: Minimum number of samples in a cluster
            
        Returns:
            List of cluster assignments
        """
        if not vectors:
            return []
            
        X = np.vstack(vectors)
        
        # Apply DBSCAN clustering
        dbscan = DBSCAN(eps=eps, min_samples=min_samples)
        cluster_assignments = dbscan.fit_predict(X)
        
        n_clusters = len(set(cluster_assignments)) - (1 if -1 in cluster_assignments else 0)
        logger.info(f"DBSCAN found {n_clusters} clusters, with {list(cluster_assignments).count(-1)} outliers")
        
        return cluster_assignments.tolist()
        
    @staticmethod
    def visualize_clusters(
        vectors: List[np.ndarray],
        cluster_assignments: List[int],
        n_components: int = 2,
        output_path: str = "cluster_visualization.png"
    ) -> None:
        """
        Visualize clusters using PCA for dimensionality reduction.
        
        Args:
            vectors: List of embedding vectors
            cluster_assignments: List of cluster assignments
            n_components: Number of PCA components for visualization
            output_path: Path to save the visualization image
        """
        if not vectors:
            logger.warning("No vectors provided for visualization")
            return
            
        # Stack vectors into a single numpy array
        X = np.vstack(vectors)
        
        # Apply PCA for visualization
        logger.info(f"Reducing dimensions with PCA...")
        pca = PCA(n_components=n_components)
        X_pca = pca.fit_transform(X)
        
        # Create scatter plot
        plt.figure(figsize=(10, 8))
        scatter = plt.scatter(X_pca[:, 0], X_pca[:, 1], c=cluster_assignments, cmap='viridis', s=5, alpha=0.7)
        
        # Add colorbar and handle outliers specially
        if -1 in cluster_assignments:
            # Get unique labels excluding outliers for colorbar
            unique_labels = sorted(set(cluster_assignments))
            if -1 in unique_labels:
                unique_labels.remove(-1)
                
            # Create a color map that handles outliers specially (make them black)
            from matplotlib.colors import ListedColormap
            import matplotlib.cm as cm
            viridis = cm.get_cmap('viridis', len(unique_labels))
            colors = viridis(np.linspace(0, 1, len(unique_labels)))
            cmap = ListedColormap(colors)
            
            # Recolor the scatter plot
            outlier_mask = np.array(cluster_assignments) == -1
            normal_mask = ~outlier_mask
            
            plt.scatter(X_pca[outlier_mask, 0], X_pca[outlier_mask, 1], c='black', s=5, alpha=0.3, label='Outliers')
            scatter = plt.scatter(X_pca[normal_mask, 0], X_pca[normal_mask, 1], 
                               c=np.array(cluster_assignments)[normal_mask], cmap=cmap, s=5, alpha=0.7)
                               
            plt.colorbar(scatter, label='Cluster')
            plt.legend()
        else:
            plt.colorbar(scatter, label='Cluster')
            
        # Calculate explained variance
        explained_var = pca.explained_variance_ratio_
        
        # Set plot labels
        plt.title(f'PCA Visualization of {len(vectors)} Embeddings in {len(set(cluster_assignments)) - (1 if -1 in cluster_assignments else 0)} Clusters')
        plt.xlabel(f'PCA Component 1 ({explained_var[0]:.1%} variance)')
        plt.ylabel(f'PCA Component 2 ({explained_var[1]:.1%} variance)')
        
        # Save the plot to a file
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        logger.info(f"Visualization saved as '{output_path}'")
        plt.close()
    
    @staticmethod
    def visualize_hierarchical_clusters(
        vectors: List[np.ndarray],
        primary_assignments: List[int],
        secondary_assignments: List[List[int]] = None,
        output_path: str = "hierarchical_clusters.png"
    ) -> None:
        """
        Visualize hierarchical clustering with primary and optional secondary clusters.
        
        Args:
            vectors: List of embedding vectors
            primary_assignments: List of primary cluster assignments
            secondary_assignments: Optional list of lists containing secondary clusters per primary cluster
            output_path: Path to save the visualization image
        """
        if not vectors:
            logger.warning("No vectors provided for visualization")
            return
            
        # Stack vectors into a single numpy array
        X = np.vstack(vectors)
        
        # Apply PCA for visualization
        logger.info(f"Reducing dimensions with PCA...")
        pca = PCA(n_components=2)
        X_pca = pca.fit_transform(X)
        
        # Create main figure
        plt.figure(figsize=(12, 10))
        
        # Plot primary clusters
        scatter = plt.scatter(X_pca[:, 0], X_pca[:, 1], c=primary_assignments, cmap='tab10', s=10, alpha=0.7)
        
        # Add cluster centroids for primary clusters
        primary_clusters = set(primary_assignments)
        for cluster_id in primary_clusters:
            # Get indices for this cluster
            indices = [i for i, c in enumerate(primary_assignments) if c == cluster_id]
            if not indices:
                continue
                
            # Calculate centroid
            centroid = X_pca[indices].mean(axis=0)
            
            # Plot centroid
            plt.plot(centroid[0], centroid[1], 'o', markerfacecolor='white', 
                     markeredgecolor='black', markersize=12, alpha=0.9)
            
            # Add label
            plt.text(centroid[0], centroid[1], str(cluster_id), 
                    fontsize=12, ha='center', va='center', weight='bold')
        
        # Calculate explained variance
        explained_var = pca.explained_variance_ratio_
        
        # Set plot labels
        plt.title(f'Hierarchical Clustering Visualization of {len(vectors)} Embeddings')
        plt.xlabel(f'PCA Component 1 ({explained_var[0]:.1%} variance)')
        plt.ylabel(f'PCA Component 2 ({explained_var[1]:.1%} variance)')
        plt.colorbar(scatter, label='Primary Cluster')
        
        # Save the plot to a file
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        logger.info(f"Visualization saved as '{output_path}'")
        plt.close()
        
    @staticmethod
    def extract_cluster_samples(
        vectors: List[np.ndarray],
        embedding_ids: List[uuid.UUID],
        message_ids: List[uuid.UUID],
        cluster_assignments: List[int],
        samples_per_cluster: int = 5
    ) -> dict:
        """
        Extract sample messages from each cluster.
        
        Args:
            vectors: List of embedding vectors
            embedding_ids: List of embedding IDs
            message_ids: List of message IDs
            cluster_assignments: List of cluster assignments
            samples_per_cluster: Number of samples to extract per cluster
            
        Returns:
            Dictionary mapping cluster IDs to lists of sample content
        """
        # Stack vectors
        X = np.vstack(vectors)
        
        # Find cluster centroids
        cluster_samples = {}
        unique_clusters = sorted(set(cluster_assignments))
        
        # Calculate cluster centroids
        centroids = {}
        for cluster_id in unique_clusters:
            if cluster_id == -1:  # Skip outliers
                continue
                
            # Get indices for this cluster
            indices = [i for i, c in enumerate(cluster_assignments) if c == cluster_id]
            if not indices:
                continue
                
            # Calculate centroid
            cluster_vectors = X[indices]
            centroid = np.mean(cluster_vectors, axis=0)
            centroids[cluster_id] = centroid
            
            # Find closest vectors to centroid
            similarities = cosine_similarity([centroid], cluster_vectors)[0]
            closest_indices = np.argsort(similarities)[-samples_per_cluster:][::-1]
            
            # Map back to original indices
            original_indices = [indices[i] for i in closest_indices]
            
            # Try to get message content for these embeddings
            cluster_samples[cluster_id] = []
            
            for idx in original_indices:
                # Check if we have a message ID
                if idx < len(message_ids) and message_ids[idx]:
                    # Try to fetch message content
                    with get_session() as session:
                        try:
                            message = session.query(Message).filter(
                                Message.id == str(message_ids[idx])
                            ).first()
                            
                            if message and message.content:
                                # Truncate to avoid very long samples
                                content = message.content
                                if len(content) > 1000:
                                    content = content[:1000] + "..."
                                    
                                cluster_samples[cluster_id].append({
                                    "message_id": str(message_ids[idx]),
                                    "embedding_id": str(embedding_ids[idx]) if idx < len(embedding_ids) else None,
                                    "role": message.role if hasattr(message, "role") else "unknown",
                                    "content": content
                                })
                        except Exception as e:
                            logger.warning(f"Error fetching message {message_ids[idx]}: {e}")
            
            # If we couldn't get enough content, try random sampling
            if len(cluster_samples[cluster_id]) < samples_per_cluster:
                with get_session() as session:
                    try:
                        # Get a few random messages
                        random_messages = session.query(Message).order_by(
                            func.random()
                        ).limit(samples_per_cluster - len(cluster_samples[cluster_id])).all()
                        
                        for message in random_messages:
                            if message.content:
                                content = message.content
                                if len(content) > 1000:
                                    content = content[:1000] + "..."
                                    
                                cluster_samples[cluster_id].append({
                                    "message_id": str(message.id),
                                    "embedding_id": None,
                                    "role": message.role if hasattr(message, "role") else "unknown",
                                    "content": content,
                                    "note": "Random sample (not from cluster)"
                                })
                    except Exception as e:
                        logger.warning(f"Error fetching random messages: {e}")
        
        return cluster_samples
    
    @staticmethod
    def generate_topic_for_sample_texts(sample_texts: List[str], provider: str = "ollama") -> dict:
        """
        Generate a topic description for a collection of sample texts using an LLM.
        
        Args:
            sample_texts: List of text samples from the cluster
            provider: LLM provider to use for generation
            
        Returns:
            Dictionary with topic information
        """
        if not sample_texts:
            return {
                "topic": "Unknown Topic",
                "keywords": [],
                "confidence": 0.0
            }
            
        # Combine sample texts with a separator
        combined_texts = "\n---\n".join(sample_texts[:5])
        
        # Use the content task manager to generate the topic
        from carchive.pipelines.content_tasks import ContentTaskManager
        
        task_mgr = ContentTaskManager(provider=provider)
        
        # Create a custom prompt for topic extraction
        prompt_template = """
        Analyze the following sample texts from a cluster of related messages.
        Generate a concise topic label (3-7 words) that best represents the central theme.
        Also extract 3-5 keywords and assign a confidence score (0.0-1.0).
        
        Sample texts:
        {content}
        
        Respond in this JSON format:
        {
          "topic": "Concise topic label",
          "keywords": ["keyword1", "keyword2", "keyword3"],
          "confidence": 0.85,
          "description": "A 1-2 sentence description of what this cluster contains"
        }
        """
        
        try:
            # We'll create a temporary "dummy" message to process
            # The actual message content doesn't matter since we're using a custom template
            # that will insert the combined_texts into the {content} placeholder
            import uuid
            from carchive.database.session import get_session
            from carchive.database.models import Message, AgentOutput
            
            temp_msg_id = str(uuid.uuid4())
            with get_session() as session:
                temp_msg = Message(
                    id=temp_msg_id,
                    content="[TEMP] Generate topic for cluster",
                    meta_info={"is_temporary": True}
                )
                session.add(temp_msg)
                session.commit()
            
            # Process with LLM
            result = task_mgr.run_task_for_message(
                message_id=temp_msg_id,
                task="cluster_topic",
                context=combined_texts,
                prompt_template=prompt_template
            )
            
            # Clean up temporary message
            with get_session() as session:
                session.query(Message).filter_by(id=temp_msg_id).delete()
                session.commit()
            
            # Try to parse the result as JSON
            import json
            try:
                topic_info = json.loads(result.content)
                return topic_info
            except json.JSONDecodeError:
                # If JSON parsing fails, extract what we can from the text
                logger.warning(f"Failed to parse topic generation result as JSON: {result.content}")
                return {
                    "topic": result.content[:50] + "..." if len(result.content) > 50 else result.content,
                    "keywords": [],
                    "confidence": 0.5,
                    "raw_response": result.content
                }
                
        except Exception as e:
            logger.error(f"Error generating topic: {e}")
            return {
                "topic": "Error Generating Topic",
                "keywords": [],
                "confidence": 0.0,
                "error": str(e)
            }
    
    @staticmethod
    def create_collections_from_clusters(
        message_ids: List[uuid.UUID],
        cluster_assignments: List[int],
        collection_prefix: str = "Cluster",
        exclude_outliers: bool = True,
        max_clusters: int = None,
        embedding_ids: List[uuid.UUID] = None,
        generate_topics: bool = False,
        topic_provider: str = "ollama",
        parent_collection_id: str = None
    ) -> List[Collection]:
        """
        Create collections from clusters.
        
        Args:
            message_ids: List of message IDs (may contain None values)
            cluster_assignments: List of cluster assignments
            collection_prefix: Prefix for collection names
            exclude_outliers: Whether to exclude outliers (-1 cluster)
            max_clusters: Maximum number of clusters to create collections for
            embedding_ids: Optional list of embedding IDs (used when message_ids might have None values)
            generate_topics: Whether to generate topic descriptions using LLM
            topic_provider: Provider to use for topic generation
            
        Returns:
            List of created collections
        """
        # Track if we have a "messages only" clustering or an "embeddings only" clustering
        has_valid_messages = any(msg_id is not None for msg_id in message_ids)
        
        # Group by cluster
        clusters = {}
        for i, cluster_id in enumerate(cluster_assignments):
            if exclude_outliers and cluster_id == -1:
                continue
                
            if cluster_id not in clusters:
                clusters[cluster_id] = []
            
            msg_id = message_ids[i] if i < len(message_ids) else None
            emb_id = embedding_ids[i] if embedding_ids and i < len(embedding_ids) else None
            
            # Add item to cluster with either message_id or embedding_id or both
            clusters[cluster_id].append((msg_id, emb_id, i))  # Store original index too
        
        # Sort clusters by size (largest first)
        sorted_clusters = sorted(clusters.items(), key=lambda x: len(x[1]), reverse=True)
        
        # Limit number of clusters if specified
        if max_clusters and max_clusters < len(sorted_clusters):
            sorted_clusters = sorted_clusters[:max_clusters]
        
        created_collections = []
        
        # Create a collection for each cluster
        for cluster_id, items in sorted_clusters:
            # Extract message IDs and embedding IDs from items
            msg_ids = [item[0] for item in items if item[0] is not None]
            emb_ids = [item[1] for item in items if item[1] is not None]
            
            if not msg_ids and not emb_ids:
                logger.warning(f"Cluster {cluster_id} has no valid IDs. Skipping.")
                continue
            
            # Get sample messages to determine topic if we have message IDs
            sample_texts = []
            if msg_ids:
                with get_session() as session:
                    try:
                        sample_messages = session.query(Message.content).filter(
                            Message.id.in_([str(msg_id) for msg_id in msg_ids[:5]])
                        ).all()
                        
                        sample_texts = [msg[0] for msg in sample_messages if msg[0]]
                    except Exception as e:
                        logger.error(f"Error fetching sample messages: {e}")
            
            # For embeddings-only clustering, try to get some sample text from embeddings
            if not sample_texts and emb_ids:
                with get_session() as session:
                    try:
                        # Try to get meta_info from embeddings to find some context
                        sample_embeddings = session.query(Embedding.meta_info).filter(
                            Embedding.id.in_([str(emb_id) for emb_id in emb_ids[:5]])
                        ).all()
                        
                        for emb_meta in sample_embeddings:
                            if isinstance(emb_meta[0], dict):
                                # Try to extract some context from meta_info
                                context = emb_meta[0].get('context') or emb_meta[0].get('text_sample')
                                if context:
                                    sample_texts.append(str(context))
                    except Exception as e:
                        logger.error(f"Error fetching sample embeddings: {e}")
            
            # Determine what kind of collection we're creating
            if msg_ids:
                item_type = "messages"
                item_count = len(msg_ids)
            else:
                item_type = "embeddings"
                item_count = len(emb_ids)
            
            # Generate topic if requested and we have sample texts
            topic_info = None
            collection_name = f"{collection_prefix} {cluster_id} ({item_count} {item_type})"
            
            if generate_topics and sample_texts:
                topic_info = EmbeddingClusterer.generate_topic_for_sample_texts(
                    sample_texts, 
                    provider=topic_provider
                )
                
                # Update collection name with the topic
                if topic_info and topic_info.get("topic"):
                    collection_name = f"{topic_info['topic']} ({item_count} {item_type})"
            
            # Create collection items
            collection_items = []
            if msg_ids:
                # Normal message-based collection items
                collection_items = [
                    CollectionItemSchema(message_id=str(msg_id))
                    for msg_id in msg_ids
                ]
            else:
                # Create a special collection that just references the embeddings in meta_info
                # (Since CollectionItem doesn't directly support embedding_id)
                collection_items = [
                    CollectionItemSchema(
                        meta_info={"embedding_id": str(emb_id)}
                    )
                    for emb_id in emb_ids
                ]
            
            if not collection_items:
                logger.warning(f"No valid items for cluster {cluster_id}. Skipping.")
                continue
            
            # Prepare meta_info with both sample texts and topic info if available
            meta_info = {
                "cluster_id": cluster_id,
                "item_count": len(collection_items),
                "item_type": item_type,
                "sample_texts": sample_texts[:5] if sample_texts else ["No sample texts available"]
            }
            
            # Add topic info to meta_info if available
            if topic_info:
                meta_info["topic"] = topic_info
            
            # Add parent collection id if provided
            if parent_collection_id:
                meta_info["parent_collection_id"] = parent_collection_id
            
            collection_data = CollectionCreateSchema(
                name=collection_name,
                items=collection_items,
                meta_info=meta_info
            )
            
            from carchive.collections.collection_manager import CollectionManager
            collection = CollectionManager.create_collection(collection_data)
            created_collections.append(collection)
            
        return created_collections