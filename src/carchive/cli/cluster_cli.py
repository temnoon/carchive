# carchive2/src/carchive2/cli/cluster_cli.py

import typer
import numpy as np
from typing import Optional, List
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
from sklearn.cluster import KMeans, DBSCAN
import matplotlib.pyplot as plt
from pathlib import Path
import json
import os
import random
from datetime import datetime

from carchive.embeddings.clustering import EmbeddingClusterer
from carchive.collections.collection_manager import CollectionManager
import logging

cluster_app = typer.Typer(help="Commands for clustering message embeddings and topic generation.")

logger = logging.getLogger(__name__)

@cluster_app.command("analyze")
def analyze_optimal_clusters(
    min_clusters: int = typer.Option(
        2,
        "--min-clusters",
        help="Minimum number of clusters to test",
        min=2
    ),
    max_clusters: int = typer.Option(
        30,
        "--max-clusters",
        help="Maximum number of clusters to test",
        min=3
    ),
    step: int = typer.Option(
        2,
        "--step",
        help="Step size for testing cluster numbers",
        min=1
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        help="Maximum number of embeddings to process (None for all)"
    ),
    output_dir: str = typer.Option(
        "cluster_analysis",
        "--output-dir",
        help="Directory to save analysis outputs"
    )
):
    """
    Analyze embeddings to determine optimal number of clusters using multiple metrics.
    
    This command examines your embedding data to recommend the ideal number of clusters
    based on silhouette score, Calinski-Harabasz index, and Davies-Bouldin index.
    It generates plots and saves a detailed report to help you make an informed decision.
    """
    # Create output directory if it doesn't exist
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(exist_ok=True, parents=True)
    
    typer.echo(f"Fetching embeddings (limit={limit})...")
    vectors, embedding_ids, message_ids = EmbeddingClusterer.fetch_embeddings(limit)
    
    if not vectors:
        typer.echo("No embeddings found to analyze!")
        raise typer.Exit(code=1)
    
    typer.echo(f"Analyzing optimal cluster count for {len(vectors)} embeddings...")
    
    # Convert to numpy array for analysis
    X = np.vstack(vectors)
    
    # Test range of cluster numbers
    cluster_range = range(min_clusters, max_clusters + 1, step)
    
    # Initialize metrics
    silhouette_scores = []
    ch_scores = []
    db_scores = []
    
    # Calculate metrics for each cluster count
    for n_clusters in cluster_range:
        typer.echo(f"Testing with {n_clusters} clusters...")
        
        # Run K-means
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(X)
        
        # Calculate silhouette score (higher is better)
        silhouette_avg = silhouette_score(X, cluster_labels)
        silhouette_scores.append(silhouette_avg)
        
        # Calculate Calinski-Harabasz Index (higher is better)
        ch_score = calinski_harabasz_score(X, cluster_labels)
        ch_scores.append(ch_score)
        
        # Calculate Davies-Bouldin Index (lower is better)
        db_score = davies_bouldin_score(X, cluster_labels)
        db_scores.append(db_score)
        
        typer.echo(f"  • Silhouette Score: {silhouette_avg:.4f}")
        typer.echo(f"  • Calinski-Harabasz Index: {ch_score:.2f}")
        typer.echo(f"  • Davies-Bouldin Index: {db_score:.4f}")
    
    # Find optimal cluster counts for each metric
    best_silhouette = max(silhouette_scores)
    best_silhouette_idx = silhouette_scores.index(best_silhouette)
    best_silhouette_n = cluster_range[best_silhouette_idx]
    
    best_ch = max(ch_scores)
    best_ch_idx = ch_scores.index(best_ch)
    best_ch_n = cluster_range[best_ch_idx]
    
    best_db = min(db_scores)
    best_db_idx = db_scores.index(best_db)
    best_db_n = cluster_range[best_db_idx]
    
    # Generate plots
    plt.figure(figsize=(15, 10))
    
    # Silhouette Score plot
    plt.subplot(3, 1, 1)
    plt.plot(list(cluster_range), silhouette_scores, 'bo-')
    plt.axvline(x=best_silhouette_n, color='r', linestyle='--')
    plt.title(f'Silhouette Score (higher is better)\nOptimal: {best_silhouette_n} clusters')
    plt.xlabel('Number of clusters')
    plt.ylabel('Score')
    plt.grid(True)
    
    # Calinski-Harabasz plot
    plt.subplot(3, 1, 2)
    plt.plot(list(cluster_range), ch_scores, 'go-')
    plt.axvline(x=best_ch_n, color='r', linestyle='--')
    plt.title(f'Calinski-Harabasz Index (higher is better)\nOptimal: {best_ch_n} clusters')
    plt.xlabel('Number of clusters')
    plt.ylabel('Score')
    plt.grid(True)
    
    # Davies-Bouldin plot
    plt.subplot(3, 1, 3)
    plt.plot(list(cluster_range), db_scores, 'ro-')
    plt.axvline(x=best_db_n, color='g', linestyle='--')
    plt.title(f'Davies-Bouldin Index (lower is better)\nOptimal: {best_db_n} clusters')
    plt.xlabel('Number of clusters')
    plt.ylabel('Score')
    plt.grid(True)
    
    plt.tight_layout()
    plot_path = os.path.join(output_dir, "cluster_analysis_plot.png")
    plt.savefig(plot_path)
    
    # Save results to JSON
    results = {
        "embeddings_count": len(vectors),
        "cluster_range": list(cluster_range),
        "metrics": {
            "silhouette_scores": {
                "values": [float(s) for s in silhouette_scores],
                "optimal_clusters": best_silhouette_n,
                "optimal_score": float(best_silhouette)
            },
            "calinski_harabasz_scores": {
                "values": [float(s) for s in ch_scores],
                "optimal_clusters": best_ch_n,
                "optimal_score": float(best_ch)
            },
            "davies_bouldin_scores": {
                "values": [float(s) for s in db_scores],
                "optimal_clusters": best_db_n,
                "optimal_score": float(best_db)
            }
        },
        "recommendation": {
            "recommended_clusters": best_silhouette_n,
            "rationale": "Based primarily on silhouette score, which measures how well-separated the clusters are."
        },
        "timestamp": datetime.now().isoformat()
    }
    
    json_path = os.path.join(output_dir, "cluster_analysis_results.json")
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Generate text report
    report = f"""
Cluster Analysis Report
======================
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Embeddings analyzed: {len(vectors)}
Cluster range tested: {min_clusters} to {max_clusters} (step: {step})

Optimal Cluster Counts by Metric:
--------------------------------
• Silhouette Score: {best_silhouette_n} clusters (score: {best_silhouette:.4f})
• Calinski-Harabasz Index: {best_ch_n} clusters (score: {best_ch:.2f})
• Davies-Bouldin Index: {best_db_n} clusters (score: {best_db:.4f})

Recommendation:
--------------
The optimal number of clusters appears to be {best_silhouette_n}.

Next Steps:
----------
1. Run the clustering with the recommended number:
   poetry run carchive cluster kmeans --n-clusters={best_silhouette_n} --generate-topics

2. For more fine-grained clustering:
   poetry run carchive cluster kmeans --n-clusters={min(best_silhouette_n*2, max_clusters)} --generate-topics

3. For more general clustering:
   poetry run carchive cluster kmeans --n-clusters={max(best_silhouette_n//2, 2)} --generate-topics
"""
    
    report_path = os.path.join(output_dir, "cluster_analysis_report.txt")
    with open(report_path, 'w') as f:
        f.write(report)
    
    typer.echo(f"\nAnalysis complete!")
    typer.echo(f"Plot saved to: {plot_path}")
    typer.echo(f"Results saved to: {json_path}")
    typer.echo(f"Report saved to: {report_path}")
    
    typer.echo("\nRecommendation:")
    typer.echo(f"The optimal number of clusters appears to be {best_silhouette_n}.")
    typer.echo(f"Consider running: poetry run carchive cluster kmeans --n-clusters={best_silhouette_n} --generate-topics")

@cluster_app.command("kmeans")
def kmeans_clustering(
    n_clusters: int = typer.Option(
        10,
        "--n-clusters",
        help="Number of clusters to create",
        min=2,
        max=100
    ),
    collection_prefix: str = typer.Option(
        "Topic",
        "--prefix",
        help="Prefix for collection names"
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        help="Maximum number of embeddings to process (None for all)"
    ),
    exclude_outliers: bool = typer.Option(
        True,
        "--exclude-outliers/--include-outliers",
        help="Whether to exclude outliers from collections"
    ),
    generate_topics: bool = typer.Option(
        False,
        "--generate-topics/--no-topics",
        help="Whether to generate descriptive topics for each cluster using LLM"
    ),
    topic_provider: str = typer.Option(
        "ollama",
        "--topic-provider",
        help="LLM provider to use for topic generation (openai, anthropic, ollama, etc.)"
    ),
    sample_content: bool = typer.Option(
        False,
        "--sample-content/--no-samples",
        help="Whether to extract and save sample content from each cluster"
    ),
    visualization: bool = typer.Option(
        False,
        "--visualization/--no-visualization",
        help="Generate PCA visualization of clusters"
    ),
    output_dir: str = typer.Option(
        "clusters_output",
        "--output-dir",
        help="Directory to save analysis outputs"
    )
):
    """
    Cluster message embeddings using KMeans algorithm and create collections.
    
    If --generate-topics is enabled, uses an LLM to analyze the content of each cluster
    and generate descriptive topic labels and keywords, stored in collection.meta_info.
    
    If --sample-content is enabled, samples representative messages from each cluster
    and saves them for review.
    
    If --visualization is enabled, generates a PCA visualization of the clusters.
    """
    # Create output directory if it doesn't exist
    if sample_content or visualization:
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(exist_ok=True, parents=True)
    
    typer.echo(f"Fetching embeddings (limit={limit})...")
    
    vectors, embedding_ids, message_ids = EmbeddingClusterer.fetch_embeddings(limit)
    
    if not vectors:
        typer.echo("No embeddings found to cluster!")
        raise typer.Exit(code=1)
    
    typer.echo(f"Clustering {len(vectors)} embeddings into {n_clusters} clusters...")
    cluster_assignments = EmbeddingClusterer.cluster_kmeans(vectors, n_clusters)
    
    # Generate visualization if requested
    if visualization:
        typer.echo("Generating cluster visualization...")
        EmbeddingClusterer.visualize_clusters(
            vectors, 
            cluster_assignments, 
            output_path=os.path.join(output_dir, f"kmeans_{n_clusters}_clusters.png")
        )
    
    # Extract sample content if requested
    if sample_content:
        typer.echo("Extracting sample content from clusters...")
        samples = EmbeddingClusterer.extract_cluster_samples(
            vectors, 
            embedding_ids, 
            message_ids, 
            cluster_assignments, 
            samples_per_cluster=5
        )
        
        # Save samples to file
        samples_path = os.path.join(output_dir, f"kmeans_{n_clusters}_samples.json")
        with open(samples_path, 'w') as f:
            json.dump(samples, f, indent=2)
            
        typer.echo(f"Samples saved to {samples_path}")
    
    typer.echo("Creating collections from clusters...")
    if generate_topics:
        typer.echo(f"Generating topics using {topic_provider} LLM...")
    
    collections = EmbeddingClusterer.create_collections_from_clusters(
        message_ids, 
        cluster_assignments,
        collection_prefix,
        exclude_outliers,
        embedding_ids=embedding_ids,
        generate_topics=generate_topics,
        topic_provider=topic_provider
    )
    
    typer.echo(f"Created {len(collections)} collections from clusters:")
    for collection in collections:
        # Display topic info if available
        if collection.meta_info and "topic" in collection.meta_info:
            topic_info = collection.meta_info["topic"]
            topic = topic_info.get("topic", "Unknown")
            confidence = topic_info.get("confidence", 0.0)
            keywords = ", ".join(topic_info.get("keywords", []))
            typer.echo(f"- {collection.name}")
            typer.echo(f"  • Confidence: {confidence:.2f}")
            if keywords:
                typer.echo(f"  • Keywords: {keywords}")
        else:
            typer.echo(f"- {collection.name}")

@cluster_app.command("dbscan")
def dbscan_clustering(
    eps: float = typer.Option(
        0.5,
        "--eps",
        help="Maximum distance between samples in a cluster",
        min=0.1,
        max=2.0
    ),
    min_samples: int = typer.Option(
        5,
        "--min-samples",
        help="Minimum number of samples in a neighborhood to form a cluster",
        min=2
    ),
    collection_prefix: str = typer.Option(
        "Topic",
        "--prefix",
        help="Prefix for collection names"
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        help="Maximum number of embeddings to process (None for all)"
    ),
    max_clusters: Optional[int] = typer.Option(
        None,
        "--max-clusters",
        help="Maximum number of clusters to create collections for"
    ),
    generate_topics: bool = typer.Option(
        False,
        "--generate-topics/--no-topics",
        help="Whether to generate descriptive topics for each cluster using LLM"
    ),
    topic_provider: str = typer.Option(
        "ollama",
        "--topic-provider",
        help="LLM provider to use for topic generation (openai, anthropic, ollama, etc.)"
    ),
    sample_content: bool = typer.Option(
        False,
        "--sample-content/--no-samples",
        help="Whether to extract and save sample content from each cluster"
    ),
    visualization: bool = typer.Option(
        False,
        "--visualization/--no-visualization",
        help="Generate PCA visualization of clusters"
    ),
    output_dir: str = typer.Option(
        "clusters_output",
        "--output-dir",
        help="Directory to save analysis outputs"
    )
):
    """
    Cluster message embeddings using DBSCAN algorithm and create collections.
    DBSCAN automatically determines the number of clusters and can identify outliers.
    
    If --generate-topics is enabled, uses an LLM to analyze the content of each cluster
    and generate descriptive topic labels and keywords, stored in collection.meta_info.
    
    If --sample-content is enabled, samples representative messages from each cluster
    and saves them for review.
    
    If --visualization is enabled, generates a PCA visualization of the clusters.
    """
    # Create output directory if it doesn't exist
    if sample_content or visualization:
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(exist_ok=True, parents=True)
    
    typer.echo(f"Fetching embeddings (limit={limit})...")
    
    vectors, embedding_ids, message_ids = EmbeddingClusterer.fetch_embeddings(limit)
    
    if not vectors:
        typer.echo("No embeddings found to cluster!")
        raise typer.Exit(code=1)
    
    typer.echo(f"Clustering {len(vectors)} embeddings using DBSCAN (eps={eps}, min_samples={min_samples})...")
    cluster_assignments = EmbeddingClusterer.cluster_dbscan(vectors, eps, min_samples)
    
    n_clusters = len(set(cluster_assignments)) - (1 if -1 in cluster_assignments else 0)
    n_outliers = cluster_assignments.count(-1)
    
    typer.echo(f"DBSCAN found {n_clusters} clusters with {n_outliers} outliers")
    
    # Generate visualization if requested
    if visualization:
        typer.echo("Generating cluster visualization...")
        EmbeddingClusterer.visualize_clusters(
            vectors, 
            cluster_assignments, 
            output_path=os.path.join(output_dir, f"dbscan_eps{eps}_minsamples{min_samples}.png")
        )
    
    # Extract sample content if requested
    if sample_content:
        typer.echo("Extracting sample content from clusters...")
        samples = EmbeddingClusterer.extract_cluster_samples(
            vectors, 
            embedding_ids, 
            message_ids, 
            cluster_assignments, 
            samples_per_cluster=5
        )
        
        # Save samples to file
        samples_path = os.path.join(output_dir, f"dbscan_eps{eps}_minsamples{min_samples}_samples.json")
        with open(samples_path, 'w') as f:
            json.dump(samples, f, indent=2)
            
        typer.echo(f"Samples saved to {samples_path}")
    
    typer.echo("Creating collections from clusters...")
    if generate_topics:
        typer.echo(f"Generating topics using {topic_provider} LLM...")
    
    collections = EmbeddingClusterer.create_collections_from_clusters(
        message_ids, 
        cluster_assignments,
        collection_prefix,
        exclude_outliers=True,
        max_clusters=max_clusters,
        embedding_ids=embedding_ids,
        generate_topics=generate_topics,
        topic_provider=topic_provider
    )
    
    typer.echo(f"Created {len(collections)} collections from clusters:")
    for collection in collections:
        # Display topic info if available
        if collection.meta_info and "topic" in collection.meta_info:
            topic_info = collection.meta_info["topic"]
            topic = topic_info.get("topic", "Unknown")
            confidence = topic_info.get("confidence", 0.0)
            keywords = ", ".join(topic_info.get("keywords", []))
            typer.echo(f"- {collection.name}")
            typer.echo(f"  • Confidence: {confidence:.2f}")
            if keywords:
                typer.echo(f"  • Keywords: {keywords}")
        else:
            typer.echo(f"- {collection.name}")

@cluster_app.command("hierarchical")
def hierarchical_clustering(
    primary_clusters: int = typer.Option(
        5,
        "--primary-clusters",
        help="Number of top-level clusters to create",
        min=2,
        max=50
    ),
    secondary_clusters: int = typer.Option(
        3,
        "--secondary-clusters",
        help="Number of sub-clusters per primary cluster",
        min=2,
        max=10
    ),
    collection_prefix: str = typer.Option(
        "Topic",
        "--prefix",
        help="Prefix for collection names"
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        help="Maximum number of embeddings to process (None for all)"
    ),
    generate_topics: bool = typer.Option(
        False,
        "--generate-topics/--no-topics",
        help="Whether to generate descriptive topics for each cluster using LLM"
    ),
    topic_provider: str = typer.Option(
        "ollama",
        "--topic-provider",
        help="LLM provider to use for topic generation (openai, anthropic, ollama, etc.)"
    ),
    visualization: bool = typer.Option(
        False,
        "--visualization/--no-visualization",
        help="Generate visualization of hierarchical clusters"
    ),
    output_dir: str = typer.Option(
        "clusters_output",
        "--output-dir",
        help="Directory to save analysis outputs"
    )
):
    """
    Create a hierarchical clustering of embeddings with primary and secondary clusters.
    
    This creates a two-level hierarchy of collections - primary collections representing
    major topics, and secondary collections representing subtopics within each main topic.
    
    If --generate-topics is enabled, LLM-generated descriptions are added to collections.
    """
    # Create output directory if it doesn't exist
    if visualization:
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(exist_ok=True, parents=True)
    
    typer.echo(f"Fetching embeddings (limit={limit})...")
    vectors, embedding_ids, message_ids = EmbeddingClusterer.fetch_embeddings(limit)
    
    if not vectors:
        typer.echo("No embeddings found to cluster!")
        raise typer.Exit(code=1)
    
    # First level clustering
    typer.echo(f"Creating {primary_clusters} primary clusters...")
    primary_assignments = EmbeddingClusterer.cluster_kmeans(vectors, primary_clusters)
    
    # Create collections for primary clusters
    primary_collections = EmbeddingClusterer.create_collections_from_clusters(
        message_ids, 
        primary_assignments,
        f"{collection_prefix}_L1",
        exclude_outliers=True,
        embedding_ids=embedding_ids,
        generate_topics=generate_topics,
        topic_provider=topic_provider
    )
    
    # Process each primary cluster
    secondary_collections = []
    for primary_id in range(primary_clusters):
        # Get indices of embeddings in this primary cluster
        indices = [i for i, cluster in enumerate(primary_assignments) if cluster == primary_id]
        
        if len(indices) < secondary_clusters * 2:
            typer.echo(f"Primary cluster {primary_id} has too few embeddings for secondary clustering")
            continue
            
        # Extract embeddings for this cluster
        cluster_vectors = [vectors[i] for i in indices]
        cluster_embedding_ids = [embedding_ids[i] for i in indices]
        cluster_message_ids = [message_ids[i] for i in indices]
        
        # Secondary clustering for this primary cluster
        typer.echo(f"Creating {secondary_clusters} sub-clusters for primary cluster {primary_id}...")
        secondary_assignments = EmbeddingClusterer.cluster_kmeans(cluster_vectors, secondary_clusters)
        
        # Create prefix that links to parent
        parent_collection = primary_collections[primary_id]
        try:
            # Try to get topic if available
            if parent_collection.meta_info and "topic" in parent_collection.meta_info:
                topic = parent_collection.meta_info["topic"].get("topic", f"Topic{primary_id}")
                secondary_prefix = f"{topic}_Sub"
            else:
                secondary_prefix = f"{collection_prefix}_L1_{primary_id}_L2"
        except Exception:
            secondary_prefix = f"{collection_prefix}_L1_{primary_id}_L2"
        
        # Create collections for secondary clusters
        these_secondary_collections = EmbeddingClusterer.create_collections_from_clusters(
            cluster_message_ids, 
            secondary_assignments,
            secondary_prefix,
            exclude_outliers=True,
            embedding_ids=cluster_embedding_ids,
            generate_topics=generate_topics,
            topic_provider=topic_provider,
            parent_collection_id=str(parent_collection.id)
        )
        
        secondary_collections.extend(these_secondary_collections)
    
    # Generate visualization if requested
    if visualization:
        typer.echo("Generating hierarchical clustering visualization...")
        EmbeddingClusterer.visualize_hierarchical_clusters(
            vectors, 
            primary_assignments, 
            output_path=os.path.join(output_dir, f"hierarchical_{primary_clusters}x{secondary_clusters}.png")
        )
    
    # Display results
    typer.echo(f"Created {len(primary_collections)} primary collections:")
    for collection in primary_collections:
        if collection.meta_info and "topic" in collection.meta_info:
            topic_info = collection.meta_info["topic"]
            topic = topic_info.get("topic", "Unknown")
            keywords = ", ".join(topic_info.get("keywords", []))
            typer.echo(f"- {collection.name}")
            if keywords:
                typer.echo(f"  • Keywords: {keywords}")
        else:
            typer.echo(f"- {collection.name}")
    
    typer.echo(f"\nCreated {len(secondary_collections)} secondary collections.")

@cluster_app.command("generate-topics")
def generate_topics_for_collections(
    collection_ids: Optional[List[str]] = typer.Option(
        None,
        "--collection-id",
        help="IDs of collections to generate topics for (can specify multiple times)",
        show_default=False
    ),
    all_collections: bool = typer.Option(
        False,
        "--all",
        help="Generate topics for all collections"
    ),
    topic_provider: str = typer.Option(
        "ollama",
        "--topic-provider",
        help="LLM provider to use for topic generation (openai, anthropic, ollama, etc.)"
    ),
    update_names: bool = typer.Option(
        False,
        "--update-names/--keep-names",
        help="Whether to update collection names with generated topics"
    )
):
    """
    Generate descriptive topics for existing collections.
    
    Analyzes the content of messages in each collection to create concise topic labels,
    keywords, and descriptions, which are stored in the collection's meta_info.
    """
    if not collection_ids and not all_collections:
        typer.echo("Error: Must specify either --collection-id or --all")
        raise typer.Exit(code=1)
    
    collections_to_process = []
    
    if all_collections:
        typer.echo("Fetching all collections...")
        collections_to_process = CollectionManager.list_collections()
    else:
        for coll_id in collection_ids:
            collection = CollectionManager.get_collection(coll_id)
            if collection:
                collections_to_process.append(collection)
            else:
                typer.echo(f"Warning: Collection {coll_id} not found")
    
    typer.echo(f"Generating topics for {len(collections_to_process)} collections using {topic_provider}...")
    
    for collection in collections_to_process:
        typer.echo(f"Processing collection: {collection.name}")
        
        # Get items from the collection
        collection_items = CollectionManager.get_items_as_dbobjects(collection.id)
        
        # Extract message contents
        sample_texts = []
        for item in collection_items:
            if hasattr(item, "content") and item.content:
                sample_texts.append(item.content)
            if len(sample_texts) >= 5:  # Limit to 5 samples
                break
        
        if not sample_texts:
            typer.echo(f"  • No text content found in collection, skipping")
            continue
        
        # Generate topic for the collection
        topic_info = EmbeddingClusterer.generate_topic_for_sample_texts(
            sample_texts,
            provider=topic_provider
        )
        
        # Update collection meta_info with topic information
        meta_info = collection.meta_info or {}
        meta_info["topic"] = topic_info
        
        # Update collection name if requested
        if update_names and topic_info and topic_info.get("topic"):
            # Keep original item count info if present in the name
            import re
            count_match = re.search(r'\(([0-9]+) ([a-z]+)\)', collection.name)
            count_suffix = ""
            if count_match:
                count_suffix = f" ({count_match.group(1)} {count_match.group(2)})"
            
            new_name = f"{topic_info['topic']}{count_suffix}"
            
            # Update collection
            from carchive.collections.schemas import CollectionUpdateSchema
            update_data = CollectionUpdateSchema(
                name=new_name,
                meta_info=meta_info
            )
        else:
            # Only update meta_info
            from carchive.collections.schemas import CollectionUpdateSchema
            update_data = CollectionUpdateSchema(
                meta_info=meta_info
            )
        
        # Apply the update
        updated_collection = CollectionManager.update_collection(str(collection.id), update_data)
        
        # Display results
        typer.echo(f"  • Topic: {topic_info.get('topic', 'Unknown')}")
        if topic_info.get("keywords"):
            typer.echo(f"  • Keywords: {', '.join(topic_info['keywords'])}")
        typer.echo(f"  • Confidence: {topic_info.get('confidence', 0.0):.2f}")
        if update_names and topic_info.get("topic"):
            typer.echo(f"  • Renamed to: {updated_collection.name}")
    
    typer.echo(f"Topic generation complete for {len(collections_to_process)} collections")

@cluster_app.command("export-samples")
def export_cluster_samples(
    collection_id: str = typer.Option(
        ...,
        "--collection-id",
        help="ID of the collection to export samples from"
    ),
    sample_count: int = typer.Option(
        10,
        "--samples",
        help="Number of sample messages to export",
        min=1,
        max=100
    ),
    output_file: str = typer.Option(
        "cluster_samples.txt",
        "--output",
        help="File to save the samples to"
    )
):
    """
    Export sample messages from a cluster collection for analysis.
    
    This command is useful for understanding cluster contents and evaluating clustering quality.
    """
    typer.echo(f"Fetching collection {collection_id}...")
    
    collection = CollectionManager.get_collection(collection_id)
    if not collection:
        typer.echo(f"Error: Collection {collection_id} not found")
        raise typer.Exit(code=1)
    
    typer.echo(f"Exporting up to {sample_count} samples from collection: {collection.name}")
    
    # Get items from the collection
    collection_items = CollectionManager.get_items_as_dbobjects(collection.id)
    
    # Extract message contents
    sample_texts = []
    for item in collection_items:
        if hasattr(item, "content") and item.content:
            role = getattr(item, "role", "unknown") if hasattr(item, "role") else "unknown"
            sample_texts.append({
                "id": str(item.id),
                "role": role,
                "content": item.content[:500] + "..." if len(item.content) > 500 else item.content
            })
        if len(sample_texts) >= sample_count:  # Limit to requested samples
            break
    
    if not sample_texts:
        typer.echo("No message content found in this collection")
        raise typer.Exit(code=1)
    
    # Save samples to file
    with open(output_file, 'w') as f:
        f.write(f"Samples from collection: {collection.name}\n")
        f.write(f"Collection ID: {collection_id}\n")
        
        # Write topic info if available
        if collection.meta_info and "topic" in collection.meta_info:
            topic_info = collection.meta_info["topic"]
            f.write(f"Topic: {topic_info.get('topic', 'Unknown')}\n")
            if topic_info.get("keywords"):
                f.write(f"Keywords: {', '.join(topic_info['keywords'])}\n")
            f.write(f"Confidence: {topic_info.get('confidence', 0.0):.2f}\n")
        
        f.write("\n" + "="*50 + "\n\n")
        
        # Write samples
        for i, sample in enumerate(sample_texts, 1):
            f.write(f"Sample {i}:\n")
            f.write(f"ID: {sample['id']}\n")
            f.write(f"Role: {sample['role']}\n")
            f.write(f"Content:\n{sample['content']}\n\n")
            f.write("-"*30 + "\n\n")
    
    typer.echo(f"Exported {len(sample_texts)} samples to {output_file}")