"""Actual loopback transport and bounded local scientific imports."""
import http.client
import importlib.util
import json
from pathlib import Path
import threading
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('research_serve',ROOT/'serve.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class Quiet(module.Handler):
            def log_message(self,*args):pass
        cls.server=module.ThreadingHTTPServer(('127.0.0.1',0),Quiet)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()

    def request(self,path,body=None,host=None):
        connection=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=20)
        headers={'Host':host or f'127.0.0.1:{self.server.server_port}'}
        if body is not None:headers['Content-Type']='application/octet-stream'
        connection.request('POST' if body is not None else 'GET',path,body,headers)
        response=connection.getresponse();result=response.status,response.read();connection.close();return result

    def test_static_routes_and_loopback_guard(self):
        self.assertEqual(self.request('/web/')[0],200)
        self.assertEqual(self.request('/api/health')[0],200)
        self.assertEqual(self.request('/web/../../serve.py')[0],404)
        self.assertEqual(self.request('/.git/config')[0],404)
        self.assertEqual(self.request('/api/health',host='example.org')[0],403)

    def test_valid_csv_becomes_scoped_tensor_case_and_current_x3d(self):
        raw=b'x,y,z\n0,0,0\n1,0,0\n0,1,0\n0,0,1\n1,2,3\n-1,2,-1\n'
        status,body=self.request('/api/import-cloud',raw)
        self.assertEqual(status,200,body[:300]);result=json.loads(body)
        result['packet']=json.loads(result['packet_text'])
        self.assertEqual(result['packet']['kind'],'tensor')
        self.assertTrue(all(w['pass'] for w in result['packet']['witnesses']))
        body=json.dumps({'case_id':result['packet']['id'],'frame':0,'packet_sha256':result['record']['stored_sha256']}).encode()
        status,xml=self.request('/api/x3d',body);self.assertEqual(status,200)
        status,reimport=self.request('/api/import-x3d',xml)
        self.assertEqual(status,200,reimport[:200]);packet=json.loads(json.loads(reimport)['packet_text'])
        self.assertEqual(packet['kind'],'inspection')
        self.assertIn('not reconstructed',packet['scope'])

    def test_imported_identity_binds_raw_input_and_requested_frame(self):
        a=b'x,y,z\n0,0,0\n1,0,0\n0,1,0\n0,0,1\n1,2,3\n-1,2,-1\n'
        b=b'z,y,x\n0,0,0\n0,0,1\n0,1,0\n1,0,0\n3,2,1\n-1,2,-1\n'
        first=json.loads(self.request('/api/import-cloud',a)[1])
        second=json.loads(self.request('/api/import-cloud',b)[1])
        self.assertNotEqual(first['record']['id'],second['record']['id'])
        for result in (first,second):
            import hashlib
            self.assertEqual(hashlib.sha256(result['packet_text'].encode()).hexdigest(),result['record']['stored_sha256'])
        bad={'case_id':first['record']['id'],'frame':0,'packet_sha256':second['record']['stored_sha256']}
        self.assertEqual(self.request('/api/x3d',json.dumps(bad).encode())[0],409)

    def test_malformed_nonfinite_rank_deficient_and_unsafe_xml_refuse(self):
        for raw in [b'a,b,c\n1,2,3',b'x,y,z\nNaN,0,1\n1,0,0\n0,1,0\n0,0,1',b'x,y,z\n0,0,0\n1,1,1\n2,2,2\n3,3,3']:
            self.assertEqual(self.request('/api/import-cloud',raw)[0],400)
        for raw in [b'<X3D><Scene><Script/></Scene></X3D>',b'<!DOCTYPE X3D [<!ENTITY a SYSTEM "file:///etc/passwd">]><X3D/>']:
            self.assertEqual(self.request('/api/import-x3d',raw)[0],400)

    def test_changed_producer_bytes_refuse_analysis_until_restart(self):
        with mock.patch.object(module,'producer_hashes',return_value={'changed.py':'different'}):
            status,body=self.request('/api/import-cloud',b'x,y,z\n0,0,0')
            self.assertEqual(status,409)
            self.assertIn(b'Restart',body)
        self.assertEqual(self.request('/api/health')[0],200)


if __name__=='__main__':unittest.main()
