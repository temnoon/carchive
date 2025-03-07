"""
API routes for clustering operations.
"""

import os
import json
import logging
import tempfile
import uuid
from typing import List, Dict, Any, Optional
from flask import Blueprint, jsonify, request, current_app, send_file
import numpy as np
import matplotlib.pyplot as plt
from sqlalchemy import desc, func
from carchive.database.session import db_session, get_session
from carchive.database.models import Embedding, Message, Collection, CollectionItem
from carchive.embeddings.clustering import EmbeddingClusterer
from carchive.collections.collection_manager import CollectionManager

logger = logging.getLogger(__name__)

bp = Blueprint("clusters", __name__, url_prefix="/api/clusters")


@bp.route("/", methods=["GET"])
@db_session
def list_clusters(session):
    """List all cluster collections."""
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        
        # Query collections with cluster metadata
        query = session.query(Collection).filter(
            Collection.meta_info.has_key("cluster_id")  # Has cluster_id in meta_info
        )
        
        # Count total results
        total = query.count()
        
        # Paginate results
        query = query.order_by(desc(Collection.created_at))
        query = query.limit(per_page).offset((page - 1) * per_page)
        
        collections = query.all()
        
        # Format result
        result = []
        for coll in collections:
            # Extract cluster metadata
            cluster_meta = {}
            if coll.meta_info:
                cluster_meta = {
                    "cluster_id": coll.meta_info.get("cluster_id"),
                    "item_count": coll.meta_info.get("item_count"),
                    "item_type": coll.meta_info.get("item_type")
                }
                
                # Include topic info if available
                if "topic" in coll.meta_info:
                    cluster_meta["topic"] = coll.meta_info.get("topic")
            
            # Count items
            item_count = session.query(func.count(CollectionItem.id)).filter_by(
                collection_id=coll.id
            ).scalar()
            
            # Add to result
            result.append({
                "id": str(coll.id),
                "name": coll.name,
                "created_at": coll.created_at.isoformat() if coll.created_at else None,
                "item_count": item_count,
                "cluster_meta": cluster_meta
            })
        
        return jsonify({
            "collections": result,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page
            }
        })
    except Exception as e:
        logger.error(f"Error listing clusters: {e}")
        return jsonify({"error": str(e)}), 500


@bp.route("/", methods=["POST"])
@db_session
def create_cluster(session):
    """Generate a new cluster from embeddings."""
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Get clustering parameters
        algorithm = data.get("algorithm", "kmeans")
        params = data.get("params", {})
        
        # For KMeans
        n_clusters = params.get("n_clusters", 10)
        
        # For DBSCAN
        eps = params.get("eps", 0.5)
        min_samples = params.get("min_samples", 5)
        
        # Collection options
        collection_prefix = data.get("collection_prefix", "Cluster")
        exclude_outliers = data.get("exclude_outliers", True)
        max_clusters = data.get("max_clusters")
        
        # Embedding limits
        limit = data.get("limit")
        
        # Topic generation
        generate_topics = data.get("generate_topics", False)
        topic_provider = data.get("topic_provider", "ollama")
        
        # Get embeddings
        vectors, embedding_ids, message_ids = EmbeddingClusterer.fetch_embeddings(limit=limit)
        
        if not vectors:
            return jsonify({"error": "No embeddings found"}), 404
        
        # Perform clustering
        if algorithm.lower() == "kmeans":
            cluster_assignments = EmbeddingClusterer.cluster_kmeans(vectors, n_clusters=n_clusters)
        elif algorithm.lower() == "dbscan":
            cluster_assignments = EmbeddingClusterer.cluster_dbscan(vectors, eps=eps, min_samples=min_samples)
        else:
            return jsonify({"error": f"Unsupported algorithm: {algorithm}"}), 400
        
        # Create visualization
        output_path = os.path.join(tempfile.gettempdir(), f"cluster_{uuid.uuid4()}.png")
        EmbeddingClusterer.visualize_clusters(vectors, cluster_assignments, output_path=output_path)
        
        # Create collections from clusters
        collections = EmbeddingClusterer.create_collections_from_clusters(
            message_ids=message_ids,
            cluster_assignments=cluster_assignments,
            collection_prefix=collection_prefix,
            exclude_outliers=exclude_outliers,
            max_clusters=max_clusters,
            embedding_ids=embedding_ids,
            generate_topics=generate_topics,
            topic_provider=topic_provider
        )
        
        # Get cluster statistics
        cluster_counts = {}
        for c in cluster_assignments:
            if c not in cluster_counts:
                cluster_counts[c] = 0
            cluster_counts[c] += 1
        
        # Format collections for response
        collection_results = []
        for coll in collections:
            collection_results.append({
                "id": str(coll.id),
                "name": coll.name,
                "item_count": len(coll.items) if hasattr(coll, "items") else 0,
                "cluster_meta": coll.meta_info
            })
        
        return jsonify({
            "status": "success",
            "message": f"Created {len(collections)} cluster collections",
            "collections": collection_results,
            "statistics": {
                "total_embeddings": len(vectors),
                "clusters": len(set(cluster_assignments)),
                "by_cluster": cluster_counts,
                "algorithm": algorithm,
                "parameters": params,
                "visualization_path": output_path
            }
        })
    except Exception as e:
        logger.error(f"Error creating clusters: {e}")
        return jsonify({"error": str(e)}), 500


@bp.route("/analyze", methods=["POST"])
@db_session
def analyze_clusters(session):
    """Analyze optimal cluster count."""
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Get analysis parameters
        min_clusters = data.get("min_clusters", 2)
        max_clusters = data.get("max_clusters", 20)
        step = data.get("step", 1)
        limit = data.get("limit")
        
        # Get embeddings
        vectors, _, _ = EmbeddingClusterer.fetch_embeddings(limit=limit)
        
        if not vectors:
            return jsonify({"error": "No embeddings found"}), 404
        
        # Create range of cluster counts to test
        cluster_range = range(min_clusters, max_clusters + 1, step)
        
        # Perform analysis using silhouette scores
        from sklearn.cluster import KMeans
        from sklearn.metrics import silhouette_score
        
        X = np.vstack(vectors)
        
        # Calculate silhouette scores for different numbers of clusters
        silhouette_scores = []
        inertia_scores = []
        
        for n_clusters in cluster_range:
            # Skip if we have fewer data points than clusters
            if n_clusters >= len(X):
                break
                
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            cluster_assignments = kmeans.fit_predict(X)
            
            # Calculate silhouette score
            silhouette_avg = silhouette_score(X, cluster_assignments)
            silhouette_scores.append(silhouette_avg)
            
            # Calculate inertia (within-cluster sum of squares)
            inertia_scores.append(kmeans.inertia_)
            
        # Find optimal cluster count (highest silhouette score)
        optimal_silhouette_idx = silhouette_scores.index(max(silhouette_scores))
        optimal_clusters = list(cluster_range)[optimal_silhouette_idx]
        
        # Create visualization of analysis
        plt.figure(figsize=(12, 6))
        
        # Plot silhouette scores
        plt.subplot(1, 2, 1)
        plt.plot(list(cluster_range)[:len(silhouette_scores)], silhouette_scores, 'o-', color='blue')
        plt.axvline(x=optimal_clusters, color='r', linestyle='--')
        plt.title('Silhouette Score by Cluster Count')
        plt.xlabel('Number of Clusters')
        plt.ylabel('Silhouette Score')
        plt.grid(True)
        
        # Plot inertia (elbow method)
        plt.subplot(1, 2, 2)
        plt.plot(list(cluster_range)[:len(inertia_scores)], inertia_scores, 'o-', color='green')
        plt.title('Elbow Method (Inertia)')
        plt.xlabel('Number of Clusters')
        plt.ylabel('Inertia')
        plt.grid(True)
        
        # Save plot
        output_path = os.path.join(tempfile.gettempdir(), f"cluster_analysis_{uuid.uuid4()}.png")
        plt.tight_layout()
        plt.savefig(output_path, dpi=300)
        plt.close()
        
        return jsonify({
            "status": "success",
            "message": f"Analyzed {len(vectors)} embeddings",
            "results": {
                "optimal_clusters": optimal_clusters,
                "silhouette_scores": {
                    n: score for n, score in zip(cluster_range, silhouette_scores)
                },
                "visualization_path": output_path
            }
        })
    except Exception as e:
        logger.error(f"Error analyzing clusters: {e}")
        return jsonify({"error": str(e)}), 500


@bp.route("/<collection_id>", methods=["GET"])
@db_session
def get_cluster(session, collection_id):
    """Get details for a specific cluster collection."""
    try:
        collection = session.query(Collection).filter_by(id=collection_id).first()
        
        if not collection:
            return jsonify({"error": "Collection not found"}), 404
        
        # Check if this is a cluster collection
        if not collection.meta_info or "cluster_id" not in collection.meta_info:
            return jsonify({"error": "Not a cluster collection"}), 400
        
        # Get collection items
        items = session.query(CollectionItem).filter_by(collection_id=collection_id).all()
        
        # Format item details
        item_details = []
        for item in items:
            detail = {
                "id": str(item.id),
                "collection_id": str(item.collection_id)
            }
            
            # Get message details if available
            if item.message_id:
                message = session.query(Message).filter_by(id=item.message_id).first()
                if message:
                    detail["message"] = {
                        "id": str(message.id),
                        "conversation_id": str(message.conversation_id) if message.conversation_id else None,
                        "role": message.role,
                        "author_name": message.author_name,
                        "content_preview": message.content[:200] + "..." if message.content and len(message.content) > 200 else message.content,
                        "created_at": message.created_at.isoformat() if message.created_at else None
                    }
            
            # Add to result
            item_details.append(detail)
        
        # Get sample texts if available
        sample_texts = []
        if collection.meta_info and "sample_texts" in collection.meta_info:
            sample_texts = collection.meta_info.get("sample_texts")
        
        return jsonify({
            "id": str(collection.id),
            "name": collection.name,
            "created_at": collection.created_at.isoformat() if collection.created_at else None,
            "cluster_meta": collection.meta_info,
            "sample_texts": sample_texts,
            "items": item_details[:20],  # Limit to first 20 items
            "item_count": len(items)
        })
    except Exception as e:
        logger.error(f"Error getting cluster {collection_id}: {e}")
        return jsonify({"error": str(e)}), 500


@bp.route("/<collection_id>", methods=["DELETE"])
@db_session
def delete_cluster(session, collection_id):
    """Delete a specific cluster collection."""
    try:
        collection = session.query(Collection).filter_by(id=collection_id).first()
        
        if not collection:
            return jsonify({"error": "Collection not found"}), 404
        
        # Check if this is a cluster collection
        if not collection.meta_info or "cluster_id" not in collection.meta_info:
            return jsonify({"error": "Not a cluster collection"}), 400
        
        # Delete the collection
        collection_manager = CollectionManager()
        deleted = collection_manager.delete_collection(collection_id)
        
        if deleted:
            return jsonify({
                "status": "success",
                "message": f"Cluster collection {collection_id} deleted"
            })
        else:
            return jsonify({"error": "Failed to delete collection"}), 500
    except Exception as e:
        logger.error(f"Error deleting cluster {collection_id}: {e}")
        return jsonify({"error": str(e)}), 500


@bp.route("/<collection_id>/visualize", methods=["GET"])
@db_session
def visualize_cluster(session, collection_id):
    """Generate visualization data for a cluster."""
    try:
        collection = session.query(Collection).filter_by(id=collection_id).first()
        
        if not collection:
            return jsonify({"error": "Collection not found"}), 404
        
        # Check if this is a cluster collection
        if not collection.meta_info or "cluster_id" not in collection.meta_info:
            return jsonify({"error": "Not a cluster collection"}), 400
        
        # Get collection items
        items = session.query(CollectionItem).filter_by(collection_id=collection_id).all()
        
        # Get message IDs
        message_ids = [item.message_id for item in items if item.message_id]
        
        if not message_ids:
            return jsonify({"error": "No messages found in cluster"}), 404
        
        # Get embeddings for these messages
        embeddings = session.query(Embedding).filter(
            Embedding.parent_message_id.in_(message_ids)
        ).all()
        
        if not embeddings:
            return jsonify({"error": "No embeddings found for cluster messages"}), 404
        
        # Extract vectors
        vectors = [np.array(emb.vector) for emb in embeddings if emb.vector]
        
        if not vectors:
            return jsonify({"error": "No valid embedding vectors found"}), 404
        
        # Apply PCA for visualization
        from sklearn.decomposition import PCA
        
        pca = PCA(n_components=2)
        X_pca = pca.fit_transform(np.vstack(vectors))
        
        # Create visualization data
        viz_data = []
        for i, embedding in enumerate(embeddings):
            if i >= len(X_pca):
                break
                
            # Get message content
            message = session.query(Message).filter_by(id=embedding.parent_message_id).first()
            content_preview = ""
            if message:
                content_preview = message.content[:100] + "..." if message.content and len(message.content) > 100 else message.content
            
            viz_data.append({
                "embedding_id": str(embedding.id),
                "message_id": str(embedding.parent_message_id) if embedding.parent_message_id else None,
                "coordinates": {
                    "x": float(X_pca[i, 0]),
                    "y": float(X_pca[i, 1])
                },
                "content_preview": content_preview
            })
        
        return jsonify({
            "status": "success",
            "visualization_data": viz_data,
            "metadata": {
                "explained_variance": pca.explained_variance_ratio_.tolist(),
                "collection_id": collection_id,
                "collection_name": collection.name,
                "point_count": len(viz_data)
            }
        })
    except Exception as e:
        logger.error(f"Error visualizing cluster {collection_id}: {e}")
        return jsonify({"error": str(e)}), 500


@bp.route("/visualization/<filename>", methods=["GET"])
def get_visualization(filename):
    """Get a visualization image."""
    try:
        # Verify the filename is safe
        if not filename or ".." in filename or "/" in filename:
            return jsonify({"error": "Invalid filename"}), 400
        
        # Get the file path
        file_path = os.path.join(tempfile.gettempdir(), filename)
        
        if not os.path.isfile(file_path):
            return jsonify({"error": "Visualization not found"}), 404
        
        # Return the file
        return send_file(file_path, mimetype="image/png")
    except Exception as e:
        logger.error(f"Error getting visualization {filename}: {e}")
        return jsonify({"error": str(e)}), 500