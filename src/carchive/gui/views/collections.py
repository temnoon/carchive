"""
Views for collection management.
"""

import json
import requests
from uuid import UUID
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session

# Create blueprint
bp = Blueprint('collections', __name__, url_prefix='/collections')


@bp.route('/')
def list_collections():
    """List all collections."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Fetch collections from API
    try:
        response = requests.get(
            f"{current_app.config['API_BASE_URL']}/collections/",
            params={'page': page, 'per_page': per_page}
        )
        response.raise_for_status()
        data = response.json()
        
        return render_template(
            'collections/list.html',
            collections=data['collections'],
            pagination=data['pagination']
        )
    except requests.RequestException as e:
        flash(f"Error fetching collections: {str(e)}", "danger")
        return render_template('collections/list.html', collections=[])


@bp.route('/<collection_id>')
def view_collection(collection_id):
    """View a specific collection."""
    try:
        # Validate UUID format
        UUID(collection_id)
        
        # Fetch collection from API
        response = requests.get(f"{current_app.config['API_BASE_URL']}/collections/{collection_id}")
        response.raise_for_status()
        
        collection = response.json()
        return render_template('collections/view.html', collection=collection)
    except ValueError:
        flash("Invalid collection ID format", "danger")
        return redirect(url_for('collections.list_collections'))
    except requests.RequestException as e:
        flash(f"Error fetching collection: {str(e)}", "danger")
        return redirect(url_for('collections.list_collections'))


@bp.route('/create', methods=['GET', 'POST'])
def create_collection():
    """Create a new collection."""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        add_from_search = request.form.get('add_from_search') == 'on'
        
        if not name:
            flash("Collection name is required", "danger")
            return render_template('collections/create.html')
        
        try:
            # Prepare collection data
            collection_data = {
                'name': name,
                'meta_info': {'description': description} if description else {}
            }
            
            # Add items from search results if requested
            if add_from_search and 'last_search_results' in session:
                items = []
                for result in session.get('last_search_results', []):
                    if 'conversation_id' in result:
                        items.append({'conversation_id': result['conversation_id']})
                    elif 'id' in result:
                        if result.get('type') == 'message':
                            items.append({'message_id': result['id']})
                        elif result.get('type') == 'conversation':
                            items.append({'conversation_id': result['id']})
                
                if items:
                    collection_data['items'] = items
            
            # Create collection via API
            response = requests.post(
                f"{current_app.config['API_BASE_URL']}/collections/",
                json=collection_data
            )
            response.raise_for_status()
            
            result = response.json()
            flash(f"Collection '{name}' created successfully", "success")
            return redirect(url_for('collections.view_collection', collection_id=result['id']))
            
        except requests.RequestException as e:
            flash(f"Error creating collection: {str(e)}", "danger")
            return render_template('collections/create.html')
    
    return render_template('collections/create.html')


@bp.route('/<collection_id>/edit', methods=['GET', 'POST'])
def edit_collection(collection_id):
    """Edit a collection."""
    try:
        # Validate UUID format
        UUID(collection_id)
        
        if request.method == 'POST':
            name = request.form.get('name')
            description = request.form.get('description')
            
            if not name:
                flash("Collection name is required", "danger")
                return redirect(url_for('collections.edit_collection', collection_id=collection_id))
            
            # Prepare update data
            update_data = {
                'name': name
            }
            
            # Get existing meta_info from API
            get_response = requests.get(f"{current_app.config['API_BASE_URL']}/collections/{collection_id}")
            get_response.raise_for_status()
            collection = get_response.json()
            
            # Update meta_info with new description
            meta_info = collection.get('meta_info', {}) or {}
            meta_info['description'] = description
            update_data['meta_info'] = meta_info
            
            # Update collection via API
            response = requests.put(
                f"{current_app.config['API_BASE_URL']}/collections/{collection_id}",
                json=update_data
            )
            response.raise_for_status()
            
            flash(f"Collection updated successfully", "success")
            return redirect(url_for('collections.view_collection', collection_id=collection_id))
            
        else:
            # Fetch collection for editing
            response = requests.get(f"{current_app.config['API_BASE_URL']}/collections/{collection_id}")
            response.raise_for_status()
            
            collection = response.json()
            return render_template('collections/edit.html', collection=collection)
            
    except ValueError:
        flash("Invalid collection ID format", "danger")
        return redirect(url_for('collections.list_collections'))
    except requests.RequestException as e:
        flash(f"Error processing collection: {str(e)}", "danger")
        return redirect(url_for('collections.list_collections'))


@bp.route('/<collection_id>/delete', methods=['POST'])
def delete_collection(collection_id):
    """Delete a collection."""
    try:
        # Validate UUID format
        UUID(collection_id)
        
        # Delete collection via API
        response = requests.delete(f"{current_app.config['API_BASE_URL']}/collections/{collection_id}")
        response.raise_for_status()
        
        flash("Collection deleted successfully", "success")
        return redirect(url_for('collections.list_collections'))
        
    except ValueError:
        flash("Invalid collection ID format", "danger")
        return redirect(url_for('collections.list_collections'))
    except requests.RequestException as e:
        flash(f"Error deleting collection: {str(e)}", "danger")
        return redirect(url_for('collections.view_collection', collection_id=collection_id))


@bp.route('/<collection_id>/items', methods=['POST'])
def add_items(collection_id):
    """Add items to a collection."""
    try:
        # Validate UUID format
        UUID(collection_id)
        
        item_type = request.form.get('item_type')
        item_id = request.form.get('item_id')
        note = request.form.get('note')
        
        if not item_type or not item_id:
            flash("Item type and ID are required", "danger")
            return redirect(url_for('collections.view_collection', collection_id=collection_id))
        
        # Validate item ID format
        try:
            UUID(item_id)
        except ValueError:
            flash("Invalid item ID format", "danger")
            return redirect(url_for('collections.view_collection', collection_id=collection_id))
        
        # Prepare item data
        items = [{
            f"{item_type}_id": item_id,
            'meta_info': {'note': note} if note else {}
        }]
        
        # Add item via API
        response = requests.post(
            f"{current_app.config['API_BASE_URL']}/collections/{collection_id}/items",
            json={'items': items}
        )
        response.raise_for_status()
        
        flash("Item added to collection successfully", "success")
        return redirect(url_for('collections.view_collection', collection_id=collection_id))
        
    except ValueError:
        flash("Invalid collection ID format", "danger")
        return redirect(url_for('collections.list_collections'))
    except requests.RequestException as e:
        flash(f"Error adding item to collection: {str(e)}", "danger")
        return redirect(url_for('collections.view_collection', collection_id=collection_id))


@bp.route('/<collection_id>/items/<item_id>/remove', methods=['POST'])
def remove_item(collection_id, item_id):
    """Remove an item from a collection."""
    try:
        # Validate UUID formats
        UUID(collection_id)
        UUID(item_id)
        
        # Remove item via API
        response = requests.delete(
            f"{current_app.config['API_BASE_URL']}/collections/{collection_id}/items/{item_id}"
        )
        response.raise_for_status()
        
        flash("Item removed from collection successfully", "success")
        return redirect(url_for('collections.view_collection', collection_id=collection_id))
        
    except ValueError:
        flash("Invalid ID format", "danger")
        return redirect(url_for('collections.view_collection', collection_id=collection_id))
    except requests.RequestException as e:
        flash(f"Error removing item from collection: {str(e)}", "danger")
        return redirect(url_for('collections.view_collection', collection_id=collection_id))


@bp.route('/<collection_id>/render')
def render_collection(collection_id):
    """Render a collection as HTML."""
    try:
        # Validate UUID format
        UUID(collection_id)
        
        # Request rendered HTML directly from API
        response = requests.get(
            f"{current_app.config['API_BASE_URL']}/collections/{collection_id}/render",
            headers={'Accept': 'text/html'}
        )
        response.raise_for_status()
        
        # Return HTML content directly
        return response.text, 200, {'Content-Type': 'text/html'}
        
    except ValueError:
        flash("Invalid collection ID format", "danger")
        return redirect(url_for('collections.list_collections'))
    except requests.RequestException as e:
        flash(f"Error rendering collection: {str(e)}", "danger")
        return redirect(url_for('collections.view_collection', collection_id=collection_id))