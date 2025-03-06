"""
Search routes for the carchive2 GUI.
"""

import requests
import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, current_app, request, redirect, url_for, flash, jsonify
import logging

logger = logging.getLogger(__name__)
bp = Blueprint('search', __name__, url_prefix='/search')

@bp.route('/')
def search_form():
    """Display search form."""
    # Get providers, roles for filters
    try:
        # Get providers
        api_url = current_app.config.get('API_URL', 'http://localhost:5000')
        providers_response = requests.get(f"{api_url}/api/providers")
        if providers_response.status_code == 200:
            providers = providers_response.json()
        else:
            providers = []
            logger.warning(f"Failed to fetch providers: {providers_response.status_code}")
        
        # Get saved searches
        saved_searches_response = requests.get(f"{api_url}/api/search/saved?per_page=5")
        if saved_searches_response.status_code == 200:
            saved_searches = saved_searches_response.json().get('searches', [])
        else:
            saved_searches = []
            logger.warning(f"Failed to fetch saved searches: {saved_searches_response.status_code}")
        
        return render_template('search/form.html', 
                             providers=providers,
                             saved_searches=saved_searches)
    except Exception as e:
        logger.error(f"Error fetching data for search form: {e}")
        return render_template('search/form.html', 
                             providers=[],
                             saved_searches=[])

@bp.route('/results')
def search_results():
    """Display search results."""
    # Get basic query parameters
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('search.search_form'))
    
    search_type = request.args.get('type', 'all')
    mode = request.args.get('mode', 'substring')
    date_range = request.args.get('date_range', 'all')
    sort = request.args.get('sort', 'relevance')
    semantic = request.args.get('semantic', 'false') == 'true'
    exact = request.args.get('exact', 'false') == 'true'
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Map GUI date range to API parameters
    days = None
    start_date = None
    end_date = None
    
    if date_range == 'today':
        days = 1
    elif date_range == 'yesterday':
        start_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')
    elif date_range == 'week':
        days = 7
    elif date_range == 'month':
        days = 30
    elif date_range == 'year':
        days = 365
    
    # Determine which endpoint to use based on semantic search toggle
    api_url = current_app.config.get('API_URL', 'http://localhost:5000')
    
    try:
        if semantic:
            # Use the vector search endpoint
            search_params = {
                'q': query,
                'limit': per_page
            }
            response = requests.get(f"{api_url}/api/search/vector", params=search_params)
            
            if response.status_code != 200:
                logger.error(f"Vector search API error: {response.status_code} - {response.text}")
                flash(f"Search error: {response.status_code}", "danger")
                return render_template('search/results.html', query=query, results=None, error=True)
            
            # Process vector search results
            data = response.json()
            results = {
                'query': query,
                'results': data.get('results', []),
                'total_count': len(data.get('results', [])),
                'search_type': 'vector',
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': len(data.get('results', [])),
                    'pages': (len(data.get('results', [])) + per_page - 1) // per_page
                }
            }
            
        else:
            # Use the unified search endpoint
            # Convert exact match to appropriate mode
            if exact:
                mode = 'exact'
            
            # Map the GUI search type to entity types for the API
            entity_types = []
            if search_type == 'all':
                entity_types = ['all']
            elif search_type == 'conversations':
                entity_types = ['conversation']
            elif search_type == 'messages':
                entity_types = ['message']
            elif search_type == 'media':
                entity_types = ['media']
            
            # Prepare parameters for the unified search
            search_params = {
                'q': query,
                'entity_type': entity_types,
                'mode': mode,
                'sort': sort,
                'limit': per_page,
                'offset': (page - 1) * per_page
            }
            
            # Add date filters if applicable
            if days:
                search_params['days'] = days
            if start_date:
                search_params['start_date'] = start_date
            if end_date:
                search_params['end_date'] = end_date
            
            # Add selected roles if provided
            roles = request.args.getlist('role')
            if roles:
                search_params['role'] = roles
            
            # Add selected providers if provided
            providers = request.args.getlist('provider')
            if providers:
                search_params['provider'] = providers
            
            # Make the API request
            response = requests.get(f"{api_url}/api/search/unified", params=search_params)
            
            if response.status_code != 200:
                logger.error(f"Unified search API error: {response.status_code} - {response.text}")
                flash(f"Search error: {response.status_code}", "danger")
                return render_template('search/results.html', query=query, results=None, error=True)
            
            # Process unified search results
            results = response.json()
        
        # Pass the results to the template
        return render_template('search/results.html', 
                             query=query,
                             results=results,
                             search_type=search_type,
                             mode=mode,
                             date_range=date_range,
                             sort=sort,
                             semantic=semantic,
                             exact=exact,
                             page=page,
                             per_page=per_page,
                             error=False)
    
    except Exception as e:
        logger.error(f"Error performing search: {e}")
        flash(f"Search error: {str(e)}", "danger")
        return render_template('search/results.html', query=query, results=None, error=True)

@bp.route('/save', methods=['POST'])
def save_search():
    """Save a search query."""
    try:
        # Get form data
        data = request.form
        name = data.get('name')
        query = data.get('query')
        search_type = data.get('type', 'all')
        
        # Additional criteria
        criteria = {
            'mode': data.get('mode', 'substring'),
            'date_range': data.get('date_range', 'all'),
            'sort': data.get('sort', 'relevance'),
            'semantic': data.get('semantic', 'false') == 'true',
            'exact': data.get('exact', 'false') == 'true',
            'roles': request.form.getlist('role'),
            'providers': request.form.getlist('provider')
        }
        
        # Make API request to save the search
        api_url = current_app.config.get('API_URL', 'http://localhost:5000')
        response = requests.post(
            f"{api_url}/api/search/save",
            json={
                'name': name,
                'query': query,
                'type': search_type,
                'criteria': criteria
            }
        )
        
        if response.status_code == 200:
            flash("Search saved successfully", "success")
        else:
            flash(f"Error saving search: {response.text}", "danger")
        
        # Redirect back to search results
        return redirect(url_for('search.search_results', q=query, type=search_type))
        
    except Exception as e:
        logger.error(f"Error saving search: {e}")
        flash(f"Error saving search: {str(e)}", "danger")
        return redirect(url_for('search.search_form'))