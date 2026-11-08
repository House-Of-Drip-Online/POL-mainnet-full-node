import pathlib
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import recovery_advisor as advisor

T=1794121000.0
OK_DISK=SimpleNamespace(total=8*1024**4,free=3*1024**4)
ACTIVE={"reason":"BOR_FULL_RESTORE_PENDING"}
PROGRESS={"status":"RESTORING","checkedAt":T-20,
          "component":"increment","compressedBytesRead":100,"componentBytes":1000}
NOT_READY={"status":"FAIL"}


def diagnose(*,maintenance=ACTIVE,progress=PROGRESS,readiness=NOT_READY,disk=OK_DISK):
    return advisor.classify(maintenance=maintenance,progress=progress,
                            readiness=readiness,disk=disk,now=T)


class RecoveryAdvisorTests(unittest.TestCase):
    def test_active_progress_continues_single_writer_only(self):
        d=diagnose()
        self.assertEqual(d["selected"],"PINNED_FULL_RESTORE")
        self.assertFalse(d["native_node_certified"])
        self.assertFalse(d["live_submission_authorized"])
        self.assertFalse(d["mutations_executed"])
        self.assertEqual(d["recovery_routes"][0]["state"],"CONTINUE_EXISTING_WRITER_ONLY")
        self.assertTrue(all(x["state"]!="CONTINUE_EXISTING_WRITER_ONLY"
                            for x in d["recovery_routes"][1:]))

    def test_stale_progress_requires_investigation_not_restart(self):
        d=diagnose(progress=dict(PROGRESS,checkedAt=T-650))
        self.assertEqual(d["selected"],"INVESTIGATE_RESTORE_STALL")
        self.assertIn("RESTORE_PROGRESS_STALE",d["alerts"])

    def test_corrupt_and_missing_component_progress_block(self):
        d=diagnose(progress=dict(PROGRESS,compressedBytesRead=1100))
        self.assertEqual(d["selected"],"INVESTIGATE_RESTORE_EVIDENCE")
        d=diagnose(progress={})
        self.assertIn("RESTORE_PROGRESS_MISSING",d["alerts"])

    def test_low_disk_free_and_unavailable_are_explicit(self):
        d=diagnose(disk=SimpleNamespace(total=8*1024**4,free=100*1024**3))
        self.assertEqual(d["selected"],"STORAGE_CAPACITY_REVIEW")
        self.assertIn("RESTORE_FREE_CAPACITY_BELOW_200_GIB",d["alerts"])
        d=diagnose(disk=None)
        self.assertEqual(d["selected"],"STORAGE_TELEMETRY_REVIEW")
        self.assertIn("DISK_OBSERVATION_UNAVAILABLE",d["alerts"])

    def test_maintenance_owner_must_not_be_overridden(self):
        d=diagnose(maintenance={"reason":"SOMEONE_ELSE_OWNS_NODE"})
        self.assertEqual(d["selected"],"STOP_FOR_GOVERNANCE_REVIEW")
        d=diagnose(maintenance={})
        self.assertEqual(d["selected"],"STOP_FOR_GOVERNANCE_REVIEW")
        self.assertIn("RESTORE_RUNNING_WITHOUT_OWNED_MAINTENANCE",d["alerts"])

    def test_ready_while_maintenance_active_is_contradiction(self):
        d=diagnose(readiness={"status":"PASS"})
        self.assertEqual(d["selected"],"STOP_FOR_GOVERNANCE_REVIEW")
        self.assertIn("CONTRADICTORY_READINESS_DURING_MAINTENANCE",d["alerts"])

    def test_restored_component_not_node_certification(self):
        d=diagnose(progress={"status":"RESTORED_PENDING_NATIVE_VALIDATION"})
        self.assertEqual(d["selected"],"VALIDATE_CANONICAL_BOR")
        self.assertFalse(d["native_node_certified"])

    def test_readiness_not_authorization(self):
        d=diagnose(maintenance={},progress={},readiness={"status":"PASS"})
        self.assertEqual(d["selected"],"VERIFY_CONSUMER_PATH_AND_RECOVERY_TESTS")
        self.assertFalse(d["native_node_certified"])
        self.assertFalse(d["live_submission_authorized"])


if __name__=="__main__":unittest.main()
