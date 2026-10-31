from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
import json, os, secrets, threading, sqlite3
from voodoosql import Catalog, QueryPack, FIXTURE, seed, save_catalog

HOST="127.0.0.1"; PORT=8332; TOKEN=secrets.token_urlsafe(24)
seed()
PACK=QueryPack()

class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(5)
    def log_message(self, fmt, *args): pass
    def _send(self,status,body,kind="application/json; charset=utf-8"):
        data=body if isinstance(body,bytes) else body.encode()
        self.send_response(status); self.send_header("Content-Type",kind); self.send_header("Content-Length",str(len(data))); self.send_header("X-Content-Type-Options","nosniff"); self.send_header("Content-Security-Policy","default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'"); self.end_headers(); self.wfile.write(data)
    def _json(self,obj,status=200): self._send(status,json.dumps(obj,ensure_ascii=False))
    def do_GET(self):
        if self.headers.get("Host") not in (f"127.0.0.1:{PORT}",f"localhost:{PORT}"):
            return self._json({"error":"Invalid host"},403)
        route=urlparse(self.path).path
        if route=="/":
            page=open(os.path.join(os.path.dirname(__file__),"static","index.html"),encoding="utf-8").read().replace("__TOKEN__",TOKEN)
            return self._send(200,page,"text/html; charset=utf-8")
        if route=="/app.css": return self._send(200,open(os.path.join(os.path.dirname(__file__),"static","app.css"),"rb").read(),"text/css; charset=utf-8")
        if route=="/app-extra.css": return self._send(200,open(os.path.join(os.path.dirname(__file__),"static","app-extra.css"),"rb").read(),"text/css; charset=utf-8")
        if route=="/app.js": return self._send(200,open(os.path.join(os.path.dirname(__file__),"static","app.js"),"rb").read(),"text/javascript; charset=utf-8")
        if route=="/eval-extra.js": return self._send(200,open(os.path.join(os.path.dirname(__file__),"static","eval-extra.js"),"rb").read(),"text/javascript; charset=utf-8")
        if route=="/api/catalog":
            c=Catalog.from_sqlite(); save_catalog(c); return self._json(c.to_dict())
        if route=="/api/graph":
            c=Catalog.from_sqlite(); save_catalog(c); return self._json(c.to_graph())
        if route=="/api/recipes": return self._json({"recipes":__import__('voodoosql').RECIPES,"fingerprint":PACK.fingerprint})
        return self._json({"error":"Not found"},404)
    def do_POST(self):
        if self.headers.get("Host") not in (f"127.0.0.1:{PORT}",f"localhost:{PORT}") or self.headers.get("Origin") not in (f"http://127.0.0.1:{PORT}",f"http://localhost:{PORT}"):
            return self._json({"error":"Invalid request origin"},403)
        if self.headers.get("X-Request-Token")!=TOKEN: return self._json({"error":"Request token required"},403)
        try: n=int(self.headers.get("Content-Length","-1"))
        except ValueError: n=-1
        if n<0 or n>16000: return self._json({"error":"Payload size must be under 16 KB"},413)
        try: body=json.loads(self.rfile.read(n))
        except Exception: return self._json({"error":"Invalid JSON"},400)
        if not isinstance(body,dict): return self._json({"error":"JSON object required"},400)
        route=urlparse(self.path).path
        if route=="/api/retrieve":
            if not isinstance(body.get("question"),str) or len(body["question"])>1000: return self._json({"error":"Question must be text under 1,000 characters"},400)
            return self._json(PACK.retrieve(body["question"]))
        if route=="/api/execute":
            try: return self._json(PACK.execute(body.get("recipe_id"),body.get("params")))
            except (ValueError,KeyError,TypeError,sqlite3.Error) as e: return self._json({"error":str(e)},400)
        return self._json({"error":"Not found"},404)

if __name__=="__main__":
    print(f"voodooSQL listening at http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
