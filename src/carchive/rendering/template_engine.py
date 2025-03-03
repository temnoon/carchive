# src/carchive/rendering/template_engine.py
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from jinja2 import Environment, FileSystemLoader, select_autoescape

class TemplateEngine:
    """
    Template engine for rendering HTML and other formats using Jinja2.
    """
    
    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize with templates directory.
        """
        # Default templates directory is in the package
        if templates_dir is None:
            current_dir = Path(__file__).parent
            templates_dir = current_dir / "templates"
            
            # Create templates directory if it doesn't exist
            if not templates_dir.exists():
                templates_dir.mkdir(parents=True, exist_ok=True)
                
                # Create default template
                default_template = templates_dir / "default.html"
                if not default_template.exists():
                    self._create_default_template(default_template)
        
        self.templates_dir = Path(templates_dir)
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render content using a template.
        """
        # Ensure template has .html extension
        if not template_name.endswith('.html'):
            template_name = f"{template_name}.html"
            
        template = self.env.get_template(template_name)
        return template.render(**context)
    
    def get_available_templates(self) -> List[str]:
        """
        Get list of available templates.
        """
        return [p.stem for p in self.templates_dir.glob('*.html')]
    
    def _create_default_template(self, template_path: Path) -> None:
        """
        Create default template if it doesn't exist.
        """
        default_template_content = """<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8"/>
  <title>{{ title }}</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 1em auto; max-width: 800px; line-height: 1.5; }
    .role-user { background: #e0f7fa; margin: .75em 0; padding: .5em; border-radius: 5px; }
    .role-assistant { background: #f1f8e9; margin: .75em 0; padding: .5em; border-radius: 5px; }
    .role-tool { background: #fff3e0; margin: .75em 0; padding: .5em; border-radius: 5px; }
    .role-unknown { background: #eceff1; margin: .75em 0; padding: .5em; border-radius: 5px; }
    .conversation-info {
      background-color: #fafafa;
      padding: 0.5em;
      margin-bottom: 0.5em;
      border-left: 4px solid #ccc;
      font-size: 0.9em;
    }
    .metadata-section {
      background: #fefefe;
      border: 1px solid #eee;
      margin-top: 0.75em;
      padding: 0.5em;
      border-radius: 4px;
    }
    hr { border: none; border-top: 1px dashed #ccc; margin: 2em 0; }
    pre { background: #f5f5f5; padding: .5em; border-radius: 5px; overflow: auto; }
    img { max-width: 100%; height: auto; }
    code { background: #f5f5f5; padding: 0.2em 0.4em; border-radius: 3px; }
    em, i { font-style: italic; }
    .message-content { margin-top: 0.5em; }
    .color-key {
      margin-top: 2em;
      padding: 1em;
      border-top: 2px solid #ccc;
    }
    .color-key span {
      display: inline-block;
      margin-right: 1em;
      padding: 0.2em 0.5em;
      border-radius: 3px;
    }
  </style>
  <script>
    MathJax = {
      tex: {
        inlineMath: [["\\\\(","\\\\)"], ["$","$"]],
        displayMath: [["\\\\[","\\\\]"], ["$$","$$"]]
      },
      options: {
        processHtmlClass: "arithmatex"
      },
      startup: {
        typeset: true
      }
    };
  </script>
  <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>
  <script>
    document.addEventListener('DOMContentLoaded', function() {
      // Find and process block math that's between [..] delimiters - multiple patterns
      // Pattern 1: Text surrounded by [ and ] on separate lines
      document.querySelectorAll('p').forEach(function(p) {
        var html = p.innerHTML;
        if (html && html.includes('[\\n') && html.includes('\\n]')) {
          // Create a proper display math element
          var div = document.createElement('div');
          div.className = 'arithmatex';
          
          // Extract the math content between the brackets
          var content = html.substring(html.indexOf('[\\n') + 3, html.lastIndexOf('\\n]')).trim();
          
          // Set the content with proper delimiters
          div.textContent = '\\\\[' + content + '\\\\]';
          
          // Replace the paragraph with our math div
          p.parentNode.replaceChild(div, p);
        } 
        // Pattern 2: Text with inline [ and ] but with <br> in between 
        else if (html && html.includes('[<br>') && html.includes('<br>]')) {
          var div = document.createElement('div');
          div.className = 'arithmatex';
          
          // Extract content between bracket tags
          var content = html.substring(html.indexOf('[<br>') + 5, html.lastIndexOf('<br>]')).trim();
          
          // Set proper math content
          div.textContent = '\\\\[' + content + '\\\\]';
          
          // Replace the paragraph
          p.parentNode.replaceChild(div, p);
        }
      });
      
      // Clean up all math elements for better rendering
      document.querySelectorAll('.arithmatex').forEach(function(el) {
        var text = el.textContent;
        
        // Fix common issues with LaTeX
        // 1. Remove excess backslashes
        text = text.replace(/\\\\\\\\([()])/g, '\\\\$1');
        text = text.replace(/\\\\\\\\([\\[\\]])/g, '\\\\$1');
        
        // 2. Ensure proper wrapping
        if (text.includes('\\\\[') && text.includes('\\\\]')) {
          // Already has display math delimiters
          // Just clean up any starting/ending whitespace
          text = text.replace(/^\\s*(\\\\\\[.*\\\\\\])\\s*$/, '$1');
        } else if (text.includes('\\\\(') && text.includes('\\\\)')) {
          // Already has inline math delimiters
          text = text.replace(/^\\s*(\\\\\\(.*\\\\\\))\\s*$/, '$1');
        } else if (text.includes('[') && text.includes(']')) {
          // Convert brackets to proper display math
          text = text.replace(/^\\s*\\[(.*?)\\]\\s*$/, '\\\\[$1\\\\]');
        }
        
        // Update the element
        el.textContent = text;
      });
      
      // Typeset the math - force processing in case MathJax missed some elements
      if (typeof MathJax !== 'undefined') {
        if (typeof MathJax.typeset === 'function') {
          MathJax.typeset();
        } else if (typeof MathJax.Hub !== 'undefined' && typeof MathJax.Hub.Typeset === 'function') {
          MathJax.Hub.Typeset();
        }
      }
    });
    
    // Additional backup typesetting on load
    window.addEventListener('load', function() {
      if (typeof MathJax !== 'undefined' && typeof MathJax.typeset === 'function') {
        MathJax.typeset();
      }
    });
  </script>
</head>
<body>
  <h1>{{ title }}</h1>
  {% if subtitle %}
  <h3>{{ subtitle }}</h3>
  {% endif %}
  
  <div class="content">
    {% for item in items %}
    <div class="role-{{ item.role }}">
      {% if item.header %}
      <div class="message-header">{{ item.header }}</div>
      {% endif %}
      
      <div class="message-content">{{ item.content | safe }}</div>
      
      {% if item.metadata and include_metadata %}
      <div class="metadata-section">
        <strong>Metadata:</strong>
        <pre>{{ item.metadata | tojson(indent=2) }}</pre>
      </div>
      {% endif %}
    </div>
    {% if not loop.last %}<hr>{% endif %}
    {% endfor %}
  </div>
  
  {% if show_color_key %}
  <div class="color-key">
    <h2>Color Key</h2>
    <span class="role-user">User</span>
    <span class="role-assistant">Assistant</span>
    <span class="role-tool">Tool</span>
    <span class="role-unknown">Unknown</span>
  </div>
  {% endif %}
</body>
</html>
"""
        template_path.write_text(default_template_content, encoding="utf-8")