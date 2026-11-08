"""Fail-closed transport range and Pebble/ancient structural pre-promotion gates."""
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import full_snapshot as snap


def good_lock():
    return {"chainId":137,"components":[
        {"name":"base","firstBlock":0,"lastBlock":100,"compressedBytes":1000,
         "maxUncompressedBytes":1200,"url":"https://snapshots.invalid/base","etag":"\"base\""},
        {"name":"increment","firstBlock":101,"lastBlock":200,"compressedBytes":1000,
         "maxUncompressedBytes":1200,"url":"https://snapshots.invalid/part","etag":"\"part\""}
    ]}


def make_db(root):
    root.mkdir(parents=True)
    (root/"CURRENT").write_text("MANIFEST-000001\n")
    (root/"MANIFEST-000001").write_bytes(b"manifest")
    ancient=root/"ancient"/"chain"
    ancient.mkdir(parents=True)
    for kind in ("bodies","headers","receipts"):
        for n in range(3):
            (ancient/(kind+f".{n:04d}.cdat")).write_bytes(b"segment")
    return root


class SnapshotPrepromotionTests(unittest.TestCase):
    def test_valid_contiguous_transport_lock(self):
        d=snap.validate_snapshot_plan(good_lock())
        self.assertEqual((d["rangeStart"],d["rangeEnd"],d["components"]),(0,200,2))

    def test_block_gap_and_overlap_are_hard_failures(self):
        for start in (99,102):
            lock=good_lock()
            lock["components"][1]["firstBlock"]=start
            with self.subTest(start=start),self.assertRaisesRegex(ValueError,"GAP_OR_OVERLAP"):
                snap.validate_snapshot_plan(lock)

    def test_chain_and_transport_identity_fail_closed(self):
        for kind in ("chain","tls","etag","duplicate","size"):
            lock=good_lock()
            if kind=="chain":lock["chainId"]=1
            if kind=="tls":lock["components"][0]["url"]="http://snapshots.invalid/base"
            if kind=="etag":lock["components"][0]["etag"]=""
            if kind=="duplicate":lock["components"][1]["name"]="base"
            if kind=="size":lock["components"][0]["maxUncompressedBytes"]=0
            with self.subTest(kind=kind),self.assertRaises(ValueError):
                snap.validate_snapshot_plan(lock)

    def test_valid_manifest_and_contiguous_ancient_segments(self):
        with tempfile.TemporaryDirectory() as d:
            db=make_db(pathlib.Path(d)/"chaindata")
            proof=snap.verify_ancient_layout(db)
            self.assertEqual(proof["manifest"],"MANIFEST-000001")
            self.assertEqual(proof["ancient_segments"]["bodies"]["count"],3)
            self.assertEqual(proof["authority"],"STRUCTURAL_ONLY_NATIVE_CHAIN_PROOF_REQUIRED")

    def test_manifest_missing_or_unsafe_pointer_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            db=make_db(pathlib.Path(d)/"chaindata")
            (db/"CURRENT").write_text("../MANIFEST-000001\n")
            with self.assertRaisesRegex(ValueError,"MANIFEST_POINTER_INVALID"):
                snap.verify_ancient_layout(db)
            (db/"CURRENT").write_text("MANIFEST-000001\n")
            (db/"MANIFEST-000001").unlink()
            with self.assertRaisesRegex(ValueError,"MANIFEST_MISSING"):
                snap.verify_ancient_layout(db)

    def test_ancient_gap_and_missing_family_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            db=make_db(pathlib.Path(d)/"chaindata")
            chain=db/"ancient"/"chain"
            (chain/"bodies.0001.cdat").unlink()
            with self.assertRaisesRegex(ValueError,"SEGMENT_GAP"):
                snap.verify_ancient_layout(db)
            (chain/"bodies.0000.cdat").unlink()
            (chain/"bodies.0002.cdat").unlink()
            with self.assertRaisesRegex(ValueError,"FAMILY_MISSING"):
                snap.verify_ancient_layout(db)

    def test_merge_heartbeat_preserves_all_files(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d)
            source=root/"source";dest=root/"dest"
            (source/"ancient").mkdir(parents=True)
            (source/"ancient"/"bodies.0000.cdat").write_bytes(b"a")
            (source/"CURRENT").write_bytes(b"MANIFEST-000001\n")
            observed=[]
            snap.merge_database(source,dest,lambda:observed.append(1))
            self.assertGreaterEqual(len(observed),2)
            self.assertEqual((dest/"CURRENT").read_bytes(),b"MANIFEST-000001\n")
            self.assertEqual((dest/"ancient"/"bodies.0000.cdat").read_bytes(),b"a")


if __name__=="__main__":unittest.main()
