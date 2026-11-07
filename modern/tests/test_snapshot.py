import io
import pathlib
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import snapshot


class SnapshotTests(unittest.TestCase):
    def test_parallel_ranges_reassemble_exact_bytes_and_reject_changed_object(self):
        payload=bytes(range(251))*13
        spec={'component':'bor','url':'https://snapshot.invalid/state','etag':'"fixed"',
              'compressedBytes':len(payload)}
        calls=[]
        def response(request,timeout):
            start,end=map(int,request.get_header('Range')[6:].split('-'))
            calls.append((start,end))
            stream=io.BytesIO(payload[start:end+1])
            stream.status=206;stream.url=spec['url']
            stream.headers={'ETag':'"fixed"','Content-Range':f'bytes {start}-{end}/{len(payload)}',
                            'Content-Length':str(end-start+1)}
            return stream
        with tempfile.TemporaryDirectory() as d,patch.object(snapshot.urllib.request,'urlopen',response):
            path=pathlib.Path(d)/'state.part'
            snapshot.parallel_download(spec,path,chunk_bytes=256,workers=3)
            self.assertEqual(path.read_bytes(),payload)
            self.assertEqual(len(calls),13)
            # Completed immutable chunks are reused after interruption.
            calls.clear();snapshot.parallel_download(spec,path,chunk_bytes=256,workers=3)
            self.assertEqual(calls,[])
        spec['etag']='"changed"'
        with tempfile.TemporaryDirectory() as d,patch.object(snapshot.urllib.request,'urlopen',response),self.assertRaises(ValueError):
            snapshot.parallel_download(spec,pathlib.Path(d)/'state.part',chunk_bytes=256,workers=3)
    def archive(self, entries):
        stream=io.BytesIO()
        with tarfile.open(fileobj=stream,mode='w') as archive:
            for name,kind in entries:
                member=tarfile.TarInfo(name)
                member.type=kind
                member.size=2 if kind==tarfile.REGTYPE else 0
                member.linkname='/etc/passwd' if kind==tarfile.SYMTYPE else ''
                archive.addfile(member,io.BytesIO(b'ok') if member.size else None)
        stream.seek(0)
        return stream

    def test_only_expected_database_is_extracted(self):
        with tempfile.TemporaryDirectory() as d:
            snapshot.extract_tar(self.archive([('bor/chaindata/CURRENT',tarfile.REGTYPE)]),pathlib.Path(d),'bor/chaindata',100)
            self.assertEqual((pathlib.Path(d)/'bor/chaindata/CURRENT').read_bytes(),b'ok')

    def test_provider_validator_state_is_ignored_not_imported(self):
        with tempfile.TemporaryDirectory() as d:
            snapshot.extract_tar(self.archive([('data/CURRENT',tarfile.REGTYPE),
                ('priv_validator_state.json',tarfile.REGTYPE)]),pathlib.Path(d),'data',100)
            self.assertTrue((pathlib.Path(d)/'data/CURRENT').exists())
            self.assertFalse((pathlib.Path(d)/'priv_validator_state.json').exists())

    def test_paths_links_and_foreign_roots_rejected(self):
        for name,kind in [('../escape',tarfile.REGTYPE),('/absolute',tarfile.REGTYPE),
                          ('data/../../escape',tarfile.REGTYPE),('config/node_key.json',tarfile.REGTYPE),
                          ('data/link',tarfile.SYMTYPE),('data/device',tarfile.CHRTYPE)]:
            with self.subTest(name=name),tempfile.TemporaryDirectory() as d,self.assertRaises(ValueError):
                snapshot.extract_tar(self.archive([(name,kind)]),pathlib.Path(d),'data',100)

    def test_expansion_limit_and_existing_file_protected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                snapshot.extract_tar(self.archive([('data/file',tarfile.REGTYPE)]),pathlib.Path(d),'data',1)
            target=pathlib.Path(d)/'data/file';target.parent.mkdir(exist_ok=True);target.write_bytes(b'keep')
            with self.assertRaises(FileExistsError):
                snapshot.extract_tar(self.archive([('data/file',tarfile.REGTYPE)]),pathlib.Path(d),'data',10)
            self.assertEqual(target.read_bytes(),b'keep')

    def test_object_identity_must_match_on_resume(self):
        spec={'etag':'"expected"','compressedBytes':100}
        snapshot.validate_headers({'ETag':'"expected"','Content-Range':'bytes 20-99/100'},206,20,spec)
        for headers,status in [({'ETag':'"different"','Content-Range':'bytes 20-99/100'},206),
                               ({'ETag':'"expected"','Content-Range':'bytes 21-99/100'},206),
                               ({'ETag':'"expected"','Content-Length':'100'},200)]:
            with self.assertRaises(ValueError):snapshot.validate_headers(headers,status,20,spec)
