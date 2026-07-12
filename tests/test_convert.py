from doctoskill.convert import convert_page


def test_convert_extracts_content_title_and_code():
    html = """<html><head><title>Site title</title></head><body>
    <header>Header junk</header><nav>Nav junk</nav><main><h1>Page Title</h1>
    <p>Real content.</p><pre><code class='language-python'>print("hi")</code></pre></main>
    <footer>Footer junk</footer></body></html>"""
    title, markdown = convert_page(html)
    assert title == "Page Title"
    assert "Real content." in markdown and 'print("hi")' in markdown
    assert "junk" not in markdown


def test_convert_respects_selector_and_title_fallback():
    title, markdown = convert_page(
        "<html><head><title>T</title></head><body><nav>N</nav><div class='article'>Only me</div></body></html>",
        ".article",
    )
    assert title == "T"
    assert markdown == "Only me"


def test_convert_strips_docfx_table_of_contents_toggle():
    _title, markdown = convert_page(
        "<html><body><main><h1>Entities</h1>"
        "<a href='#sidetoggle'>Show / Hide Table of Contents</a>"
        "<p>Useful content.</p></main></body></html>"
    )
    assert "Show / Hide Table of Contents" not in markdown
    assert "Useful content." in markdown


def test_convert_chooses_h1_article_over_unrelated_content_class():
    html = """<html><body>
      <div class='content'><a href='/'>Global menu</a></div>
      <div class='content-block'><div class='content'><div class='section'>
        <h1>UI Toolkit</h1><p>VisualElement, UXML, and USS documentation.</p>
      </div></div></div>
    </body></html>"""
    title, markdown = convert_page(html)
    assert title == "UI Toolkit"
    assert "VisualElement, UXML, and USS" in markdown
    assert "Global menu" not in markdown
