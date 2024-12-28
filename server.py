from http.server import BaseHTTPRequestHandler, HTTPServer
import re

import fetchardy

PORT = 10002

pattern = r'^/(\d+)$'

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        match = re.match(pattern, self.path)
        if not match or not match.group(1):
            self.send_response_only(400)
            self.end_headers()
            self.wfile.write(b'Bad request: should be of the form \'/<id>\'')
            return
        num = match.group(1)
        self.send_response_only(200)
        self.end_headers()

        fetchardy.get_game(num)

        self.wfile.write(f'{num}'.encode())

with HTTPServer(("", PORT), Handler) as httpd:
    httpd.serve_forever()
