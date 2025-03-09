"""
Gencom views for the GUI.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from carchive.database.session import get_session
from carchive.database.models import AgentOutput, Message, Conversation, Chunk, Provider
from carchive.pipelines.content_tasks import ContentTaskManager
from sqlalchemy import func, desc, text
import uuid
import logging
import json
import requests
from collections import Counter
from urllib.parse import urlencode
import io
import base64
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use Agg backend to avoid display requirement

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
bp = Blueprint('gencom', __name__, url_prefix='/gencom')

# Configure the content providers and output types
PROVIDERS = ["ollama", "openai", "anthropic", "groq"]
OUTPUT_TYPES = [
    {"id": "gencom", "name": "General Comment", "description": "General AI comment on content"},
    {"id": "gencom_summary", "name": "Summary", "description": "Concise summary of the content"},
    {"id": "gencom_category", "name": "Category", "description": "Thematic category assignment"},
    {"id": "gencom_quality", "name": "Quality Rating", "description": "Content quality evaluation (1-10)"},
    {"id": "gencom_title", "name": "Title", "description": "Concise title for the content"}
]

@bp.route('/')
def index():
    """Main Gencom dashboard page."""
    return render_template('gencom/index.html', 
                          providers=PROVIDERS,
                          output_types=OUTPUT_TYPES)

@bp.route('/generate', methods=['GET', 'POST'])
def generate():
    """Generate AI comment for a single target."""
    if request.method == 'POST':
        # Process form submission
        target_type = request.form.get('target_type')
        target_id = request.form.get('target_id')
        output_type = request.form.get('output_type', 'gencom')
        provider = request.form.get('provider', 'ollama')
        prompt_template = request.form.get('prompt_template')
        max_words = request.form.get('max_words')
        override = 'override' in request.form
        generate_embedding = 'generate_embedding' in request.form
        
        try:
            # Validate inputs
            if not target_id or not target_type:
                flash("Target ID and Target Type are required", "error")
                return redirect(url_for('gencom.generate'))
            
            # Validate target exists
            with get_session() as session:
                if target_type == 'message':
                    target = session.query(Message).filter_by(id=target_id).first()
                elif target_type == 'conversation':
                    target = session.query(Conversation).filter_by(id=target_id).first()
                elif target_type == 'chunk':
                    target = session.query(Chunk).filter_by(id=target_id).first()
                else:
                    flash(f"Invalid target type: {target_type}", "error")
                    return redirect(url_for('gencom.generate'))
                
                if not target:
                    flash(f"{target_type.capitalize()} with ID {target_id} not found", "error")
                    return redirect(url_for('gencom.generate'))
            
            # Create a Content Task Manager
            manager = ContentTaskManager(provider=provider)
            
            # Run the task
            output = manager.run_task_for_target(
                target_type=target_type,
                target_id=target_id,
                task=output_type,
                prompt_template=prompt_template,
                override=override,
                max_words=int(max_words) if max_words else None
            )
            
            # Generate embedding if requested
            if generate_embedding:
                from carchive.embeddings.embed_manager import EmbeddingManager
                embedding_manager = EmbeddingManager(provider=provider)
                embedding = embedding_manager.embed_texts(
                    texts=[output.content],
                    parent_ids=[str(output.id)],
                    parent_type="agent_output"
                )
                flash(f"Embedding generated with ID: {embedding[0].id}", "success")
            
            flash(f"Comment generated successfully with ID: {output.id}", "success")
            return redirect(url_for('gencom.view', output_id=output.id))
            
        except Exception as e:
            logger.error(f"Error generating comment: {e}")
            flash(f"Error: {str(e)}", "error")
            return redirect(url_for('gencom.generate'))
    
    # GET request: show form
    target_type = request.args.get('target_type')
    target_id = request.args.get('target_id')
    output_type = request.args.get('output_type', 'gencom')
    
    # Show form with target filled in if provided
    return render_template('gencom/generate.html', 
                          target_type=target_type,
                          target_id=target_id,
                          output_type=output_type,
                          providers=PROVIDERS,
                          output_types=OUTPUT_TYPES)

@bp.route('/view/<uuid:output_id>')
def view(output_id):
    """View details of a single gencom output."""
    try:
        with get_session() as session:
            # Get the agent output
            output = session.query(AgentOutput).filter_by(id=output_id).first()
            if not output:
                flash(f"Comment with ID {output_id} not found", "error")
                return redirect(url_for('gencom.index'))
            
            # Get the target object data
            target = None
            target_content = None
            target_link = None
            
            if output.target_type == 'message':
                target = session.query(Message).filter_by(id=output.target_id).first()
                if target:
                    target_content = target.content
                    target_link = url_for('messages.view', message_id=target.id)
            elif output.target_type == 'conversation':
                target = session.query(Conversation).filter_by(id=output.target_id).first()
                if target:
                    target_content = f"Conversation: {target.title or 'Untitled'}"
                    target_link = url_for('conversations.view', conversation_id=target.id)
            elif output.target_type == 'chunk':
                target = session.query(Chunk).filter_by(id=output.target_id).first()
                if target:
                    target_content = target.content
                    if target.message_id:
                        target_link = url_for('messages.view', message_id=target.message_id)
            
            # Check for embeddings
            has_embedding = False
            from carchive.database.models import Embedding
            embedding = session.query(Embedding).filter_by(
                parent_type="agent_output",
                parent_id=str(output_id)
            ).first()
            if embedding:
                has_embedding = True
            
            return render_template('gencom/view.html', 
                                  output=output,
                                  target_content=target_content,
                                  target_link=target_link,
                                  has_embedding=has_embedding)
    
    except Exception as e:
        logger.error(f"Error viewing output: {e}")
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for('gencom.index'))

@bp.route('/batch', methods=['GET', 'POST'])
def batch():
    """Batch generation of AI comments."""
    if request.method == 'POST':
        # Process form submission
        target_type = request.form.get('target_type')
        output_type = request.form.get('output_type', 'gencom')
        provider = request.form.get('provider', 'ollama')
        prompt_template = request.form.get('prompt_template')
        max_words = request.form.get('max_words')
        min_word_count = request.form.get('min_word_count', '5')
        limit = request.form.get('limit')
        roles = request.form.getlist('roles') or None
        source_provider = request.form.get('source_provider')
        days = request.form.get('days')
        override = 'override' in request.form
        generate_embedding = 'generate_embedding' in request.form
        
        try:
            # Build API request data
            data = {
                "target_type": target_type,
                "output_type": output_type,
                "provider": provider,
                "override": override,
                "generate_embedding": generate_embedding,
                "min_word_count": int(min_word_count) if min_word_count else 5
            }
            
            # Add optional parameters
            if prompt_template:
                data["prompt_template"] = prompt_template
            if max_words:
                data["max_words"] = int(max_words)
            if limit:
                data["limit"] = int(limit)
            if roles:
                data["roles"] = roles
            if source_provider and source_provider != "":
                data["source_provider"] = source_provider
            if days:
                data["days"] = int(days)
            
            # Make API request to our batch endpoint
            response = requests.post(
                f"http://localhost:5000/api/gencom/batch", 
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                flash(f"Batch processing complete: {result['processed']} processed, {result['skipped']} skipped, {result['failed']} failed", "success")
                
                if generate_embedding and 'embedding_success' in result:
                    flash(f"Embeddings: {result['embedding_success']} created, {result['embedding_failed']} failed", "info")
                
                return redirect(url_for('gencom.list'))
            else:
                error_message = response.json().get('detail', 'Unknown error')
                flash(f"Error: {error_message}", "error")
                return redirect(url_for('gencom.batch'))
            
        except Exception as e:
            logger.error(f"Error in batch generation: {e}")
            flash(f"Error: {str(e)}", "error")
            return redirect(url_for('gencom.batch'))
    
    # GET request: show form
    # Get available providers from database for dropdown
    providers_db = []
    try:
        with get_session() as session:
            providers_db = [(p.id, p.name) for p in session.query(Provider).all()]
    except Exception:
        pass  # If we can't get providers, just use the default list
    
    return render_template('gencom/batch.html', 
                          providers=PROVIDERS,
                          output_types=OUTPUT_TYPES,
                          message_roles=["user", "assistant", "system", "tool"],
                          source_providers=providers_db)

@bp.route('/list')
def list():
    """List all gencom outputs with filtering."""
    try:
        # Get filter parameters
        output_type = request.args.get('output_type', 'gencom')
        target_type = request.args.get('target_type')
        
        # Pagination parameters
        page = int(request.args.get('page', 1))
        per_page = 20
        
        with get_session() as session:
            # Build query
            query = session.query(AgentOutput).filter(
                AgentOutput.output_type == output_type
            )
            
            # Apply target type filter if specified
            if target_type:
                query = query.filter(AgentOutput.target_type == target_type)
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            query = query.order_by(AgentOutput.created_at.desc())
            query = query.offset((page - 1) * per_page).limit(per_page)
            
            results = query.all()
            
            # Calculate pagination data
            total_pages = (total + per_page - 1) // per_page
            
            # Enhance results with target information
            enhanced_results = []
            for output in results:
                item = {
                    "output": output,
                    "target_content": None,
                    "target_link": None
                }
                
                # Get target information
                if output.target_type == 'message':
                    message = session.query(Message).filter_by(id=output.target_id).first()
                    if message:
                        item["target_content"] = message.content[:100] + "..." if len(message.content) > 100 else message.content
                        item["target_link"] = url_for('messages.view', message_id=message.id)
                
                elif output.target_type == 'conversation':
                    conversation = session.query(Conversation).filter_by(id=output.target_id).first()
                    if conversation:
                        item["target_content"] = f"Conversation: {conversation.title or 'Untitled'}"
                        item["target_link"] = url_for('conversations.view', conversation_id=conversation.id)
                
                elif output.target_type == 'chunk':
                    chunk = session.query(Chunk).filter_by(id=output.target_id).first()
                    if chunk:
                        item["target_content"] = chunk.content[:100] + "..." if len(chunk.content) > 100 else chunk.content
                        if chunk.message_id:
                            item["target_link"] = url_for('messages.view', message_id=chunk.message_id)
                
                enhanced_results.append(item)
            
            return render_template('gencom/list.html',
                                  results=enhanced_results,
                                  output_type=output_type,
                                  target_type=target_type,
                                  output_types=OUTPUT_TYPES,
                                  page=page,
                                  total_pages=total_pages,
                                  total=total)
    
    except Exception as e:
        logger.error(f"Error listing outputs: {e}")
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for('gencom.index'))

@bp.route('/purge', methods=['GET', 'POST'])
def purge():
    """Purge gencom outputs matching criteria."""
    if request.method == 'POST':
        # Process form submission
        output_type = request.form.get('output_type')
        target_type = request.form.get('target_type', 'message')
        conversation_id = request.form.get('conversation_id')
        source_provider = request.form.get('source_provider')
        role = request.form.get('role')
        
        try:
            # Build API request data
            data = {
                "output_type": output_type,
                "target_type": target_type,
            }
            
            # Add optional parameters
            if conversation_id:
                data["conversation_id"] = conversation_id
            if source_provider and source_provider != "":
                data["source_provider"] = source_provider
            if role and role != "":
                data["role"] = role
            
            # Make API request
            response = requests.post(
                f"http://localhost:5000/api/gencom/purge", 
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                flash(f"{result['message']}", "success")
                return redirect(url_for('gencom.list', output_type=output_type))
            else:
                error_message = response.json().get('detail', 'Unknown error')
                flash(f"Error: {error_message}", "error")
                return redirect(url_for('gencom.purge'))
            
        except Exception as e:
            logger.error(f"Error purging outputs: {e}")
            flash(f"Error: {str(e)}", "error")
            return redirect(url_for('gencom.purge'))
    
    # GET request: show form
    output_type = request.args.get('output_type')
    
    # Get available providers from database for dropdown
    providers_db = []
    try:
        with get_session() as session:
            providers_db = [(p.id, p.name) for p in session.query(Provider).all()]
    except Exception:
        pass  # If we can't get providers, just use the default list
    
    return render_template('gencom/purge.html',
                          output_type=output_type,
                          output_types=OUTPUT_TYPES,
                          source_providers=providers_db,
                          message_roles=["user", "assistant", "system", "tool"])

@bp.route('/categories')
def categories():
    """Display statistics about gencom categories."""
    try:
        # Get parameters
        target_type = request.args.get('target_type', 'message')
        output_type = request.args.get('output_type', 'gencom_category')
        min_count = int(request.args.get('min_count', 3))
        limit = int(request.args.get('limit', 20))
        exclude_generic = request.args.get('exclude_generic') == 'true'
        role = request.args.get('role')
        format_type = request.args.get('format', 'chart')
        chart_type = request.args.get('chart_type', 'pie')
        
        # Make API request
        params = {
            'target_type': target_type,
            'output_type': output_type,
            'min_count': min_count,
            'limit': limit,
            'exclude_generic': exclude_generic
        }
        
        if role:
            params['role'] = role
            
        response = requests.get(
            f"http://localhost:5000/api/gencom/categories", 
            params=params
        )
        
        if response.status_code != 200:
            error_message = response.json().get('detail', 'Unknown error')
            flash(f"Error: {error_message}", "error")
            return redirect(url_for('gencom.index'))
        
        categories_data = response.json()
        
        # If format is chart, generate a chart
        chart_img = None
        if format_type == 'chart' and categories_data:
            # Create chart
            plt.figure(figsize=(10, 6))
            
            if chart_type == 'pie':
                labels = [item['category'] for item in categories_data]
                sizes = [item['total'] for item in categories_data]
                
                # Generate colors
                colors = plt.cm.tab20.colors
                
                # Create pie chart
                plt.pie(sizes, labels=None, autopct='%1.1f%%', startangle=140, colors=colors)
                plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
                
                # Add legend outside the pie
                plt.legend(labels, loc="center left", bbox_to_anchor=(1, 0.5))
                plt.title(f"Category Distribution ({target_type}s)")
                
            elif chart_type == 'bar':
                categories = [item['category'] for item in categories_data]
                counts = [item['total'] for item in categories_data]
                
                # Create horizontal bar chart for better label readability
                y_pos = range(len(categories))
                plt.barh(y_pos, counts)
                plt.yticks(y_pos, categories)
                plt.xlabel('Count')
                plt.title(f"Category Distribution ({target_type}s)")
                
            # Convert plot to base64 for embedding in HTML
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', bbox_inches='tight')
            buffer.seek(0)
            chart_img = base64.b64encode(buffer.getvalue()).decode('utf-8')
            plt.close()
        
        return render_template('gencom/categories.html',
                              categories=categories_data,
                              target_type=target_type,
                              output_type=output_type,
                              min_count=min_count,
                              limit=limit,
                              exclude_generic=exclude_generic,
                              role=role,
                              format_type=format_type,
                              chart_type=chart_type,
                              chart_img=chart_img,
                              output_types=OUTPUT_TYPES,
                              message_roles=["user", "assistant", "system", "tool"])
    
    except Exception as e:
        logger.error(f"Error analyzing categories: {e}")
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for('gencom.index'))