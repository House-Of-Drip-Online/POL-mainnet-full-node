import io
import pathlib
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import full_snapshot


class FullSnapshotTests(unittest.TestCase):
    def test_stream_is_ordered_bounded_and_retries_transport_errors(self):
        data = bytes(range(251)) * 23
        spec = {'url': 'https://snapshot.invalid/full', 'etag': '"immutable"',
                'compressedBytes': len(data)}
        attempts = {}
        def fetch(request, timeout):
            start, end = map(int, request.get_header('Range')[6:].split('-'))
            attempts[start] = attempts.get(start, 0) + 1
            if start == 256 and attempts[start] == 1:
                raise OSError('transient connection failure')
            stream = io.BytesIO(data[start:end + 1])
            stream.status = 206
            stream.url = spec['url']
            stream.headers = {'ETag': spec['etag'], 'Content-Length': str(end-start+1),
                              'Content-Range': f'bytes {start}-{end}/{len(data)}'}
            return stream
        with patch.object(full_snapshot.urllib.request, 'urlopen', fetch), \
             patch.object(full_snapshot.time, 'sleep'):
            with full_snapshot.RangeReader(spec, workers=3, chunk_bytes=256) as source:
                self.assertEqual(source.read(), data)
                self.assertLessEqual(source.peak_pending, 3)
            self.assertEqual(attempts[256], 2)

    def test_changed_object_or_short_range_never_becomes_valid_stream(self):
        for changed, short in [(True, False), (False, True)]:
            spec = {'url': 'https://snapshot.invalid/full', 'etag': '"fixed"', 'compressedBytes': 4}
            def fetch(request, timeout):
                stream = io.BytesIO(b'abc' if short else b'abcd')
                stream.status = 206; stream.url = spec['url']
                stream.headers = {'ETag': '"changed"' if changed else spec['etag'],
                                  'Content-Length': '4', 'Content-Range': 'bytes 0-3/4'}
                return stream
            with patch.object(full_snapshot.urllib.request, 'urlopen', fetch), \
                 patch.object(full_snapshot.time, 'sleep'), self.assertRaises((ValueError, OSError)):
                with full_snapshot.RangeReader(spec, workers=1, chunk_bytes=4) as source:
                    source.read()

    def archive(self, name='bor/chaindata/file', content=b'content', kind=tarfile.REGTYPE):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w') as archive:
            member = tarfile.TarInfo(name); member.type = kind
            member.size = len(content) if kind == tarfile.REGTYPE else 0
            archive.addfile(member, io.BytesIO(content) if member.size else None)
        stream.seek(0)
        return stream

    def test_restart_accepts_identical_files_and_rejects_changed_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            full_snapshot.extract_resumable(self.archive(), root, 100)
            full_snapshot.extract_resumable(self.archive(), root, 100)
            with self.assertRaisesRegex(ValueError, 'EXISTING_FILE_DIFFERS'):
                full_snapshot.extract_resumable(self.archive(content=b'changed'), root, 100)
            self.assertEqual((root/'bor/chaindata/file').read_bytes(), b'content')

    def test_extraction_rejects_links_escape_and_expansion(self):
        for name, kind, maximum in [('../escape', tarfile.REGTYPE, 100),
                                    ('/absolute', tarfile.REGTYPE, 100),
                                    ('bor/chaindata/link', tarfile.SYMTYPE, 100),
                                    ('bor/chaindata/file', tarfile.REGTYPE, 1)]:
            with tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
                full_snapshot.extract_resumable(self.archive(name, kind=kind), pathlib.Path(directory), maximum)

    def test_merge_never_overwrites_conflicting_component(self):
        with tempfile.TemporaryDirectory() as directory:
            source = pathlib.Path(directory)/'source'; target = pathlib.Path(directory)/'target'
            source.mkdir(); target.mkdir()
            (source/'file').write_bytes(b'increment'); (target/'file').write_bytes(b'base')
            with self.assertRaisesRegex(ValueError, 'COMPONENT_OVERLAP'):
                full_snapshot.merge_database(source, target)
            self.assertEqual((target/'file').read_bytes(), b'base')
            self.assertEqual((source/'file').read_bytes(), b'increment')


if __name__ == '__main__': unittest.main()
