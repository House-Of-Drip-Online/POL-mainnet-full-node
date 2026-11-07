import importlib.util
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        path=ROOT/'deploy.py'
        self.assertTrue(path.exists(),'Missing executable AWS deployment controller')
        spec=importlib.util.spec_from_file_location('deploy',path)
        self.mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.mod)

    def test_root_and_wrong_account_are_rejected_before_mutation(self):
        for identity in [{'Account':'919989872157','Arn':'arn:aws:iam::919989872157:root'},
                         {'Account':'123456789012','Arn':'arn:aws:sts::123456789012:assumed-role/Node/session'}]:
            with self.subTest(identity=identity),self.assertRaises(ValueError):
                self.mod.assert_deployer(identity,'919989872157')

    def test_assumed_role_identity_allowed(self):
        self.mod.assert_deployer({'Account':'919989872157','Arn':'arn:aws:sts::919989872157:assumed-role/Node/session'},'919989872157')

    def test_owner_authorized_root_exception_is_explicit(self):
        identity={'Account':'919989872157','Arn':'arn:aws:iam::919989872157:root'}
        self.mod.assert_deployer(identity,'919989872157',owner_authorized_root=True)
        with self.assertRaises(ValueError):
            self.mod.assert_deployer(identity,'123456789012',owner_authorized_root=True)

    def test_no_unreviewed_deletion_or_replacement(self):
        for action,replacement in [('Remove',None),('Modify','True'),('Modify','Conditional')]:
            with self.subTest(action=action),self.assertRaises(ValueError):
                self.mod.assert_nondestructive([{'ResourceChange':{'Action':action,'Replacement':replacement}}])
        self.mod.assert_nondestructive([{'ResourceChange':{'Action':'Add'}}])

    def test_cost_includes_gp3_performance_and_root_disk(self):
        estimate=self.mod.monthly_base_cost()
        self.assertAlmostEqual(estimate['total'],1352.802,places=2)


if __name__=='__main__':unittest.main()
