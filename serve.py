#!/usr/bin/env python3
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import os
from urllib.parse import unquote

class RangeRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        super().end_headers()

    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            for index in ('index.html', 'index.htm'):
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)
        ctype = self.guess_type(path)
        try:
            f = open(path, 'rb')
        except OSError:
            self.send_error(404, 'File not found')
            return None
        fs = os.fstat(f.fileno())
        size = fs.st_size
        range_header = self.headers.get('Range')
        if range_header and range_header.startswith('bytes='):
            start_s, _, end_s = range_header.replace('bytes=', '', 1).partition('-')
            try:
                start = int(start_s) if start_s else 0
                end = int(end_s) if end_s else size - 1
                end = min(end, size - 1)
                if start > end or start >= size:
                    self.send_error(416, 'Requested Range Not Satisfiable')
                    f.close()
                    return None
                self.send_response(206)
                self.send_header('Content-type', ctype)
                self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
                self.send_header('Content-Length', str(end - start + 1))
                self.send_header('Last-Modified', self.date_time_string(fs.st_mtime))
                self.end_headers()
                f.seek(start)
                self.range = (start, end)
                return f
            except ValueError:
                pass
        self.send_response(200)
        self.send_header('Content-type', ctype)
        self.send_header('Content-Length', str(size))
        self.send_header('Last-Modified', self.date_time_string(fs.st_mtime))
        self.end_headers()
        self.range = None
        return f

    def copyfile(self, source, outputfile):
        r = getattr(self, 'range', None)
        if not r:
            return super().copyfile(source, outputfile)
        start, end = r
        remaining = end - start + 1
        while remaining > 0:
            chunk = source.read(min(64 * 1024, remaining))
            if not chunk:
                break
            outputfile.write(chunk)
            remaining -= len(chunk)

if __name__ == '__main__':
    os.chdir(os.path.dirname(__file__))
    server = ThreadingHTTPServer(('127.0.0.1', 8767), RangeRequestHandler)
    print('Serving http://127.0.0.1:8767/ with Range support')
    server.serve_forever()
