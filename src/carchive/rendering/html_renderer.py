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
                           template: str = "default", include_raw: bool = False) -> str:
        """
        Render a conversation to HTML.
        """
        with get_session() as session:
            conversation = session.query(Conversation).filter_by(id=conversation_id).first()
            if not conversation:
                raise ValueError(f"Conversation '{conversation_id}' not found.")
            
            messages = session.query(Message).filter_by(conversation_id=conversation_id).all()
            if not messages:
                raise ValueError(f"No messages found in conversation '{conversation_id}'.")
            
            rendered_items = []
            
            for message in messages:
                if not isinstance(message.content, str) or not message.content:
                    continue
                
                role = self._determine_role(message.meta_info)
                content = message.content
                
                # Include raw markdown before rendered content if requested
                if include_raw:
                    raw_content = f"<pre>{content}</pre><hr>"
                    content = raw_content + self.markdown_renderer.render(content, str(message.id))
                else:
                    content = self.markdown_renderer.render(content, str(message.id))
                
                rendered_items.append({
                    "role": role,
                    "content": content,
                    "metadata": message.meta_info
                })
            
            if not rendered_items:
                raise ValueError(f"No renderable content found in conversation '{conversation_id}'.")
            
            # Render using template
            context = {
                "title": f"Conversation: {conversation.title or conversation_id}",
                "subtitle": f"Created: {conversation.created_at}",
                "items": rendered_items,
                "include_metadata": include_raw,
                "show_color_key": True
            }
            
            html_content = self.template_engine.render(template, context)
            
            # Write to file if output_path provided
            if output_path:
                Path(output_path).write_text(html_content, encoding="utf-8")
                
            return html_content
            
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