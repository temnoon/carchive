"""
GUI views for clustering operations.
"""

import logging
import json
import os
import requests
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, current_app, flash, jsonify, send_file
)

logger = logging.getLogger(__name__)

bp = Blueprint("clusters", __name__, url_prefix="/clusters")

@bp.route("/")
def index():
    """Clusters dashboard view."""
    try:
        # Get paginated clusters list
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        
        params = {"page": page, "per_page": per_page}
            
        api_url = f"{current_app.config['API_URL']}/api/clusters/"
        response = requests.get(api_url, params=params)
        
        if response.status_code == 200:
            clusters_data = response.json()
        else:
            clusters_data = {"collections": [], "pagination": {"page": 1, "pages": 1, "total": 0}}
            flash(f"Error loading clusters: {response.text}", "danger")
        
        return render_template(
            "clusters/index.html",
            clusters=clusters_data["collections"],
            pagination=clusters_data["pagination"]
        )
    except Exception as e:
        logger.error(f"Error in clusters index view: {e}")
        flash(f"Error: {str(e)}", "danger")
        return render_template("clusters/index.html", clusters=[], pagination={"page": 1, "pages": 1, "total": 0})


@bp.route("/create", methods=["GET", "POST"])
def create():
    """Create a new cluster view."""
    if request.method == "POST":
        try:
            # Process form data
            algorithm = request.form.get("algorithm", "kmeans")
            
            # Get parameters based on algorithm
            params = {}
            if algorithm == "kmeans":
                params["n_clusters"] = int(request.form.get("n_clusters", 10))
            elif algorithm == "dbscan":
                params["eps"] = float(request.form.get("eps", 0.5))
                params["min_samples"] = int(request.form.get("min_samples", 5))
            
            # Collection options
            collection_prefix = request.form.get("collection_prefix", "Cluster")
            exclude_outliers = request.form.get("exclude_outliers") == "true"
            max_clusters = request.form.get("max_clusters")
            if max_clusters:
                max_clusters = int(max_clusters)
            
            # Embedding limits
            limit = request.form.get("limit")
            if limit:
                limit = int(limit)
            
            # Topic generation
            generate_topics = request.form.get("generate_topics") == "true"
            topic_provider = request.form.get("topic_provider", "ollama")
            
            # Send to API
            api_url = f"{current_app.config['API_URL']}/api/clusters/"
            data = {
                "algorithm": algorithm,
                "params": params,
                "collection_prefix": collection_prefix,
                "exclude_outliers": exclude_outliers,
                "max_clusters": max_clusters,
                "limit": limit,
                "generate_topics": generate_topics,
                "topic_provider": topic_provider
            }
            
            response = requests.post(api_url, json=data)
            
            # Handle API response
            if response.status_code == 200:
                result = response.json()
                collections = result.get("collections", [])
                flash(f"Created {len(collections)} cluster collections successfully", "success")
                
                # Check if we have a visualization path
                viz_path = result.get("statistics", {}).get("visualization_path")
                if viz_path and os.path.exists(viz_path):
                    # Extract filename for display
                    viz_filename = os.path.basename(viz_path)
                    flash(f"Visualization created: {viz_filename}", "info")
                
            else:
                error_msg = f"API Error: {response.status_code}"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_msg = error_data["error"]
                except:
                    pass
                flash(f"Error: {error_msg}", "danger")
            
            return redirect(url_for("clusters.index"))
            
        except Exception as e:
            logger.error(f"Error creating clusters: {e}")
            flash(f"Error: {str(e)}", "danger")
            return redirect(url_for("clusters.create"))
    
    # GET request - show form
    return render_template("clusters/create.html")


@bp.route("/analyze", methods=["GET", "POST"])
def analyze():
    """Analyze optimal cluster count view."""
    if request.method == "POST":
        try:
            # Process form data
            min_clusters = int(request.form.get("min_clusters", 2))
            max_clusters = int(request.form.get("max_clusters", 20))
            step = int(request.form.get("step", 1))
            limit = request.form.get("limit")
            if limit:
                limit = int(limit)
            
            # Send to API
            api_url = f"{current_app.config['API_URL']}/api/clusters/analyze"
            data = {
                "min_clusters": min_clusters,
                "max_clusters": max_clusters,
                "step": step,
                "limit": limit
            }
            
            response = requests.post(api_url, json=data)
            
            # Handle API response
            if response.status_code == 200:
                result = response.json()
                optimal = result.get("results", {}).get("optimal_clusters")
                viz_path = result.get("results", {}).get("visualization_path")
                
                flash(f"Analysis complete. Optimal cluster count: {optimal}", "success")
                
                # Store analysis results in session for display
                from flask import session
                session["cluster_analysis"] = {
                    "optimal_clusters": optimal,
                    "visualization_path": viz_path,
                    "visualization_filename": os.path.basename(viz_path) if viz_path else None
                }
                
                return redirect(url_for("clusters.analyze", result="success"))
                
            else:
                error_msg = f"API Error: {response.status_code}"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_msg = error_data["error"]
                except:
                    pass
                flash(f"Error: {error_msg}", "danger")
                return redirect(url_for("clusters.analyze"))
            
        except Exception as e:
            logger.error(f"Error analyzing clusters: {e}")
            flash(f"Error: {str(e)}", "danger")
            return redirect(url_for("clusters.analyze"))
    
    # GET request - show form or results
    from flask import session
    analysis_results = session.get("cluster_analysis")
    show_results = request.args.get("result") == "success" and analysis_results
    
    return render_template("clusters/analyze.html", 
                          show_results=show_results,
                          analysis=analysis_results)


@bp.route("/<collection_id>")
def view(collection_id):
    """View a specific cluster."""
    try:
        # Get cluster details
        api_url = f"{current_app.config['API_URL']}/api/clusters/{collection_id}"
        response = requests.get(api_url)
        
        if response.status_code == 200:
            cluster = response.json()
        else:
            flash(f"Error loading cluster: {response.text}", "danger")
            return redirect(url_for("clusters.index"))
        
        # Check if we should show visualization
        show_viz = request.args.get("viz") == "true"
        viz_data = None
        
        if show_viz:
            # Get visualization data
            viz_url = f"{current_app.config['API_URL']}/api/clusters/{collection_id}/visualize"
            viz_response = requests.get(viz_url)
            
            if viz_response.status_code == 200:
                viz_data = viz_response.json()
            else:
                flash(f"Error loading visualization: {viz_response.text}", "warning")
        
        return render_template(
            "clusters/view.html", 
            cluster=cluster, 
            show_viz=show_viz,
            viz_data=viz_data
        )
    except Exception as e:
        logger.error(f"Error viewing cluster {collection_id}: {e}")
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for("clusters.index"))


@bp.route("/<collection_id>/delete", methods=["POST"])
def delete(collection_id):
    """Delete a specific cluster."""
    try:
        # Delete cluster
        api_url = f"{current_app.config['API_URL']}/api/clusters/{collection_id}"
        response = requests.delete(api_url)
        
        if response.status_code == 200:
            flash("Cluster deleted successfully", "success")
        else:
            flash(f"Error deleting cluster: {response.text}", "danger")
        
        return redirect(url_for("clusters.index"))
    except Exception as e:
        logger.error(f"Error deleting cluster {collection_id}: {e}")
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for("clusters.index"))


@bp.route("/visualization/<path:filepath>")
def get_visualization(filepath):
    """Get a visualization image."""
    try:
        # Forward the request to the API
        api_url = f"{current_app.config['API_URL']}/api/clusters/visualization/{filepath}"
        response = requests.get(api_url, stream=True)
        
        if response.status_code == 200:
            # Create a temporary file for the image
            import tempfile
            import os
            
            temp_file = os.path.join(tempfile.gettempdir(), f"viz_{os.path.basename(filepath)}")
            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return send_file(temp_file, mimetype="image/png")
        else:
            flash(f"Error getting visualization: {response.text}", "danger")
            return redirect(url_for("clusters.index"))
    except Exception as e:
        logger.error(f"Error getting visualization {filepath}: {e}")
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for("clusters.index"))