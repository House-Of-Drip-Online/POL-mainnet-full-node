import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "probes" / "native_25_cycle_cert.py"
spec = importlib.util.spec_from_file_location("native_25_cycle_cert", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

H = "0x" + "a" * 64

def query(url, method, params, timeout):
    if method == "eth_chainId":
        return "0x89"
    if method == "eth_syncing":
        return False
    if method == "net_peerCount":
        return "0x64"
    if method == "eth_getBlockByNumber":
        return {"number": "0x64", "hash": H, "timestamp": "0x3e8"}
    raise AssertionError(method)


class NativeCycleProbeTests(unittest.TestCase):
    def test_exact_same_height_chain_hash_and_private_gateway_pass(self):
        row = module.sample_native_cycle("http://local", "http://reference",
                                         "http://gateway", query=query, now_seconds=1000.0)
        self.assertEqual("PASS", row["status"])
        self.assertEqual(100, row["borPeers"])
        self.assertEqual(0, row["lagBlocks"])
        self.assertEqual(100, row["canonicalComparisonBlock"])
        self.assertFalse(row["executionAuthorized"])
        self.assertTrue(row["gatewayReady"])

    def test_gateway_failure_keeps_node_unready(self):
        def unavailable(url, method, params, timeout):
            if url == "http://gateway":
                raise ConnectionError("not ready")
            return query(url, method, params, timeout)
        row = module.sample_native_cycle("http://local", "http://reference",
                                         "http://gateway", query=unavailable, now_seconds=1000.0)
        self.assertEqual("FAIL", row["status"])
        self.assertFalse(row["gatewayReady"])

    def test_canonical_hash_disagreement_fails(self):
        def mismatch(url, method, params, timeout):
            if url == "http://reference" and method == "eth_getBlockByNumber":
                return {"number": "0x64", "hash": "0x" + "b"*64, "timestamp": "0x3e8"}
            return query(url, method, params, timeout)
        row = module.sample_native_cycle("http://local", "http://reference",
                                         "http://gateway", query=mismatch, now_seconds=1000.0)
        self.assertEqual("FAIL", row["status"])
        self.assertIn("PINNED_HASH_DISAGREEMENT", row["failures"])


if __name__ == "__main__":
    unittest.main()
