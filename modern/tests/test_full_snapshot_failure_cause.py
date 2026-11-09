"""Regression: a tar short read must not hide the actual pinned range failure."""
import io
import json
import pathlib
import tarfile
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import full_snapshot


class BrokenRange(io.RawIOBase):
    def readable(self):
        return True

    def readinto(self, buffer):
        raise OSError('FULL_SNAPSHOT_SHORT_RANGE')


class FakeLz4:
    def __init__(self):
        self.stdin=io.BytesIO()
        self.stdout=io.BytesIO()
        self.killed=False

    def wait(self):
        return 1 if self.killed else 0

    def kill(self):
        self.killed=True


class RestoreFailureCauseTests(unittest.TestCase):
    def test_transport_failure_not_masked_by_downstream_tar_readerror(self):
        spec={'name':'increment','url':'https://snapshot.invalid/increment',
              'etag':'"pinned"','compressedBytes':100,'maxUncompressedBytes':500}
        with tempfile.TemporaryDirectory() as d:
            stage=pathlib.Path(d)/'increment'
            proc=FakeLz4()
            progress=pathlib.Path(d)/'progress.json'
            progress.write_text(json.dumps({'status':'RESTORING','component':'increment',
                                           'compressedBytesRead':60,'componentBytes':100}))
            with patch.object(full_snapshot.subprocess,'Popen',return_value=proc), \
                 patch.object(full_snapshot,'RangeReader',return_value=BrokenRange()), \
                 patch.object(full_snapshot,'extract_resumable',
                              side_effect=tarfile.ReadError('unexpected end of data')):
                with self.assertRaisesRegex(OSError,'FULL_SNAPSHOT_SHORT_RANGE'):
                    full_snapshot.restore_component(spec,stage,progress,0)
            self.assertTrue(proc.killed)
            self.assertFalse((stage/'complete.json').exists())
            state=json.loads(progress.read_text())
            self.assertEqual(state['status'],'FAILED')
            self.assertEqual(state['failureType'],'OSError')
            self.assertEqual(state['failedCondition'],'FULL_SNAPSHOT_SHORT_RANGE')
            self.assertEqual(state['component'],'increment')
            self.assertFalse(state['canonicalStateVerified'])
            self.assertFalse(state['executionAuthorized'])

    def test_archive_readerror_preserved_when_no_upstream_error(self):
        spec={'name':'increment','url':'https://snapshot.invalid/increment',
              'etag':'"pinned"','compressedBytes':100,'maxUncompressedBytes':500}
        with tempfile.TemporaryDirectory() as d:
            stage=pathlib.Path(d)/'increment'
            proc=FakeLz4()
            with patch.object(full_snapshot.subprocess,'Popen',return_value=proc), \
                 patch.object(full_snapshot,'RangeReader',return_value=io.BytesIO()), \
                 patch.object(full_snapshot,'extract_resumable',
                              side_effect=tarfile.ReadError('unexpected end of data')):
                with self.assertRaisesRegex(tarfile.ReadError,'unexpected end of data'):
                    full_snapshot.restore_component(spec,stage,pathlib.Path(d)/'progress.json',0)
            self.assertFalse((stage/'complete.json').exists())


if __name__=='__main__':unittest.main()
