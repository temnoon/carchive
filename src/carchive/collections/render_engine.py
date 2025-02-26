# src/carchive/carchive/collections/render_engine.py
import markdown
from pathlib import Path
from markdown.extensions.codehilite import CodeHiliteExtension
from pymdownx.arithmatex import ArithmatexExtension
from carchive.database.session import get_session
from carchive.database.models import Collection, CollectionItem, Message, Chunk, Conversation

def determine_role(msg_meta):
    if not msg_meta:
        return "unknown"
    return msg_meta.get("author_role", "unknown")

def render_collection_to_html(
    collection_name: str,
    output_file: Path,
    include_conversation_info: bool = False,
    include_message_metadata: bool = False
) -> None:
    """
    Renders the given collection's items to an HTML file with role-based styling and MathJax support.
    Optionally includes conversation info and message metadata.
    """
    with get_session() as session:
        collection = session.query(Collection).filter_by(name=collection_name).first()
        if not collection:
            raise ValueError(f"Collection '{collection_name}' not found.")

        items = session.query(CollectionItem).filter_by(collection_id=collection.id).all()
        if not items:
            raise ValueError(f"Collection '{collection_name}' has no items.")

        rendered_parts = []

        for item in items:
            content_html = ""
            role_class = "role-unknown"
            message_meta = {}
            conversation_info_html = ""
            media_info_html = ""

            if item.message_id is not None:  # Correct the logic check
                msg = session.query(Message).filter_by(id=item.message_id).first()
                if msg is not None and isinstance(msg.content, str):  # Ensure msg and msg.content are valid
                    if include_conversation_info and msg.conversation_id is not None:
                        convo = session.query(Conversation).filter_by(id=msg.conversation_id).first()
                        if convo:
                            conversation_info_html = (
                                f"<div class='conversation-info'>"
                                f"<strong>Conversation Title:</strong> {convo.title or '(Untitled)'} "
                                f"<br><strong>Conversation UUID:</strong> {convo.id}"
                                f"</div>"
                            )
                    message_meta = msg.meta_info or {}
                    content_html = markdown.markdown(
                        msg.content,  # Use the content as-is
                        extensions=["extra", CodeHiliteExtension(), ArithmatexExtension()],
                        extension_configs={
                            "pymdownx.arithmatex": {
                                "generic": False,
                                "tex_inline_wrap": ["\\(", "\\)"],
                                "tex_block_wrap": ["\\[", "\\]"]
                            }
                        },
                    )
                    role = determine_role(message_meta)
                    role_class = f"role-{role}"
            elif item.chunk_id is not None:  # Correct the logic check
                chunk = session.query(Chunk).filter_by(id=item.chunk_id).first()
                if chunk is not None and isinstance(chunk.content, str):  # Ensure chunk and chunk.content are valid
                    content_html = markdown.markdown(
                        chunk.content,  # Use the content as-is
                        extensions=["extra", CodeHiliteExtension(), ArithmatexExtension()],
                        extension_configs={
                            "pymdownx.arithmatex": {
                                "generic": False,
                                "tex_inline_wrap": ["\\(", "\\)"],
                                "tex_block_wrap": ["\\[", "\\]"]
                            }
                        },
                    )
                    role_class = "role-unknown"

            if content_html:
                # Optionally include metadata info
                if include_message_metadata and isinstance(message_meta, dict) and message_meta:
                    possible_media = message_meta.get("media_references", [])
                    if possible_media:
                        media_list = "<ul>" + "".join(f"<li>{m}</li>" for m in possible_media) + "</ul>"
                        media_info_html = (
                            "<div class='metadata-section'>"
                            f"<strong>Media References:</strong>{media_list}"
                            "</div>"
                        )
                    meta_pre = (
                        "<div class='metadata-section'>"
                        f"<strong>Metadata:</strong><pre>{message_meta}</pre>"
                        "</div>"
                    )
                    content_html += media_info_html + meta_pre

                final_html = f"{conversation_info_html}{content_html}"
                rendered_parts.append(f"<div class='{role_class}'>{final_html}</div>")

    if not rendered_parts:
        raise ValueError(f"No renderable content found in collection '{collection_name}'.")

    css_styles = """
<style>
body { font-family: Arial, sans-serif; margin: 1em auto; max-width: 800px; }
.role-user { background: #e0f7fa; margin: .75em 0; padding: .5em; border-radius: 5px; }
.role-assistant { background: #f1f8e9; margin: .75em 0; padding: .5em; border-radius: 5px; }
.role-tool { background: #fff3e0; margin: .75em 0; padding: .5em; border-radius: 5px; }
.role-unknown { background: #eceff1; margin: .75em 0; padding: .5em; border-radius: 5px; }
hr { border: none; border-top: 1px dashed #ccc; margin: 2em 0; }
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
em, i {
  font-style: italic;
  font-size: inherit;
  letter-spacing: inherit;
  word-spacing: inherit;
}
pre { background: #f5f5f5; padding: 0.5em; border-radius: 5px; overflow: auto; }
</style>
"""

    mathjax_script = """
<script>
MathJax = {
  tex: {
    inlineMath: [["\\(","\\)"], ["$","$"]],
    displayMath: [["\\[","\\]"], ["$$","$$"]]
  },
  options: {
    skipHtmlTags: ["script","noscript","style","textarea","pre","code"]
  }
};
</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>
"""

    color_key = """
<div style="margin-top: 2em; padding: 1em; border-top: 2px solid #ccc;">
  <h2>Color Key</h2>
  <span class='role-user' style="padding: 0.2em;"> User </span>
  <span class='role-assistant' style="padding: 0.2em;"> Assistant </span>
  <span class='role-tool' style="padding: 0.2em;"> Tool </span>
  <span class='role-unknown' style="padding: 0.2em;"> Unknown </span>
</div>
"""

    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8"/>
  <title>Collection: {collection_name}</title>
  {css_styles}
  {mathjax_script}
</head>
<body>
  <h1>Collection: {collection_name}</h1>
  <div>
    {"<hr>".join(rendered_parts)}
  </div>
  {color_key}
</body>
</html>
"""
    output_file.write_text(html_content, encoding="utf-8")

def render_conversation_to_html(conversation_id: str, output_file: Path) -> None:
    """
    Render a full conversation as an HTML page with role-based styling and MathJax support.
    Displays raw Markdown before each rendered message for debugging.
    """
    with get_session() as session:
        conversation = session.query(Conversation).filter_by(id=conversation_id).first()
        if not conversation:
            raise ValueError(f"Conversation '{conversation_id}' not found.")

        messages = session.query(Message).filter_by(conversation_id=conversation_id).all()
        if not messages:
            raise ValueError(f"No messages found in conversation '{conversation_id}'.")

        rendered_parts = []
        for msg in messages:
            if not isinstance(msg.content, str) or not msg.content:  # Ensure msg.content is valid
                continue
            raw_md_html = f"<pre>{msg.content}</pre>"
            content_html = markdown.markdown(
                msg.content,  # Use the content as-is
                extensions=["extra", CodeHiliteExtension(), ArithmatexExtension()],
                extension_configs={
                    "pymdownx.arithmatex": {
                        "generic": False,
                        "tex_inline_wrap": ["\\(", "\\)"],
                        "tex_block_wrap": ["\\[", "\\]"]
                    }
                },
            )
            role = determine_role(msg.meta_info)
            role_class = f"role-{role}"
            combined_html = f"{raw_md_html}<hr>{content_html}"
            rendered_parts.append(f"<div class='{role_class}'>{combined_html}</div>")

    if not rendered_parts:
        raise ValueError(f"No renderable content found in conversation '{conversation_id}'.")

    css_styles = """
<style>
body { font-family: Arial, sans-serif; margin: 1em auto; max-width: 800px; }
.role-user { background: #e0f7fa; margin: .75em 0; padding: .5em; border-radius: 5px; }
.role-assistant { background: #f1f8e9; margin: .75em 0; padding: .5em; border-radius: 5px; }
.role-tool { background: #fff3e0; margin: .75em 0; padding: .5em; border-radius: 5px; }
.role-unknown { background: #eceff1; margin: .75em 0; padding: .5em; border-radius: 5px; }
hr { border: none; border-top: 1px dashed #ccc; margin: 2em 0; }
pre { background: #f5f5f5; padding: 0.5em; border-radius: 5px; overflow: auto; }
em, i {
  font-style: italic;
  font-size: inherit;
  letter-spacing: inherit;
  word-spacing: inherit;
}
</style>
"""
    mathjax_script = """
<script>
MathJax = {
  tex: {
    inlineMath: [["\\(","\\)"], ["$","$"]],
    displayMath: [["\\[","\\]"], ["$$","$$"]]
  },
  options: {
    skipHtmlTags: ["script","noscript","style","textarea","pre","code"]
  }
};
</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>
"""
    color_key = """
<div style="margin-top: 2em; padding: 1em; border-top: 2px solid #ccc;">
  <h2>Color Key</h2>
  <span class='role-user' style="padding: 0.2em;"> User </span>
  <span class='role-assistant' style="padding: 0.2em;"> Assistant </span>
  <span class='role-tool' style="padding: 0.2em;"> Tool </span>
  <span class='role-unknown' style="padding: 0.2em;"> Unknown </span>
</div>
"""

    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8"/>
  <title>Conversation: {conversation_id}</title>
  {css_styles}
  {mathjax_script}
</head>
<body>
  <h1>Conversation: {conversation_id}</h1>
  <div>
    {"<hr>".join(rendered_parts)}
  </div>
  {color_key}
</body>
</html>
"""
    output_file.write_text(html_content, encoding="utf-8")
