import http.server
import socketserver
import threading
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def static_pages():
    """Serve tests/flow/static_pages/ on a free port."""
    pages_dir = Path(__file__).parent / "static_pages"
    pages_dir.mkdir(exist_ok=True)
    (pages_dir / "search.html").write_text(
        "<!doctype html><html><body>"
        "<input id='q' />"
        "<button id='go' onclick=\"document.getElementById('out').innerText='hello '+document.getElementById('q').value\">go</button>"
        "<div id='out'></div>"
        "</body></html>"
    )

    class _H(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(pages_dir), **kw)

        def log_message(self, *_):
            pass

    httpd = socketserver.TCPServer(("127.0.0.1", 0), _H)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
