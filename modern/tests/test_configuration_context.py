import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from configuration_context import assert_operational_configuration
from commissioning_witness import evaluate_witness


def observation(block,status="PASS"):
    return {"schema":"omega.polygon137.rpc-gate.v1","chainId":137,
            "canonicalComparisonBlock":block,"status":status,
            "failures":[] if status=="PASS" else ["NODE_LAG_LIMIT_EXCEEDED"]}


class ConfigurationSeparationTests(unittest.TestCase):
    def test_runtime_admission_has_no_witness_counter(self):
        assert_operational_configuration({"OMEGA_CONFIGURATION_CONTEXT":"RUNTIME"})

    def test_runtime_rejects_other_contexts_and_build_inputs(self):
        for env in ({"OMEGA_CONFIGURATION_CONTEXT":"BUILD"},
                    {"OMEGA_CONFIGURATION_CONTEXT":"COMMISSIONING"},
                    {"OMEGA_BUILD_AUTHORITY":"ECS_FARGATE"},
                    {"OMEGA_COMMISSIONING_REQUIRED_OBSERVATIONS":"25"}):
            with self.subTest(env=env),self.assertRaises(ValueError):
                assert_operational_configuration(env)

    def test_25_advancing_header_observations_remain_a_separate_witness(self):
        result=evaluate_witness([observation(h) for h in range(100,125)])
        self.assertTrue(result["witness_passed"])
        self.assertFalse(result["blocks_operational_admission"])
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["native_pool_state_certified"])

    def test_same_block_repetition_cannot_complete_the_witness(self):
        self.assertFalse(evaluate_witness([observation(100)]*25)["witness_passed"])

    def test_failure_breaks_consecutive_sequence(self):
        rows=[observation(h) for h in range(100,124)]+[observation(124,"FAIL"),observation(125)]
        self.assertEqual(evaluate_witness(rows)["consecutive_passes"],1)

    def test_wrong_chain_or_arbitrary_pass_label_cannot_count(self):
        self.assertFalse(evaluate_witness([{"status":"PASS","canonicalComparisonBlock":h} for h in range(100,125)])["witness_passed"])

    def test_existing_native_collector_records_are_consumed_without_a_duplicate_collector(self):
        rows=[{"schema":"omega.polygon137.native-cycle-witness.v1","sourceChainId":137,
               "canonicalComparisonBlock":h,"status":"PASS","failures":[]} for h in range(100,125)]
        result=evaluate_witness(rows+[{"summary":{"cycles":25}}])
        self.assertTrue(result["witness_passed"])
        self.assertEqual(result["observations_examined"],25)
