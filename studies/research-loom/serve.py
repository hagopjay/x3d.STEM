#!/usr/bin/env python3
"""Loopback server: saved cases plus bounded CSV/X3D inspection, never supplied code."""
from __future__ import annotations

import argparse
import csv
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import sys
import threading
from urllib.parse import unquote, urlsplit
import webbrowser

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from stemloom.exchange import from_x3d, to_x3d

MIME={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8',
      '.css':'text/css; charset=utf-8','.json':'application/json; charset=utf-8',
      '.md':'text/plain; charset=utf-8','.x3d':'model/x3d+xml','.png':'image/png',
      '.jpg':'image/jpeg','.svg':'image/svg+xml','.woff2':'font/woff2','.blend':'application/octet-stream',
      '.csv':'text/csv; charset=utf-8','.vtp':'application/xml','.vti':'application/xml'}
_IMPORTS={}
_LOCK=threading.Lock()
_WORKERS=threading.BoundedSemaphore(2)


def producer_hashes():
    paths=list((ROOT/'stemloom').glob('*.py'))+[ROOT/'tools'/'build.py']
    result={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
    result['../../lib/stemkit/core.py']=hashlib.sha256((ROOT.parents[1]/'lib/stemkit/core.py').read_bytes()).hexdigest()
    return result


_PRODUCERS=producer_hashes()


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')


class Handler(BaseHTTPRequestHandler):
    def _local(self):
        accepted={f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
        return self.headers.get('Host') in accepted and (not self.headers.get('Origin') or urlsplit(self.headers['Origin']).netloc in accepted)

    def send(self,status,raw,mime='application/json; charset=utf-8'):
        self.send_response(status);self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(len(raw)));self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw)

    def respond(self,status,obj):
        self.send(status,canonical(obj))

    def do_GET(self):
        if not self._local():return self.respond(403,{'error':'Loopback origin required.'})
        path=unquote(urlsplit(self.path).path)
        if path=='/api/health':return self.respond(200,{'service':'research-loom','scope':'Bounded local data imports; no supplied code executes.'})
        if path=='/':
            self.send_response(307);self.send_header('Location','/web/');self.send_header('Content-Length','0');self.end_headers();return
        parts=path.lstrip('/').split('/')
        if not parts or parts[0] not in ('web','docs','exports','evidence','renders'):
            return self.respond(404,{'error':'File not found.'})
        candidate=(ROOT/path.lstrip('/')).resolve()
        if path.endswith('/'):candidate=candidate/'index.html'
        if not candidate.is_relative_to((ROOT/parts[0]).resolve()) or not candidate.is_file():
            return self.respond(404,{'error':'File not found.'})
        self.send(200,candidate.read_bytes(),MIME.get(candidate.suffix,'application/octet-stream'))

    def do_POST(self):
        if not self._local():return self.respond(403,{'error':'Loopback origin required.'})
        if self.path not in ('/api/import-cloud','/api/import-x3d','/api/x3d'):
            return self.respond(404,{'error':'Unknown endpoint.'})
        if producer_hashes()!=_PRODUCERS:
            return self.respond(409,{'error':'Scientific producer source changed. Restart the local server.'})
        try:
            from stemloom.core import Rejected, source_hashes, validate_case
        except ImportError:
            return self.respond(503,{'error':'Install requirements.txt to enable scientific imports. The included browser case bank remains available without those packages.'})
        try:
            size=int(self.headers.get('Content-Length','-1'))
            maximum=2*1024*1024 if self.path=='/api/import-cloud' else 16*1024*1024
            if not 1<=size<=maximum or self.headers.get('Transfer-Encoding'):
                self.close_connection=True;return self.respond(413,{'error':'Import exceeds its declared byte budget.'})
            if not _WORKERS.acquire(blocking=False):return self.respond(429,{'error':'Two imports are already being processed.'})
            try:
                raw=self.rfile.read(size)
                if self.path=='/api/x3d':
                    request=json.loads(raw)
                    if not isinstance(request,dict) or set(request)!={'case_id','frame','packet_sha256'} or not isinstance(request['case_id'],str):raise ValueError('Expected a stored case identity, packet digest and frame.')
                    with _LOCK:packet=_IMPORTS.get(request['case_id'])
                    if packet is None:raise ValueError('Unknown imported case.')
                    if hashlib.sha256(canonical(packet)).hexdigest()!=request['packet_sha256']:
                        return self.respond(409,{'error':'The stored imported case changed. Reopen the current packet.'})
                    return self.send(200,to_x3d(packet,request['frame']).encode(),'model/x3d+xml')
                if self.path=='/api/import-cloud':
                    from stemloom.tensor import build_from_points
                    text=raw.decode('utf-8-sig');reader=csv.DictReader(io.StringIO(text))
                    if not reader.fieldnames or not {'x','y','z'}.issubset(reader.fieldnames):raise ValueError('CSV needs named x,y,z numeric columns.')
                    points=[]
                    for row in reader:
                        if len(points)>=5000:raise ValueError('The cloud exceeds 5,000 observations.')
                        points.append([float(row[k]) for k in ('x','y','z')])
                    packet=build_from_points(points,label='Imported research cloud')
                    packet['source_sha256']=_PRODUCERS
                    packet['input_sha256']=hashlib.sha256(raw).hexdigest()
                    packet['id']+='-'+packet['input_sha256'][:12]
                    packet['schema']='stemloom.case/1'
                    validate_case(packet)
                    message='Cloud analyzed. Coverage remains a model assumption; coordinate units are supplied by you.'
                else:
                    frame=from_x3d(raw.decode('utf-8'));metadata=frame.pop('metadata')
                    frame['metrics']=[{'id':'geometry','label':'Geometric parts','value':sum(len(frame[k]) for k in ('meshes','lines','points')),'unit':'records','note':'Actual geometry decoded from the selected XML.'}]
                    packet={'schema':'stemloom.case/1','id':'inspection-'+hashlib.sha256(raw).hexdigest()[:12],
                            'kind':'inspection','title':'Imported X3D geometry inspection',
                            'question':'What survived the transfer?',
                            'description':'This scene was reconstructed from actual geometry nodes, not cached source positions.',
                            'scope':'Geometry inspection only. Original scientific claims, arrays, and witnesses are not reconstructed or re-certified.',
                            'axes':metadata.get('axes','Coordinates retain the imported world convention.'),
                            'units':metadata.get('units',{'length':'undeclared'}), 'frames':[frame],
                            'insights':['Compare coordinates and topology before interpreting a returned image.','Preserved metadata is a provenance claim, not an independent recomputation of the original science.'],
                            'sources':[{'title':'Research Loom exchange contract','url':'https://www.web3d.org/x3d/what-x3d/','note':'This inspector accepts the explicitly documented static subset only.'}],
                            'witnesses':[{'id':'static_subset_readback','pass':True,'observed':0.,'limit':0.,'rule':'at most','note':'Structural parsing and finite/bounded geometry validation passed. Scientific witnesses were not recomputed.'}],
                            'source_sha256':_PRODUCERS,'declared_provenance':metadata}
                    message='Geometry inspected. Scientific evidence was not recomputed.'
                if producer_hashes()!=_PRODUCERS:
                    return self.respond(409,{'error':'Scientific producer source changed during import. Restart the local server.'})
                with _LOCK:
                    if len(_IMPORTS)>=8:_IMPORTS.pop(next(iter(_IMPORTS)))
                    _IMPORTS[packet['id']]=packet
                packet_bytes=canonical(packet)
                record={'id':packet['id'],'kind':packet['kind'],'title':packet['title'],'frames':len(packet['frames']),
                        'eligible':True,'exports':{},'export_frame':0,'mode':'inspection' if self.path.endswith('x3d') else 'analysis'}
                record['stored_sha256']=hashlib.sha256(packet_bytes).hexdigest()
                self.respond(200,{'packet_text':packet_bytes.decode('utf-8'),'record':record,'message':message})
            finally:_WORKERS.release()
        except ImportError:
            self.respond(503,{'error':'Install requirements.txt to enable this scientific analysis.'})
        except (Rejected,ValueError,TypeError,KeyError,UnicodeError,OverflowError,RecursionError) as error:
            self.respond(400,{'error':str(error)[:400]})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--port',type=int,default=8860);p.add_argument('--open',action='store_true');args=p.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    url=f'http://127.0.0.1:{args.port}/web/'
    print('Research Loom:',url,flush=True)
    if args.open:webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()


if __name__=='__main__':main()
