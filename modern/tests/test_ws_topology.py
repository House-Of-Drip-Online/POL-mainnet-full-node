"""Deployment-topology parity: separate private HTTP/WS gateways, no public RPC."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class NodeTopologyTests(unittest.TestCase):
    def test_websocket_service_execs_readiness_guarded_gateway(self):
        unit=(ROOT/'templates/omega-rpc-ws.service').read_text()
        self.assertIn('rpc_ws_proxy.py --bind @PRIVATE_IP@',unit)
        self.assertIn('User=omega-rpc',unit)
        self.assertIn('ProtectSystem=strict',unit)
        self.assertIn('ReadOnlyPaths=/run/omega-polygon',unit)

    def test_bootstrap_enables_and_starts_both_private_rpc_services(self):
        source=(ROOT/'bootstrap.py').read_text()
        for action in ("enable","start"):
            self.assertIn(f"run('systemctl','{action}','heimdalld.service','omega-rpc.service','omega-rpc-ws.service','omega-monitor.timer')",source)

    def test_cfn_clients_only_and_8546_websocket_output(self):
        source=(ROOT/'aws/node.yaml').read_text()
        self.assertIn("FromPort: 8546\n          ToPort: 8546\n          SourceSecurityGroupId: !Ref ClientSecurityGroup",source)
        self.assertIn("PrivateWebSocket: {Value: !Sub 'ws://${Node.PrivateIp}:8546'}",source)
        self.assertIn("PrivateRpc: {Value: !Sub 'http://${Node.PrivateIp}:8545'}",source)
        self.assertNotIn("PrivateWebSocket: {Value: !Sub 'ws://${Node.PrivateIp}:8545'}",source)


if __name__=='__main__':unittest.main()
