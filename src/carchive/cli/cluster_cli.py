# carchive2/src/carchive2/cli/cluster_cli.py

import typer
from typing import Optional, List
from carchive.embeddings.clustering import EmbeddingClusterer
from carchive.collections.collection_manager import CollectionManager
import logging
import uuid

cluster_app = typer.Typer(help="Commands for clustering message embeddings and topic generation.")

logger = logging.getLogger(__name__)

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
    )
):
    """
    Cluster message embeddings using KMeans algorithm and create collections.
    
    If --generate-topics is enabled, uses an LLM to analyze the content of each cluster
    and generate descriptive topic labels and keywords, stored in collection.meta_info.
    """
    typer.echo(f"Fetching embeddings (limit={limit})...")
    
    vectors, embedding_ids, message_ids = EmbeddingClusterer.fetch_embeddings(limit)
    
    if not vectors:
        typer.echo("No embeddings found to cluster!")
        raise typer.Exit(code=1)
    
    typer.echo(f"Clustering {len(vectors)} embeddings into {n_clusters} clusters...")
    cluster_assignments = EmbeddingClusterer.cluster_kmeans(vectors, n_clusters)
    
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
    )
):
    """
    Cluster message embeddings using DBSCAN algorithm and create collections.
    DBSCAN automatically determines the number of clusters and can identify outliers.
    
    If --generate-topics is enabled, uses an LLM to analyze the content of each cluster
    and generate descriptive topic labels and keywords, stored in collection.meta_info.
    """
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