# Embedding Clusters: Advanced Clustering for Conversations

This guide explains how to use the embedding clustering functionality in carchive to organize your conversations 
into meaningful topics and collections.

## Overview

The clustering system analyzes the vector embeddings of your messages to group similar content together.
You can use different clustering algorithms to identify patterns, create topic-based collections,
and better organize your conversation archive.

## Getting Started

### Prerequisites

Make sure you have:

1. A populated database with embeddings (run the `embed` command if you haven't created embeddings yet)
2. Required dependencies: `matplotlib`, `scikit-learn`, and `numpy`

### Basic Usage

To start clustering your embeddings:

```bash
# Analyze to find the optimal number of clusters
poetry run carchive cluster analyze

# Run KMeans clustering with 20 clusters and create collections
poetry run carchive cluster kmeans --n-clusters=20 --visualization

# Use DBSCAN for density-based clustering (automatically finds clusters)
poetry run carchive cluster dbscan --visualization

# Create a hierarchical clustering (topics and subtopics)
poetry run carchive cluster hierarchical --primary-clusters=5 --secondary-clusters=3
```

## Command Reference

### Analyze Optimal Clusters

```bash
poetry run carchive cluster analyze [OPTIONS]
```

Analyzes your embeddings to determine the ideal number of clusters using multiple statistical metrics:
- Silhouette Score (higher is better)
- Calinski-Harabasz Index (higher is better)
- Davies-Bouldin Index (lower is better)

Options:
- `--min-clusters` - Minimum number of clusters to test (default: 2)
- `--max-clusters` - Maximum number of clusters to test (default: 30)
- `--step` - Step size for testing cluster numbers (default: 2)
- `--limit` - Maximum number of embeddings to process (default: all)
- `--output-dir` - Directory to save analysis outputs (default: "cluster_analysis")

### KMeans Clustering

```bash
poetry run carchive cluster kmeans [OPTIONS]
```

Clusters embeddings using the KMeans algorithm and creates collections for each cluster.

Options:
- `--n-clusters` - Number of clusters to create (default: 10)
- `--prefix` - Prefix for collection names (default: "Topic")
- `--limit` - Maximum number of embeddings to process (default: all)
- `--exclude-outliers/--include-outliers` - Whether to exclude outliers (default: exclude)
- `--generate-topics/--no-topics` - Use LLM to generate descriptive topics (default: no)
- `--topic-provider` - LLM provider for topic generation (default: "ollama")
- `--visualization/--no-visualization` - Generate cluster visualization (default: no)
- `--output-dir` - Directory to save outputs (default: "clusters_output")

### DBSCAN Clustering

```bash
poetry run carchive cluster dbscan [OPTIONS]
```

Clusters embeddings using DBSCAN (Density-Based Spatial Clustering of Applications with Noise),
which automatically determines the number of clusters based on density and can identify outliers.

Options:
- `--eps` - Maximum distance between samples in a cluster (default: 0.5)
- `--min-samples` - Minimum samples to form a cluster (default: 5)
- `--prefix` - Prefix for collection names (default: "Topic")
- `--limit` - Maximum number of embeddings to process (default: all)
- `--max-clusters` - Maximum number of clusters to create (default: all)
- `--generate-topics/--no-topics` - Use LLM to generate descriptive topics (default: no)
- `--topic-provider` - LLM provider for topic generation (default: "ollama")
- `--visualization/--no-visualization` - Generate cluster visualization (default: no)
- `--output-dir` - Directory to save outputs (default: "clusters_output")

### Hierarchical Clustering

```bash
poetry run carchive cluster hierarchical [OPTIONS]
```

Creates a two-level hierarchy of clusters - primary clusters for major topics and
secondary clusters for subtopics within each primary topic.

Options:
- `--primary-clusters` - Number of top-level clusters (default: 5)
- `--secondary-clusters` - Number of sub-clusters per primary cluster (default: 3)
- `--prefix` - Prefix for collection names (default: "Topic")
- `--limit` - Maximum number of embeddings to process (default: all)
- `--generate-topics/--no-topics` - Use LLM to generate descriptive topics (default: no)
- `--topic-provider` - LLM provider for topic generation (default: "ollama")
- `--visualization/--no-visualization` - Generate visualization (default: no)
- `--output-dir` - Directory to save outputs (default: "clusters_output")

### Generate Topics for Collections

```bash
poetry run carchive cluster generate-topics [OPTIONS]
```

Adds LLM-generated topic descriptions to existing collections.

Options:
- `--collection-id` - IDs of collections to process (can specify multiple)
- `--all` - Generate topics for all collections (default: false)
- `--topic-provider` - LLM provider to use (default: "ollama")
- `--update-names/--keep-names` - Update collection names with topics (default: keep)

### Export Cluster Samples

```bash
poetry run carchive cluster export-samples [OPTIONS]
```

Exports sample messages from a cluster collection for analysis.

Options:
- `--collection-id` - ID of the collection to export samples from (required)
- `--samples` - Number of sample messages to export (default: 10)
- `--output` - File to save the samples to (default: "cluster_samples.txt")

## Advanced Topics

### Choosing the Right Algorithm

- **KMeans**: Best for well-separated clusters of similar sizes
- **DBSCAN**: Good for finding clusters of irregular shapes and identifying outliers
- **Hierarchical**: Creates a multi-level organization for better content discovery

### Topic Generation

When using `--generate-topics`, the system will analyze the content of each cluster and
generate appropriate topic names, keywords, and descriptions using the specified LLM provider.

The generated topics are stored in the collection's metadata and can be displayed with:

```bash
poetry run carchive collection list --verbose
```

### Visualization

Enabling visualization with `--visualization` creates PCA plots showing how your 
embeddings cluster in 2D space, which helps verify the quality of clustering.

Visualization images are saved to the specified output directory.

## Troubleshooting

### Missing Dependencies

If you encounter errors about missing libraries:

```bash
pip install matplotlib scikit-learn numpy tqdm
```

### No Embeddings Found

If the system can't find any embeddings:

1. Check your database connection
2. Make sure you've run the embedding process:

```bash
poetry run carchive embed run --model=nomic-embed-text
```

### Poor Clustering Results

If your clustering results don't seem meaningful:

1. Try analyzing with different parameters: `poetry run carchive cluster analyze`
2. Try DBSCAN with different `eps` values
3. Consider increasing your embedding dimension or using a different embedding model
