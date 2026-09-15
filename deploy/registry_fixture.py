"""Offline integration fixture only. This is not a Solid server or login provider."""
from http.server import BaseHTTPRequestHandler, HTTPServer

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/registry/':
            text = '@prefix ldp: <http://www.w3.org/ns/ldp#> . <http://registry:8080/registry/> ldp:contains <http://registry:8080/registry/members> .'
        elif self.path == '/registry/members':
            text = '@prefix foaf: <http://xmlns.com/foaf/0.1/> . <#group> foaf:member <https://pod.example/a/profile/card#me>, <https://pod.example/b/profile/card#me> .'
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', 'text/turtle')
        self.end_headers()
        self.wfile.write(text.encode())

HTTPServer(('0.0.0.0', 8080), Handler).serve_forever()
