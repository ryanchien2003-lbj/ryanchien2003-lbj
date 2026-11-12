"""Local practice form. Submitted bodies are discarded."""
from http.server import BaseHTTPRequestHandler, HTTPServer

FORM = """<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>Practice application</title>
<h1>Practice application for Example Company</h1>
<p>This form runs locally and discards the submission.</p>
<form id="application" method="post" enctype="multipart/form-data">
<p><label>Name <input required id="name" name="name"></label></p>
<p><label>Email <input required type="email" id="email" name="email"></label></p>
<p><label>Resume <input required type="file" id="resume" name="resume"></label></p>
<p><label>Cover letter <textarea required id="letter" name="letter" rows="12" cols="70"></textarea></label></p>
<p><label>Availability <select required id="availability" name="availability">
<option value="">Select</option><option value="summer">Summer</option></select></label></p>
<button type="submit">Submit practice application</button>
</form>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def send_html(self, html):
        payload = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == "/apply":
            self.send_html(FORM)
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path != "/apply":
            self.send_error(404)
            return
        size = int(self.headers.get("Content-Length", "0"))
        if not 0 < size <= 1_000_000:
            self.send_error(400)
            return
        self.rfile.read(size)
        self.send_html('<!doctype html><html lang="en"><title>Received</title>'
                       '<h1 id="application-received">Practice application received</h1></html>')


if __name__ == "__main__":
    print("Practice form: http://127.0.0.1:8765/apply", flush=True)
    with HTTPServer(("127.0.0.1", 8765), Handler) as server:
        server.serve_forever()
