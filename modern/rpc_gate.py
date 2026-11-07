#!/usr/bin/env python3
"""Read-only Polygon 137 local-node acceptance gate.

Never logs endpoints, secrets, or strategies; never signs or broadcasts.
Every check is pinned to immutable header identity with an independent RPC.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from typing import Any, Callable

HASH = re.compile(r'^0x[0-9a-fA-F]{64}$')
Query = Callable[[str,str,list[Any],float], Any]


class RpcFailure(ValueError):
    """Invalid gate configuration."""


def rpc_query(url: str, method: str, params: list[Any], timeout: float) -> Any:
    request = urllib.request.Request(url, method='POST', headers={
        'content-type':'application/json','user-agent':'OMEGA-PolygonNode/1.0'},
        data=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode())
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data=json.loads(response.read(1024*1024))
    if not isinstance(data,dict) or data.get('jsonrpc')!='2.0' or data.get('id')!=1 or data.get('error') or 'result' not in data:
        raise ValueError('INVALID_JSON_RPC_RESPONSE')
    return data['result']


def height(raw:Any)->int:
    if not isinstance(raw,str) or not re.fullmatch(r'0x[0-9a-fA-F]+',raw):
        raise ValueError('INVALID_RPC_HEX_HEIGHT')
    n=int(raw,16)
    if n < 0 or n >= 1<<64:raise ValueError('BLOCK_HEIGHT_OUT_OF_RANGE')
    return n


def read_head(raw:Any)->dict[str,Any]:
    if not isinstance(raw,dict) or not isinstance(raw.get('hash'),str) or not HASH.fullmatch(raw['hash']):
        raise ValueError('INVALID_HEAD_HASH')
    return {'height':height(raw.get('number')),'hash':raw['hash'].lower(),'timestamp':height(raw.get('timestamp'))}


def evaluate_rpc_gate(local_url:str, reference_url:str,*,
        max_lag_blocks:int=2,max_head_age_seconds:int=120,timeout_seconds:float=5.0,
        now_seconds:float|None=None,query:Query=rpc_query)->dict[str,Any]:
    if not local_url.startswith(('http://','https://')) or not reference_url.startswith(('http://','https://')) or local_url==reference_url:
        raise RpcFailure('LOCAL_AND_REFERENCE_URLS_MUST_BE_DISTINCT')
    if not isinstance(max_lag_blocks,int) or max_lag_blocks<0 or max_lag_blocks>128 or not isinstance(max_head_age_seconds,int) or not 10<=max_head_age_seconds<=3600 or not 0<timeout_seconds<=30:
        raise RpcFailure('RPC_GATE_CONFIG_INVALID')
    now = time.time() if now_seconds is None else now_seconds
    failures:list[str]=[]
    out:dict[str,Any]={'schema':'omega.polygon137.rpc-gate.v1','status':'FAIL','chainId':137,
        'executionAuthorized':False,'independentOperatorProven':False,'lagBlocks':None,
        'canonicalComparisonBlock':None,'failures':failures}
    try:
        local_chain=query(local_url,'eth_chainId',[],timeout_seconds)
        ref_chain=query(reference_url,'eth_chainId',[],timeout_seconds)
        if height(local_chain)!=137: failures.append('LOCAL_CHAIN_ID_MISMATCH')
        if height(ref_chain)!=137: failures.append('REFERENCE_CHAIN_ID_MISMATCH')
        if failures:return out
        sync=query(local_url,'eth_syncing',[],timeout_seconds)
        if sync is not False: failures.append('LOCAL_SYNC_INCOMPLETE')
        if query(reference_url,'eth_syncing',[],timeout_seconds) is not False:
            failures.append('REFERENCE_SYNC_INCOMPLETE')
        raw_local=query(local_url,'eth_getBlockByNumber',['latest',False],timeout_seconds)
        raw_ref=query(reference_url,'eth_getBlockByNumber',['latest',False],timeout_seconds)
        try:local=read_head(raw_local)
        except (ValueError,TypeError):failures.append('LOCAL_HEAD_INVALID');local=None
        try:ref=read_head(raw_ref)
        except (ValueError,TypeError):failures.append('REFERENCE_HEAD_INVALID');ref=None
        if not local or not ref:return out
        for name,row in [('LOCAL',local),('REFERENCE',ref)]:
            if row['timestamp']>now+10 or now-row['timestamp']>max_head_age_seconds:
                failures.append(f'{name}_HEAD_STALE')
        lag=max(0,ref['height']-local['height'])
        out['lagBlocks']=lag
        if lag>max_lag_blocks:failures.append('NODE_LAG_LIMIT_EXCEEDED')
        if local['height']-ref['height']>max_lag_blocks:
            failures.append('REFERENCE_LAG_LIMIT_EXCEEDED')
        pin=min(local['height'],ref['height'])
        out['canonicalComparisonBlock']=pin
        local_pin=read_head(query(local_url,'eth_getBlockByNumber',[hex(pin),False],timeout_seconds))
        ref_pin=read_head(query(reference_url,'eth_getBlockByNumber',[hex(pin),False],timeout_seconds))
        if local_pin['height']!=pin or ref_pin['height']!=pin:failures.append('PINNED_HEADER_HEIGHT_MISMATCH')
        if local_pin['hash']!=ref_pin['hash']:failures.append('PINNED_HASH_DISAGREEMENT')
        # Detect local providers giving two incompatible responses at the SAME head.
        if local['height']==pin and local['hash']!=local_pin['hash']:failures.append('LOCAL_HEAD_REORG_DURING_GATE')
        if ref['height']==pin and ref['hash']!=ref_pin['hash']:failures.append('REFERENCE_HEAD_REORG_DURING_GATE')
    except Exception:
        # Never emit exception text: provider URLs often contain API keys.
        failures.append('RPC_READ_OR_RESPONSE_FAILED')
    out['failures']=sorted(set(failures))
    out['status']='PASS' if not out['failures'] else 'FAIL'
    return out


def main()->int:
    p=argparse.ArgumentParser(description='Check private Bor against independent Polygon RPC; never broadcasts')
    p.add_argument('--local-url',required=True)
    p.add_argument('--reference-url',required=True)
    p.add_argument('--max-lag-blocks',type=int,default=2)
    p.add_argument('--max-head-age-seconds',type=int,default=120)
    p.add_argument('--timeout-seconds',type=float,default=5)
    args=p.parse_args()
    try:
        result=evaluate_rpc_gate(args.local_url,args.reference_url,
            max_lag_blocks=args.max_lag_blocks,max_head_age_seconds=args.max_head_age_seconds,
            timeout_seconds=args.timeout_seconds)
    except RpcFailure:
        result={'schema':'omega.polygon137.rpc-gate.v1','status':'FAIL','executionAuthorized':False,
            'failures':['INVALID_GATE_CONFIGURATION']}
    print(json.dumps(result,sort_keys=True))
    return 0 if result['status']=='PASS' else 2

if __name__=='__main__':sys.exit(main())
