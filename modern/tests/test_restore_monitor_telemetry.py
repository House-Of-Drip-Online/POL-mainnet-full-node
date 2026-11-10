"""Regression: maintenance must not suppress disk/restore telemetry or fake 0% usage."""
import datetime
import io
import json
import pathlib
import sys
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import monitor


class RestoreMonitoringTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.maintenance=pathlib.Path(self.tmp.name)/"maintenance.json"
        self.progress=pathlib.Path(self.tmp.name)/"progress.json"
        self.maintenance.write_text(json.dumps({"reason":"BOR_FULL_RESTORE_PENDING"}))
        self._patches=[
            patch.object(monitor,"MAINTENANCE_PATH",self.maintenance),
            patch.object(monitor,"RESTORE_PROGRESS_PATH",self.progress),
            patch.object(monitor,"read_heimdall",return_value=self.heimdall()),
            patch.object(monitor.urllib.request,"urlopen",
                         side_effect=lambda *args,**kwargs:io.BytesIO(b'{"result":{"n_peers":"27"}}')),
        ]
        for obj in self._patches:
            obj.start()
            self.addCleanup(obj.stop)

    @staticmethod
    def heimdall():
        ts=datetime.datetime.now(datetime.timezone.utc).isoformat()
        return {"result":{"node_info":{"network":"heimdallv2-137"},
                          "sync_info":{"latest_block_time":ts,
                                       "latest_block_height":"57380817",
                                       "latest_block_hash":"0x"+"0"*64,
                                       "catching_up":False}}}

    def snapshot_progress(self, age=10):
        self.progress.write_text(json.dumps({"status":"RESTORING",
            "checkedAt":time.time()-age,"component":"increment",
            "compressedBytesRead":500,"componentBytes":1000,"bytesPerSecond":50}))

    def observe(self,total=1024**4,free=1024**4//2):
        with patch.object(monitor.shutil,"disk_usage",
                          return_value=SimpleNamespace(total=total,used=total-free,free=free)):
            return monitor.check("https://reference.invalid")

    def test_maintenance_includes_real_disk_usage_and_restore_progress(self):
        self.snapshot_progress()
        d=self.observe()
        self.assertEqual(d["status"],"FAIL")
        self.assertIn("NODE_MAINTENANCE",d["failures"])
        self.assertAlmostEqual(d["diskUsedPercent"],50)
        self.assertAlmostEqual(d["restoreComponentPercent"],50)
        self.assertLess(d["restoreProgressAgeSeconds"],180)
        metrics={m["MetricName"]:m["Value"] for m in monitor.cloudwatch_metrics(d,"node")}
        self.assertEqual(metrics["DiskUsedPercent"],50)
        self.assertEqual(metrics["DiskTelemetryHealthy"],1)
        self.assertEqual(metrics["RestoreComponentPercent"],50)

    def test_disk_pressure_detected_during_restore(self):
        self.snapshot_progress()
        d=self.observe(total=1000*1024**3,free=90*1024**3)
        self.assertIn("DISK_PRESSURE",d["failures"])
        self.assertAlmostEqual(d["diskUsedPercent"],91)
        self.assertEqual(d["status"],"FAIL")

    def test_restore_staleness_reported_without_clearing_maintenance(self):
        self.snapshot_progress(age=600)
        d=self.observe()
        self.assertIn("RESTORE_PROGRESS_STALE",d["failures"])
        self.assertIn("NODE_MAINTENANCE",d["failures"])
        self.assertGreater(d["restoreProgressAgeSeconds"],180)

    def test_disk_probe_failure_does_not_emit_fake_zero_percent(self):
        self.snapshot_progress()
        with patch.object(monitor.shutil,"disk_usage",side_effect=OSError("disk unreachable")):
            d=monitor.check("https://reference.invalid")
        self.assertIn("DISK_TELEMETRY_UNAVAILABLE",d["failures"])
        self.assertNotIn("diskUsedPercent",d)
        metrics={m["MetricName"]:m["Value"] for m in monitor.cloudwatch_metrics(d,"node")}
        self.assertNotIn("DiskUsedPercent",metrics)
        self.assertEqual(metrics["DiskTelemetryHealthy"],0)

    def test_bad_restore_progress_fails_closed(self):
        self.progress.write_text(json.dumps({"status":"RESTORING",
            "checkedAt":time.time(),"compressedBytesRead":150,"componentBytes":100}))
        d=self.observe()
        self.assertIn("RESTORE_PROGRESS_INVALID",d["failures"])

    def test_merge_heartbeat_reports_age_not_quote_download_fraction(self):
        self.progress.write_text(json.dumps({"status":"MERGING","checkedAt":time.time()-10,
                                             "processedEntries":13000}))
        d=self.observe()
        self.assertEqual(d["restore"]["status"],"MERGING")
        self.assertLess(d["restoreProgressAgeSeconds"],180)
        self.assertNotIn("restoreComponentPercent",d)
        self.assertNotIn("RESTORE_PROGRESS_INVALID",d["failures"])

    def test_missing_restore_progress_is_explicit(self):
        d=self.observe()
        self.assertIn("RESTORE_PROGRESS_MISSING",d["failures"])

    def test_terminal_failure_cannot_appear_as_running_progress(self):
        self.progress.write_text(json.dumps({'status':'FAILED','checkedAt':time.time(),
            'component':'increment','failureType':'HTTPError','failedCondition':'HTTP_404',
            'compressedBytesRead':500,'componentBytes':1000}))
        d=self.observe()
        self.assertEqual(d['status'],'FAIL')
        self.assertIn('RESTORE_FAILED',d['failures'])
        self.assertNotIn('restoreComponentPercent',d)
        self.assertTrue(self.maintenance.exists())


    def test_rpc_peer_and_lag_metrics_preserve_real_measurements(self):
        result = {'status':'PASS','failures':[],'peerCount':41,
                  'lagBlocks':1,'heimdall':{'peers':24}}
        metrics = {m['MetricName']:m['Value'] for m in monitor.cloudwatch_metrics(result,'node')}
        self.assertEqual(metrics['BorPeers'],41)
        self.assertEqual(metrics['HeimdallPeers'],24)
        self.assertEqual(metrics['NodeLagBlocks'],1)
        self.assertEqual(metrics['RPCGateFailed'],0)

    def test_missing_and_malformed_rpc_metrics_never_become_zero(self):
        result = {'status':'FAIL','failures':['RPC_READ_OR_RESPONSE_FAILED'],
                  'peerCount':False,'lagBlocks':None,'heimdall':{'peers':'0'}}
        metrics = {m['MetricName']:m['Value'] for m in monitor.cloudwatch_metrics(result,'node')}
        for name in ('BorPeers','HeimdallPeers','NodeLagBlocks'):
            self.assertNotIn(name,metrics)
        self.assertEqual(metrics['RPCGateFailed'],1)


if __name__=="__main__":unittest.main()
