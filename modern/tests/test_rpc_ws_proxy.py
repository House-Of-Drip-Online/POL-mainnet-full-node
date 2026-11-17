"""Read-only Polygon WS gateway security and freshness regression tests."""
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import rpc_ws_proxy as proxy


def payload(method, params=None):
    return {"jsonrpc": "2.0", "id": 1, "method": method, "params": [] if params is None else params}


class PrivateWsProxyContractTests(unittest.TestCase):
    def test_private_gateway_is_fail_closed_without_readiness(self):
        with tempfile.TemporaryDirectory() as d:
            file = pathlib.Path(d) / "ready.json"
            self.assertFalse(proxy.is_ready(file, now=100))
            file.write_text(json.dumps({"status": "FAIL", "checkedAt": 98}))
            self.assertFalse(proxy.is_ready(file, now=100))
            file.write_text(json.dumps({"status": "PASS", "checkedAt": 20}))
            self.assertFalse(proxy.is_ready(file, now=100))
            file.write_text(json.dumps({"status": "PASS", "checkedAt": 98}))
            self.assertTrue(proxy.is_ready(file, now=100))

    def test_authorized_new_head_and_filter_log_subscriptions(self):
        proxy.validate_request(payload("eth_subscribe", ["newHeads"]), websocket=True)
        proxy.validate_request(payload("eth_subscribe", ["logs", {"address": "0x" + "1" * 40}]), websocket=True)
        proxy.validate_request(payload("eth_unsubscribe", ["0xabc"]), websocket=True)

    def test_signing_broadcast_mempool_trace_methods_rejected(self):
        for method in (
            "eth_sendRawTransaction", "eth_sendTransaction", "personal_sign",
            "eth_sign", "debug_traceTransaction", "txpool_content", "admin_peers",
            "eth_subscribe", "eth_unsubscribe",
        ):
            if method in ("eth_subscribe", "eth_unsubscribe"):
                with self.assertRaises(ValueError):
                    proxy.validate_request(payload(method, ["newHeads"]), websocket=False)
            else:
                with self.assertRaisesRegex(ValueError, "METHOD_NOT_ALLOWED"):
                    proxy.validate_request(payload(method, []), websocket=True)

    def test_pending_subscription_is_not_admitted(self):
        for params in (["newPendingTransactions"], ["syncing"], ["logs", {"address": []}, "extra"]):
            with self.assertRaises(ValueError):
                proxy.validate_request(payload("eth_subscribe", params), websocket=True)

    def test_all_batch_members_checked(self):
        rows = [payload("eth_chainId"), payload("eth_sendRawTransaction", ["0x123"])]
        with self.assertRaisesRegex(ValueError, "METHOD_NOT_ALLOWED"):
            proxy.validate_payload(rows, websocket=True)
        with self.assertRaisesRegex(ValueError, "BATCH_LIMIT"):
            proxy.validate_payload([payload("eth_chainId") for _ in range(proxy.MAX_BATCH + 1)])

    def test_explicit_historical_log_range_is_bounded(self):
        proxy.validate_request(payload("eth_getLogs", [{"fromBlock": "0xa", "toBlock": "0x20"}]))
        with self.assertRaisesRegex(ValueError, "LOG_WINDOW_LIMIT"):
            proxy.validate_request(payload("eth_getLogs", [{"fromBlock": "0x0", "toBlock": "0x800"}]))
        with self.assertRaisesRegex(ValueError, "EXPLICIT_LOG_WINDOW_REQUIRED"):
            proxy.validate_request(payload("eth_getLogs", [{"fromBlock": "latest"}]))

    def test_blockhash_and_range_cannot_mix(self):
        block = "0x" + "0" * 64
        proxy.validate_request(payload("eth_getLogs", [{"blockHash": block}]))
        with self.assertRaisesRegex(ValueError, "AMBIGUOUS_LOG_FILTER"):
            proxy.validate_request(payload("eth_getLogs", [{"blockHash": block, "fromBlock": "0x1"}]))

    def test_no_argument_rpc_validation(self):
        proxy.validate_request(payload("eth_chainId"))
        with self.assertRaisesRegex(ValueError, "NO_ARGUMENTS_EXPECTED"):
            proxy.validate_request(payload("eth_chainId", ["extra"]))


if __name__ == "__main__":
    unittest.main()
