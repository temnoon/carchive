"""
GUI views for embedding operations.
"""

import logging
import json
import requests
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, current_app, flash, jsonify
)

logger = logging.getLogger(__name__)

bp = Blueprint("embeddings", __name__, url_prefix="/embeddings")

@bp.route("/")
def index():
    """Embeddings dashboard view."""
    try:
        # Get embeddings stats
        api_url = f"{current_app.config['API_URL']}/api/embeddings/status"
        response = requests.get(api_url)
        
        if response.status_code == 200:
            stats = response.json()
        else:
            stats = {"error": f"API Error: {response.status_code}"}
            flash(f"Error loading embedding statistics: {response.text}", "danger")
        
        # Get paginated embeddings list
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        provider = request.args.get("provider")
        model = request.args.get("model")
        
        params = {"page": page, "per_page": per_page}
        if provider:
            params["provider"] = provider
        if model:
            params["model"] = model
            
        api_url = f"{current_app.config['API_URL']}/api/embeddings/"
        response = requests.get(api_url, params=params)
        
        if response.status_code == 200:
            embeddings_data = response.json()
        else:
            embeddings_data = {"embeddings": [], "pagination": {"page": 1, "pages": 1, "total": 0}}
            flash(f"Error loading embeddings: {response.text}", "danger")
        
        return render_template(
            "embeddings/index.html",
            stats=stats,
            embeddings=embeddings_data["embeddings"],
            pagination=embeddings_data["pagination"],
            provider_filter=provider,
            model_filter=model
        )
    except Exception as e:
        logger.error(f"Error in embeddings index view: {e}")
        flash(f"Error: {str(e)}", "danger")
        return render_template("embeddings/index.html", stats={}, embeddings=[], pagination={"page": 1, "pages": 1, "total": 0})


@bp.route("/generate", methods=["GET", "POST"])
def generate():
    """Generate embeddings view."""
    if request.method == "POST":
        try:
            # Process form data
            embed_type = request.form.get("embed_type")
            provider = request.form.get("provider")
            model = request.form.get("model")
            
            api_url = f"{current_app.config['API_URL']}/api/embeddings/"
            
            if embed_type == "text":
                # Text embedding
                text = request.form.get("text", "")
                if not text:
                    flash("No text provided", "warning")
                    return redirect(url_for("embeddings.generate"))
                
                # Send to API
                data = {
                    "text": text,
                    "provider": provider,
                    "model": model
                }
                response = requests.post(api_url, json=data)
                
            elif embed_type == "messages":
                # Message embedding
                message_ids = request.form.get("message_ids", "").strip().split("\n")
                message_ids = [m.strip() for m in message_ids if m.strip()]
                
                if not message_ids:
                    flash("No message IDs provided", "warning")
                    return redirect(url_for("embeddings.generate"))
                
                # Send to API
                data = {
                    "message_ids": message_ids,
                    "provider": provider,
                    "model": model
                }
                response = requests.post(api_url, json=data)
                
            elif embed_type == "embed_all":
                # Embed all messages
                min_word_count = request.form.get("min_word_count", 5, type=int)
                include_roles = request.form.getlist("include_roles")
                
                options = {
                    "min_word_count": min_word_count,
                    "exclude_empty": True,
                    "include_roles": include_roles if include_roles else ["user", "assistant"]
                }
                
                # Send to API
                data = {
                    "embed_all": True,
                    "options": options,
                    "provider": provider,
                    "model": model
                }
                response = requests.post(api_url, json=data)
                
            else:
                flash("Invalid embedding type", "danger")
                return redirect(url_for("embeddings.generate"))
            
            # Handle API response
            if response.status_code == 200:
                result = response.json()
                flash(result.get("message", "Embeddings generated successfully"), "success")
            else:
                error_msg = f"API Error: {response.status_code}"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_msg = error_data["error"]
                except:
                    pass
                flash(f"Error: {error_msg}", "danger")
            
            return redirect(url_for("embeddings.index"))
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            flash(f"Error: {str(e)}", "danger")
            return redirect(url_for("embeddings.generate"))
    
    # GET request - show form
    return render_template("embeddings/generate.html")


@bp.route("/<embedding_id>")
def view(embedding_id):
    """View a specific embedding."""
    try:
        # Get embedding details
        api_url = f"{current_app.config['API_URL']}/api/embeddings/{embedding_id}"
        response = requests.get(api_url)
        
        if response.status_code == 200:
            embedding = response.json()
        else:
            flash(f"Error loading embedding: {response.text}", "danger")
            return redirect(url_for("embeddings.index"))
        
        return render_template("embeddings/view.html", embedding=embedding)
    except Exception as e:
        logger.error(f"Error viewing embedding {embedding_id}: {e}")
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for("embeddings.index"))


@bp.route("/<embedding_id>/delete", methods=["POST"])
def delete(embedding_id):
    """Delete a specific embedding."""
    try:
        # Delete embedding
        api_url = f"{current_app.config['API_URL']}/api/embeddings/{embedding_id}"
        response = requests.delete(api_url)
        
        if response.status_code == 200:
            flash("Embedding deleted successfully", "success")
        else:
            flash(f"Error deleting embedding: {response.text}", "danger")
        
        return redirect(url_for("embeddings.index"))
    except Exception as e:
        logger.error(f"Error deleting embedding {embedding_id}: {e}")
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for("embeddings.index"))