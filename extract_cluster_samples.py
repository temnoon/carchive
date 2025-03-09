#!/usr/bin/env python
import logging
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
from carchive.database.session import get_session
from carchive.database.models import Embedding, Message
import pandas as pd
import random
import json
from tqdm import tqdm

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)

def fetch_embeddings_with_text_samples(limit=None):
    """Fetch embedding vectors from database with text samples for testing"""
    with get_session() as session:
        query = session.query(Embedding)
        
        if limit:
            query = query.limit(limit)
            
        embeddings = query.all()
        
        embedding_data = []
        vectors = []
        
        for emb in embeddings:
            if emb.vector is not None:
                try:
                    # Convert to numpy array
                    vector_array = np.array(emb.vector)
                    if vector_array.size > 0:  # Only include non-empty vectors
                        # Check for text in meta_info
                        text_sample = None
                        if isinstance(emb.meta_info, dict):
                            # Try different possible keys for text content
                            for key in ['text', 'content', 'text_sample', 'context', 'source_text']:
                                if key in emb.meta_info and emb.meta_info[key]:
                                    text_sample = emb.meta_info[key]
                                    break
                        
                        # Skip if no text found (optional)
                        # if not text_sample:
                        #     continue
                            
                        vectors.append(vector_array)
                        embedding_data.append({
                            'id': emb.id,
                            'meta_info': emb.meta_info,
                            'parent_type': emb.parent_type,
                            'parent_id': emb.parent_id,
                            'parent_message_id': emb.parent_message_id,
                            'text_sample': text_sample
                        })
                except (ValueError, TypeError) as e:
                    logger.warning(f"Skipping embedding {emb.id} due to vector conversion error: {e}")
                    
        logger.info(f"Fetched {len(vectors)} embeddings")
        return embedding_data, vectors

def create_text_samples_by_querying_message_content(embedding_data, cluster_assignments, n_clusters=10, samples_per_cluster=5):
    """Create text samples by querying the messages table"""
    # Query the messages table for random examples
    all_samples = {}
    
    # Create DataFrame for easier analysis
    df = pd.DataFrame({
        'embedding_id': [data['id'] for data in embedding_data],
        'cluster': cluster_assignments,
        'text_sample': [data.get('text_sample') for data in embedding_data]
    })
    
    # Group by cluster
    for cluster_id in range(n_clusters):
        # Get embeddings for this cluster
        cluster_embeddings = df[df['cluster'] == cluster_id]
        
        # Skip if empty cluster
        if len(cluster_embeddings) == 0:
            continue
            
        # Find embeddings with text samples
        embeddings_with_text = cluster_embeddings[cluster_embeddings['text_sample'].notnull()]
        
        if len(embeddings_with_text) >= samples_per_cluster:
            # If we have enough embeddings with text, use those
            samples = embeddings_with_text.sample(min(samples_per_cluster, len(embeddings_with_text)))
            samples_list = samples['text_sample'].tolist()
        else:
            # Otherwise, we need to query the messages table for examples
            # Query messages with content closest to the cluster centroid
            samples_list = []
            
            # Query random messages from the messages table
            with get_session() as session:
                try:
                    # Get the last 1000 messages by id
                    messages = session.query(Message.id, Message.content, Message.role).order_by(
                        Message.id.desc()
                    ).limit(1000).all()
                    
                    if messages:
                        # Randomly sample
                        random_messages = random.sample(messages, min(samples_per_cluster, len(messages)))
                        
                        for msg_id, content, role in random_messages:
                            # Maximum 200 characters for sample
                            if content:
                                samples_list.append(f"[{role}] {content[:200]}..." if len(content) > 200 else f"[{role}] {content}")
                except Exception as e:
                    logger.error(f"Error querying messages: {e}")
        
        # Store samples for this cluster
        all_samples[cluster_id] = samples_list
        
    return all_samples

def cluster_kmeans(vectors, n_clusters=10):
    """Cluster vectors using KMeans algorithm"""
    if not vectors:
        return []
        
    # Stack vectors into a single numpy array
    X = np.vstack(vectors)
    
    # Apply KMeans clustering
    logger.info(f"Clustering {len(vectors)} embeddings into {n_clusters} clusters...")
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    cluster_assignments = kmeans.fit_predict(X)
    
    # Return cluster assignments and centroids
    return cluster_assignments, kmeans.cluster_centers_

def main():
    # Step 1: Fetch embeddings
    embedding_data, vectors = fetch_embeddings_with_text_samples(limit=None)
    
    if not vectors:
        logger.error("No embeddings found!")
        return
    
    # Step 2: Cluster embeddings
    n_clusters = 10  # We'll use 10 clusters for analysis
    cluster_assignments, centroids = cluster_kmeans(vectors, n_clusters=n_clusters)
    
    # Step 3: Create samples
    logger.info("Creating text samples by querying messages...")
    text_samples = create_text_samples_by_querying_message_content(
        embedding_data, cluster_assignments, n_clusters, samples_per_cluster=10
    )
    
    # Step 4: Output results to a report file
    with open('cluster_text_samples.json', 'w') as f:
        json.dump(text_samples, f, indent=4)
        
    # Also output as readable text
    with open('cluster_text_samples.txt', 'w') as f:
        f.write(f"Text samples from {len(vectors)} embeddings in {n_clusters} clusters\n")
        f.write("=" * 80 + "\n\n")
        
        # Get cluster sizes
        cluster_counts = {}
        for c in cluster_assignments:
            if c not in cluster_counts:
                cluster_counts[c] = 0
            cluster_counts[c] += 1
            
        # Sort clusters by size
        sorted_clusters = sorted(cluster_counts.items(), key=lambda x: x[1], reverse=True)
        
        for cluster_id, count in sorted_clusters:
            percentage = (count / len(cluster_assignments)) * 100
            f.write(f"Cluster {cluster_id}: {count} embeddings ({percentage:.1f}%)\n")
            f.write("-" * 40 + "\n")
            
            # Write samples
            if cluster_id in text_samples:
                for i, sample in enumerate(text_samples[cluster_id]):
                    # Truncate long samples for readability
                    sample_text = sample[:500] + "..." if len(sample) > 500 else sample
                    f.write(f"Sample {i+1}:\n{sample_text}\n\n")
            else:
                f.write("No text samples available for this cluster\n")
                
            f.write("\n")
            
    logger.info("Analysis complete. Results saved to 'cluster_text_samples.txt' and 'cluster_text_samples.json'")
        
if __name__ == "__main__":
    main()