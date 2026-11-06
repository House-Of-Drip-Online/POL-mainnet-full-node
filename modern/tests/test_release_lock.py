import json
import pathlib
import re
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]

class ReleaseLockTests(unittest.TestCase):
    def test_approved_polygon_mainnet_binary_pair_is_pinned(self):
        lock=json.loads((ROOT/'release-lock.json').read_text())
        self.assertEqual(lock['schema'],'omega.polygon137.node-release-lock.v1')
        self.assertEqual(lock['chainId'],137)
        self.assertEqual(lock['architecture'],'amd64')
        self.assertEqual(lock['bor']['tag'],'v2.11.0')
        self.assertEqual(lock['heimdall']['tag'],'v0.13.2')
        for product in ('bor','heimdall'):
            for artifact in lock[product]['artifacts']:
                self.assertTrue(artifact['url'].startswith('https://github.com/0xPolygon/'))
                self.assertRegex(artifact['sha256'],r'^[a-f0-9]{64}$')
                self.assertTrue(artifact['name'].endswith('.deb'))
        self.assertEqual(len(lock['bor']['artifacts']),2)
        self.assertEqual(len(lock['heimdall']['artifacts']),2)

    def test_stager_has_no_automatic_package_install_or_service_start(self):
        stage=(ROOT/'stage-signed-releases.yml').read_text()
        self.assertIn('ansible.builtin.get_url',stage)
        self.assertIn('checksum:',stage)
        self.assertNotIn('ansible.builtin.apt:',stage)
        self.assertNotIn('ansible.builtin.systemd:',stage)
        self.assertNotIn('shell:',stage)
        self.assertNotIn('command:',stage)

if __name__=='__main__':unittest.main()