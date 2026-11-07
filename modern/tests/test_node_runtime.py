import importlib.util
import inspect
import json
import pathlib
import sys
import tempfile
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def module(name):
    path = ROOT / (name + '.py')
    if not path.is_file():
        raise AssertionError(f'Production module missing: {path.name}')
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class GatewayPolicyTests(unittest.TestCase):
    def setUp(self):
        self.mod = module('rpc_proxy')

    def request(self, method='eth_chainId', params=None):
        return {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or []}

    def test_reads_allowed_broadcast_and_admin_rejected(self):
        self.mod.validate_request(self.request())
        for method in ['eth_sendRawTransaction', 'eth_sendTransaction', 'personal_unlockAccount',
                       'admin_peers', 'debug_traceTransaction', 'eth_sign']:
            with self.subTest(method=method), self.assertRaises(ValueError):
                self.mod.validate_request(self.request(method))

    def test_mixed_batch_cannot_hide_broadcast(self):
        with self.assertRaises(ValueError):
            self.mod.validate_payload([self.request(), self.request('eth_sendRawTransaction', ['0x01'])])

    def test_batch_is_bounded_and_never_empty(self):
        for payload in [[], [self.request()] * 51, None, 'eth_chainId']:
            with self.subTest(payload=str(payload)[:30]), self.assertRaises(ValueError):
                self.mod.validate_payload(payload)

    def test_log_window_bounded_and_explicit(self):
        self.mod.validate_request(self.request('eth_getLogs', [{'fromBlock': '0x100', 'toBlock': '0x110'}]))
        for filt in [{}, {'fromBlock': 'earliest', 'toBlock': 'latest'},
                     {'fromBlock': '0x1', 'toBlock': '0xffff'},
                     {'fromBlock': '0x20', 'toBlock': '0x10'}]:
            with self.subTest(filt=filt), self.assertRaises(ValueError):
                self.mod.validate_request(self.request('eth_getLogs', [filt]))

    def test_websocket_subscription_policy(self):
        self.mod.validate_request(self.request('eth_subscribe', ['newHeads']), websocket=True)
        with self.assertRaises(ValueError):
            self.mod.validate_request(self.request('eth_subscribe', ['newHeads']))
        with self.assertRaises(ValueError):
            self.mod.validate_request(self.request('eth_subscribe', ['newPendingTransactions', True]), websocket=True)

    def test_readiness_expires_and_rejects_future_time(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / 'ready.json'
            self.assertFalse(self.mod.is_ready(path, now=100))
            for state, checked, expected in [('PASS',99,True), ('PASS',60,False),
                                             ('FAIL',99,False), ('PASS',200,False)]:
                path.write_text(json.dumps({'status':state,'checkedAt':checked}))
                self.assertEqual(self.mod.is_ready(path,now=100),expected)


class BootstrapSafetyTests(unittest.TestCase):
    def setUp(self):
        self.mod = module('bootstrap')

    def test_config_overrides_unsafe_vendor_defaults(self):
        vendor = {'chain':'mainnet','p2p':{},'jsonrpc':{'http':{'vhosts':['*'],'corsdomain':['*']}}}
        bor = self.mod.configure_bor(vendor)
        self.assertEqual(bor['jsonrpc']['http']['host'],'127.0.0.1')
        self.assertEqual(bor['jsonrpc']['http']['port'],18545)
        self.assertEqual(bor['jsonrpc']['http']['corsdomain'],[])
        self.assertNotIn('*',bor['jsonrpc']['http']['vhosts'])
        self.assertEqual(bor['syncmode'],'snap')
        self.assertFalse(bor['miner']['mine'])
        self.assertEqual(bor['db.engine'],'pebble')
        self.assertEqual(bor['state.scheme'],'path')

    def test_heimdall_removes_vendor_external_ip_and_binds_local(self):
        cfg = {'p2p':{'external_address':'15.165.197.16:26656'},'rpc':{},'instrumentation':{}}
        app = {'api':{},'grpc':{},'heimdall':{}}
        cfg,app = self.mod.configure_heimdall(cfg,app)
        self.assertEqual(cfg['p2p']['external_address'],'')
        self.assertEqual(cfg['rpc']['laddr'],'tcp://127.0.0.1:26657')
        self.assertEqual(app['api']['address'],'tcp://127.0.0.1:1317')

    def test_heimdall_updates_actual_custom_configuration_section(self):
        _,app=self.mod.configure_heimdall({'p2p':{},'rpc':{},'instrumentation':{}},
            {'api':{},'grpc':{},'custom':{'bor_rpc_url':'http://localhost:8545'}})
        self.assertEqual(app['custom']['bor_rpc_url'],'http://127.0.0.1:18545')

    def test_hash_mismatch_never_replaces_destination(self):
        with tempfile.TemporaryDirectory() as d:
            path=pathlib.Path(d)/'file'
            path.write_bytes(b'keep-me')
            with self.assertRaises(ValueError):
                self.mod.verify_file(path,'0'*64)
            self.assertEqual(path.read_bytes(),b'keep-me')

    def test_xfs_label_is_valid_and_consistent_across_mount_lifecycle(self):
        label = self.mod.XFS_VOLUME_LABEL
        self.assertEqual(label, 'omega-pol137')
        self.assertLessEqual(len(label.encode('ascii')), 12)
        mount_source = inspect.getsource(self.mod.mount_volume)
        self.assertGreaterEqual(mount_source.count('XFS_VOLUME_LABEL'), 2)
        self.assertNotIn("'omega-polygon'", mount_source)

    def test_heimdall_nonvalidator_identity_is_idempotent_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            home = pathlib.Path(d)
            self.assertEqual(self.mod.heimdall_identity_state(home), 'MISSING')
            node_key = home / 'config/node_key.json'
            node_key.parent.mkdir()
            node_key.write_text('{"id":"test"}')
            with self.assertRaisesRegex(ValueError, 'PARTIAL_IDENTITY'):
                self.mod.heimdall_identity_state(home)
            val_key = home / 'config/priv_validator_key.json'
            val_key.write_text('{"address":"test"}')
            val_state = home / 'data/priv_validator_state.json'
            val_state.parent.mkdir()
            val_state.write_text('{"height":"0"}')
            self.assertEqual(self.mod.heimdall_identity_state(home), 'READY')
            self.assertEqual(node_key.read_text(), '{"id":"test"}')

    def test_disk_format_refuses_any_existing_signature(self):
        self.assertFalse(self.mod.may_format({'blockdevices':[{'name':'nvme1n1','type':'disk','fstype':'xfs','children':[]}]}))
        self.assertFalse(self.mod.may_format({'blockdevices':[{'name':'nvme1n1','type':'disk','fstype':None,'children':[{'name':'p1'}]}]}))
        self.assertTrue(self.mod.may_format({'blockdevices':[{'name':'nvme1n1','type':'disk','fstype':None}]}))


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.mod=module('monitor')

    def test_heimdall_sync_requires_real_boolean_and_fresh_chain137_head(self):
        raw={'result':{'node_info':{'network':'heimdallv2-137'},'sync_info':{
            'catching_up':False,'latest_block_height':'57006001',
            'latest_block_time':'2026-11-06T00:00:00Z'}}}
        self.assertTrue(self.mod.heimdall_ready(raw,now=1793923201))
        for value in [True, 'false', None]:
            raw['result']['sync_info']['catching_up']=value
            self.assertFalse(self.mod.heimdall_ready(raw,now=1793923201))


if __name__=='__main__':
    unittest.main()
