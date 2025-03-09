#!/usr/bin/env python
import logging
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
from carchive.database.session import get_session
from carchive.database.models import Embedding, Message
import pandas as pd
from tqdm import tqdm

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)

def fetch_embeddings(limit=None):
    """Fetch embedding vectors from database"""
    with get_session() as session:
        query = session.query(Embedding.id, Embedding.vector, Embedding.meta_info, Embedding.parent_type, Embedding.parent_id)
        
        if limit:
            query = query.limit(limit)
            
        results = query.all()
        
        embedding_data = []
        vectors = []
        
        for emb_id, vector, meta_info, parent_type, parent_id in results:
            if vector is not None:
                try:
                    # Convert to numpy array
                    vector_array = np.array(vector)
                    if vector_array.size > 0:  # Only include non-empty vectors
                        vectors.append(vector_array)
                        embedding_data.append({
                            'id': emb_id,
                            'meta_info': meta_info,
                            'parent_type': parent_type,
                            'parent_id': parent_id
                        })
                except (ValueError, TypeError) as e:
                    logger.warning(f"Skipping embedding {emb_id} due to vector conversion error: {e}")
                    
        logger.info(f"Fetched {len(vectors)} embeddings")
        return embedding_data, vectors

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

def find_closest_to_centroid(vectors, centroids, cluster_assignments, embedding_data, n_samples=5):
    """Find embeddings closest to each cluster centroid"""
    closest_per_cluster = {}
    
    # Stack vectors
    X = np.vstack(vectors)
    
    # Calculate closest for each centroid
    for cluster_id, centroid in enumerate(centroids):
        # Get indices for this cluster
        cluster_indices = [i for i, c in enumerate(cluster_assignments) if c == cluster_id]
        
        if not cluster_indices:
            closest_per_cluster[cluster_id] = []
            continue
            
        # Get cluster vectors
        cluster_vectors = X[cluster_indices]
        
        # Calculate distances to centroid
        similarities = cosine_similarity([centroid], cluster_vectors)[0]
        
        # Find closest
        closest_indices = np.argsort(similarities)[-n_samples:][::-1]  # Get last N, reversed for descending order
        
        # Map back to original indices
        closest_original_indices = [cluster_indices[i] for i in closest_indices]
        
        # Store results
        closest_per_cluster[cluster_id] = [
            {
                'embedding_id': embedding_data[i]['id'],
                'meta_info': embedding_data[i]['meta_info'],
                'parent_type': embedding_data[i]['parent_type'],
                'parent_id': embedding_data[i]['parent_id'],
                'similarity': similarities[closest_indices[idx]]
            }
            for idx, i in enumerate(closest_original_indices)
        ]
    
    return closest_per_cluster

def analyze_content_in_clusters(embedding_data, cluster_assignments, n_clusters=10):
    """Analyze embedding content by cluster"""
    # Create DataFrame for analysis
    df = pd.DataFrame({
        'embedding_id': [data['id'] for data in embedding_data],
        'parent_type': [data['parent_type'] for data in embedding_data],
        'cluster': cluster_assignments
    })
    
    # Get cluster sizes
    cluster_sizes = df['cluster'].value_counts().sort_values(ascending=False)
    
    # Print results
    print("\nCluster distribution:")
    for cluster_id, count in cluster_sizes.items():
        percentage = (count / len(df)) * 100
        print(f"Cluster {cluster_id}: {count} embeddings ({percentage:.1f}%)")
        
        # Analyze parent types in this cluster
        parent_types = df[df['cluster'] == cluster_id]['parent_type'].value_counts()
        for parent_type, type_count in parent_types.items():
            type_percentage = (type_count / count) * 100
            print(f"  - {parent_type}: {type_count} ({type_percentage:.1f}%)")
            
    return df

def main():
    # Step 1: Fetch embeddings
    embedding_data, vectors = fetch_embeddings(limit=None)
    
    if not vectors:
        logger.error("No embeddings found!")
        return
    
    # Step 2: Cluster embeddings
    n_clusters = 10  # We'll use 10 clusters for analysis
    cluster_assignments, centroids = cluster_kmeans(vectors, n_clusters=n_clusters)
    
    # Step 3: Analyze clusters
    df = analyze_content_in_clusters(embedding_data, cluster_assignments, n_clusters)
    
    # Step 4: Find representative embeddings for each cluster
    logger.info("Finding closest embeddings to centroids...")
    closest_embeddings = find_closest_to_centroid(
        vectors, centroids, cluster_assignments, embedding_data, n_samples=5
    )
    
    # Step 5: Output results to a report file
    with open('cluster_analysis_report.txt', 'w') as f:
        f.write(f"Analysis of {len(vectors)} embeddings in {n_clusters} clusters\n")
        f.write("=" * 80 + "\n\n")
        
        # Write cluster sizes
        cluster_sizes = df['cluster'].value_counts().sort_values(ascending=False)
        f.write("Cluster distribution:\n")
        for cluster_id, count in cluster_sizes.items():
            percentage = (count / len(df)) * 100
            f.write(f"Cluster {cluster_id}: {count} embeddings ({percentage:.1f}%)\n")
            
            # Parent types in this cluster
            parent_types = df[df['cluster'] == cluster_id]['parent_type'].value_counts()
            for parent_type, type_count in parent_types.items():
                type_percentage = (type_count / count) * 100
                f.write(f"  - {parent_type}: {type_count} ({type_percentage:.1f}%)\n")
            
            # Top 5 representative embeddings
            f.write("\n  Representative embeddings:\n")
            for i, embedding in enumerate(closest_embeddings.get(cluster_id, [])):
                f.write(f"  {i+1}. ID: {embedding['embedding_id']}\n")
                f.write(f"     Similarity to centroid: {embedding['similarity']:.4f}\n")
                f.write(f"     Parent type: {embedding['parent_type']}\n")
                if embedding['parent_id']:
                    f.write(f"     Parent ID: {embedding['parent_id']}\n")
                f.write(f"     Meta info: {embedding['meta_info']}\n")
                f.write("\n")
                
            f.write("\n")
            
    logger.info("Analysis complete. Results saved to 'cluster_analysis_report.txt'")
        
if __name__ == "__main__":
    main()