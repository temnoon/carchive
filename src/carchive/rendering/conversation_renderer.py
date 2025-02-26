# carchive2/rendering/conversation_renderer.py
import json
from pathlib import Path
from carchive.database.session import get_session
from carchive.database.models import Conversation, Message

def render_conversation_html(conversation_id: str, output_file: str, return_as_string=False):
    with get_session() as session:
        convo = session.query(Conversation).filter_by(id=conversation_id).first()
        if not convo:
            raise ValueError(f"Conversation {conversation_id} not found.")

        messages = convo.messages  # or sorted by created_at, etc.
        # Build your HTML
        meta_info_pretty = json.dumps(convo.meta_info or {}, indent=2)

        # Example toggles for meta info and raw vs. rendered markdown:
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="UTF-8"/>
        <style>
        body {{ font-family: sans-serif; max-width: 800px; margin: 1em auto; }}
        .role-user {{ background: #e0f7fa; padding: .5em; margin: .75em 0; border-radius: 5px; }}
        .role-assistant {{ background: #f1f8e9; padding: .5em; margin: .75em 0; border-radius: 5px; }}
        .meta-info-block {{ display: none; white-space: pre-wrap; background: #f9f9f9; border: 1px solid #ddd; padding: 1em; margin-top: 1em; }}
        </style>
        <script>
        function toggleMeta() {{
          let blocks = document.querySelectorAll('.meta-info-block');
          blocks.forEach(b => {{
            if (b.style.display === 'none') b.style.display = 'block';
            else b.style.display = 'none';
          }});
        }}
        </script>
        </head>
        <body>
          <h1>{convo.title or "Untitled Conversation"}</h1>
          <p>Created: {convo.created_at}</p>
          <button onclick="toggleMeta()">Toggle Meta Info</button>
          <div class="meta-info-block">{meta_info_pretty}</div>
          <hr>
        """

        for msg in messages:
            role = msg.meta_info.get("author_role", "unknown")
            content_html = msg.content  # TODO: process or convert markdown
            msg_meta_pretty = json.dumps(msg.meta_info or {}, indent=2)
            html_content += f"""
            <div class="role-{role}">
              <h4>{role}</h4>
              <div>{content_html}</div>
              <button onclick="this.nextElementSibling.style.display =
                (this.nextElementSibling.style.display === 'none' ? 'block' : 'none')">
                Toggle Message Meta
              </button>
              <pre class="meta-info-block" style="display:none;">{msg_meta_pretty}</pre>
            </div>
            """

        html_content += "</body></html>"

        if return_as_string:
            return html_content
        else:
            Path(output_file).write_text(html_content, encoding="utf-8")
