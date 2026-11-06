import json
import unittest
from unittest.mock import patch
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rpc_gate import evaluate_rpc_gate, RpcFailure


def block(number, block_hash='0x'+'a'*64, timestamp=1793952000):
    return {'number':hex(number),'hash':block_hash,'timestamp':hex(timestamp)}

class RpcGateTests(unittest.TestCase):
    def evidence(self, local_height=100, ref_height=101, hash_match=True, sync=False, now=1793952050):
        actual_hash='0x'+'a'*64
        wrong_hash='0x'+'b'*64
        def query(endpoint, method, params, timeout):
            local=endpoint=='http://private:8545'
            if method=='eth_chainId':return '0x89'
            if method=='eth_syncing':return sync if local else False
            if method=='eth_getBlockByNumber':
                req=params[0]
                if req=='latest': return block(local_height if local else ref_height,actual_hash if local else actual_hash)
                return block(int(req,16),actual_hash if (hash_match or not local) else wrong_hash)
            raise AssertionError(method)
        return query

    def gate(self, **kwargs):
        custom_query=kwargs.pop('query',None)
        return evaluate_rpc_gate('http://private:8545','https://independent.example/rpc',
                max_lag_blocks=2,max_head_age_seconds=120,timeout_seconds=3,
                now_seconds=1793952050,query=custom_query if custom_query is not None else self.evidence(**kwargs))

    def test_healthy_synced_matching_hash(self):
        result=self.gate()
        self.assertEqual(result['status'],'PASS')
        self.assertEqual(result['canonicalComparisonBlock'],100)
        self.assertEqual(result['lagBlocks'],1)
        self.assertFalse(result['executionAuthorized'])
        self.assertNotIn('private:8545',json.dumps(result))

    def test_syncing_rejected(self):
        result=self.gate(sync={'startingBlock':'0x1'})
        self.assertEqual(result['status'],'FAIL')
        self.assertIn('LOCAL_SYNC_INCOMPLETE',result['failures'])

    def test_lag_rejected(self):
        result=self.gate(local_height=90,ref_height=100)
        self.assertIn('NODE_LAG_LIMIT_EXCEEDED',result['failures'])

    def test_cross_provider_hash_mismatch_rejected(self):
        result=self.gate(hash_match=False)
        self.assertIn('PINNED_HASH_DISAGREEMENT',result['failures'])

    def test_wrong_chain_id_rejected(self):
        q=self.evidence()
        def wrong(endpoint,method,params,timeout):
            if method=='eth_chainId' and endpoint.startswith('http:'):return '0x1'
            return q(endpoint,method,params,timeout)
        result=self.gate(query=wrong)
        self.assertIn('LOCAL_CHAIN_ID_MISMATCH',result['failures'])

    def test_stale_header_rejected(self):
        q=self.evidence()
        def stale(endpoint,method,params,timeout):
            value=q(endpoint,method,params,timeout)
            if method=='eth_getBlockByNumber' and params[0]=='latest' and endpoint.startswith('http:'):
                return {**value,'timestamp':hex(1793900000)}
            return value
        result=self.gate(query=stale)
        self.assertIn('LOCAL_HEAD_STALE',result['failures'])

    def test_same_url_refused(self):
        with self.assertRaises(RpcFailure):
            evaluate_rpc_gate('http://same:8545','http://same:8545',query=self.evidence(),now_seconds=1793952050)

    def test_invalid_block_data_rejected(self):
        q=self.evidence()
        def corrupt(endpoint,method,params,timeout):
            value=q(endpoint,method,params,timeout)
            if method=='eth_getBlockByNumber' and params[0]=='latest' and endpoint.startswith('http:'):
                return {**value,'hash':'oops'}
            return value
        result=self.gate(query=corrupt)
        self.assertIn('LOCAL_HEAD_INVALID',result['failures'])

    def test_errors_fail_closed_without_secret_leaks(self):
        def error(endpoint,method,params,timeout):
            raise OSError('failure secret-123')
        result=self.gate(query=error)
        self.assertEqual(result['status'],'FAIL')
        self.assertNotIn('secret-123',json.dumps(result))
        self.assertFalse(result['executionAuthorized'])

if __name__=='__main__':unittest.main()