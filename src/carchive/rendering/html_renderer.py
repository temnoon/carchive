# src/carchive/rendering/html_renderer.py
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

from carchive.database.session import get_session
from carchive.database.models import Collection, CollectionItem, Message, Chunk, Conversation
from carchive.rendering.base_renderer import ContentRenderer
from carchive.rendering.markdown_renderer import MarkdownRenderer
from carchive.rendering.template_engine import TemplateEngine

class HTMLRenderer(ContentRenderer):
    """
    HTML renderer implementation for rendering content to HTML format.
    """
    
    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize with optional templates directory.
        """
        self.markdown_renderer = MarkdownRenderer()
        self.template_engine = TemplateEngine(templates_dir)
    
    def render_text(self, text: str) -> str:
        """
        Render text content to HTML.
        """
        return self.markdown_renderer.render(text)
    
    def render_collection(self, collection_name: str, output_path: str, 
                      template: str = "default", include_metadata: bool = False) -> str:
        """
        Render a collection to HTML.
        """
        with get_session() as session:
            collection = session.query(Collection).filter_by(name=collection_name).first()
            if not collection:
                raise ValueError(f"Collection '{collection_name}' not found.")
            
            items = session.query(CollectionItem).filter_by(collection_id=collection.id).all()
            if not items:
                raise ValueError(f"Collection '{collection_name}' has no items.")
            
            rendered_items = []
            
            for item in items:
                role = "unknown"
                content = ""
                metadata = {}
                header = ""
                
                if item.message_id is not None:
                    message = session.query(Message).filter_by(id=item.message_id).first()
                    if message is not None and isinstance(message.content, str):
                        content = self.markdown_renderer.render(message.content)
                        metadata = message.meta_info or {}
                        role = self._determine_role(metadata)
                        
                        # Add conversation info as header if available
                        if message.conversation_id is not None:
                            convo = session.query(Conversation).filter_by(id=message.conversation_id).first()
                            if convo:
                                header = f"From conversation: {convo.title or '(Untitled)'}"
                                
                elif item.chunk_id is not None:
                    chunk = session.query(Chunk).filter_by(id=item.chunk_id).first()
                    if chunk is not None and isinstance(chunk.content, str):
                        content = self.markdown_renderer.render(chunk.content)
                        metadata = chunk.meta_info or {}
                
                if content:
                    rendered_items.append({
                        "role": role,
                        "content": content,
                        "metadata": metadata,
                        "header": header
                    })
            
            if not rendered_items:
                raise ValueError(f"No renderable content found in collection '{collection_name}'.")
            
            # Render using template
            context = {
                "title": f"Collection: {collection_name}",
                "items": rendered_items,
                "include_metadata": include_metadata,
                "show_color_key": True
            }
            
            html_content = self.template_engine.render(template, context)
            
            # Write to file if output_path provided
            if output_path:
                Path(output_path).write_text(html_content, encoding="utf-8")
                
            return html_content
    
    def render_conversation(self, conversation_id: str, output_path: str, 
                           template: str = "default", include_raw: bool = False,
                           gencom_fields: str = "none", gencom_field_labels: dict = None,
                           media_display_mode: str = "inline") -> str:
        """
        Render a conversation to HTML.
        
        Args:
            conversation_id: The ID of the conversation to render
            output_path: Path to save the output
            template: Template name to use for rendering
            include_raw: Whether to include raw markdown in the output
            gencom_fields: Which gencom fields to include - "none", "all", or comma-separated list
            gencom_field_labels: Dict mapping gencom field names to display labels
            media_display_mode: How to display media - "inline", "gallery", or "thumbnails"
        """
        with get_session() as session:
            conversation = session.query(Conversation).filter_by(id=conversation_id).first()
            if not conversation:
                raise ValueError(f"Conversation '{conversation_id}' not found.")
            
            messages = session.query(Message).filter_by(conversation_id=conversation_id).order_by(Message.created_at).all()
            if not messages:
                raise ValueError(f"No messages found in conversation '{conversation_id}'.")
            
            rendered_items = []
            
            for message in messages:
                if not isinstance(message.content, str) or not message.content:
                    continue
                
                role = self._determine_role(message.meta_info)
                content = message.content
                
                # Process gencom fields if present in metadata
                gencom_html = ""
                if gencom_fields != "none" and message.meta_info and "gencom" in message.meta_info:
                    gencom_data = message.meta_info.get("gencom", {})
                    if gencom_data:
                        gencom_html = self._render_gencom_fields(
                            gencom_data, 
                            gencom_fields, 
                            gencom_field_labels or {}
                        )
                
                # Include raw markdown before rendered content if requested
                if include_raw:
                    raw_content = f"<pre>{content}</pre><hr>"
                    content = raw_content + self.markdown_renderer.render(content, str(message.id))
                else:
                    content = self.markdown_renderer.render(content, str(message.id))
                
                # Add gencom HTML at the end of the content if present
                if gencom_html:
                    content = f"{content}\n{gencom_html}"
                
                # Create rendered item
                rendered_items.append({
                    "role": role,
                    "content": content,
                    "metadata": message.meta_info,
                    "message_id": str(message.id)
                })
            
            if not rendered_items:
                raise ValueError(f"No renderable content found in conversation '{conversation_id}'.")
            
            # Render using template
            context = {
                "title": f"Conversation: {conversation.title or conversation_id}",
                "subtitle": f"Created: {conversation.created_at}",
                "items": rendered_items,
                "include_metadata": include_raw,
                "show_color_key": True,
                "media_display_mode": media_display_mode
            }
            
            html_content = self.template_engine.render(template, context)
            
            # Write to file if output_path provided
            if output_path:
                Path(output_path).write_text(html_content, encoding="utf-8")
                
            return html_content
            
    def _render_gencom_fields(self, gencom_data: dict, gencom_fields: str, field_labels: dict = None) -> str:
        """
        Render gencom fields as HTML.
        
        Args:
            gencom_data: Dictionary of gencom fields and values
            gencom_fields: Which fields to include - "none", "all", or comma-separated list
            field_labels: Optional dict mapping field names to display labels
        
        Returns:
            HTML string of rendered gencom fields
        """
        if not gencom_data or gencom_fields == "none":
            return ""
            
        # Determine which fields to display
        fields_to_show = []
        if gencom_fields == "all":
            fields_to_show = list(gencom_data.keys())
        else:
            # Parse comma-separated list
            requested_fields = [f.strip() for f in gencom_fields.split(",")]
            fields_to_show = [f for f in requested_fields if f in gencom_data]
            
        if not fields_to_show:
            return ""
            
        # Build HTML
        field_labels = field_labels or {}
        html = ['<div class="gencom-fields">']
        html.append('<h3>Agent Thought Process</h3>')
        
        for field in fields_to_show:
            # Get display label (use field name if no label provided)
            label = field_labels.get(field, field.replace('_', ' ').title())
            value = gencom_data.get(field, "")
            
            # Render the value as markdown
            rendered_value = self.markdown_renderer.render(value)
            
            # Add to HTML
            html.append(f'<div class="gencom-field">')
            html.append(f'<div class="gencom-field-label">{label}</div>')
            html.append(f'<div class="gencom-field-value">{rendered_value}</div>')
            html.append('</div>')
            
        html.append('</div>')
        return "\n".join(html)
            
    def render_search_results(self, results: List[Dict[str, Any]], output_path: str, 
                            template: str = "default") -> str:
        """
        Render search results to HTML.
        """
        rendered_items = []
        
        for result in results:
            content = result.get("content", "")
            metadata = result.get("metadata", {})
            role = self._determine_role(metadata)
            
            # Add a header with the source information
            header = ""
            if "source" in result:
                header = f"Source: {result['source']}"
            
            rendered_items.append({
                "role": role,
                "content": self.markdown_renderer.render(content),
                "metadata": metadata,
                "header": header
            })
        
        if not rendered_items:
            raise ValueError("No renderable content found in search results.")
        
        # Render using template
        context = {
            "title": "Search Results",
            "items": rendered_items,
            "include_metadata": False,
            "show_color_key": True
        }
        
        html_content = self.template_engine.render(template, context)
        
        # Write to file if output_path provided
        if output_path:
            Path(output_path).write_text(html_content, encoding="utf-8")
            
        return html_content
    
    def _determine_role(self, metadata: Optional[Dict[str, Any]]) -> str:
        """
        Determine the role from metadata.
        """
        if not metadata:
            return "unknown"
        return metadata.get("author_role", "unknown")