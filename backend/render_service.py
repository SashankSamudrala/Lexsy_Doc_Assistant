# backend/render_service.py
import re
import mammoth

PLACEHOLDER_RE = re.compile(r"\[[^\[\]\n\r]+?\]")

def docx_to_html(docx_path: str) -> str:
    with open(docx_path, "rb") as f:
        result = mammoth.convert_to_html(f, style_map=_style_map())
    html = result.value

    # Highlight placeholders and add a data-key for click sync
    def repl(m):
        raw = m.group(0)
        data_key = raw  # keep exact; frontend uses it to map to field
        return f"<span class='ph' data-key='{_escape_attr(data_key)}'>{raw}</span>"

    html = PLACEHOLDER_RE.sub(repl, html)
    wrapped = f"""
    <div class="docx-page">
      {html}
    </div>
    """
    return wrapped

def _style_map():
    return """
    p[style-name='Normal'] => p:fresh
    table => table.table
    """

def _escape_attr(s: str) -> str:
    return s.replace('"', '&quot;').replace("'", "&#39;")
