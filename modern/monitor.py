#!/usr/bin/env python3
"""Continuous sync gate, atomic readiness, disk telemetry and CloudWatch evidence."""
from __future__ import annotations
import argparse
import datetime
import json
import os
import pathlib
import shutil
import subprocess
import time
import urllib.request

from rpc_gate import evaluate_rpc_gate, rpc_query, height


def heimdall_ready(raw, *, now=None):
    try:
        data=raw['result']
        info=data['sync_info']
        stamp=datetime.datetime.fromisoformat(info['latest_block_time'].replace('Z','+00:00')).timestamp()
        age=(time.time() if now is None else now)-stamp
        return (data['node_info']['network']=='heimdallv2-137'
                and info['catching_up'] is False
                and int(info['latest_block_height'])>57006000 and -10<=age<=120)
    except (KeyError,TypeError,ValueError):return False


def read_heimdall():
    with urllib.request.urlopen('http://127.0.0.1:26657/status',timeout=4) as r:
        return json.loads(r.read(1024*1024))


def check(reference):
    result={'status':'FAIL','failures':[],'checkedAt':time.time(),'executionAuthorized':False}
    try:
        if not heimdall_ready(read_heimdall()):
            result['failures'].append('HEIMDALL_NOT_READY')
        gate=evaluate_rpc_gate('http://127.0.0.1:18545',reference,timeout_seconds=4)
        result.update({k:v for k,v in gate.items() if k not in ('failures','status')})
        result['failures']+=gate['failures']
        peers=height(rpc_query('http://127.0.0.1:18545','net_peerCount',[],4))
        result['peerCount']=peers
        if peers<1:result['failures'].append('NO_BOR_PEERS')
        usage=shutil.disk_usage('/data')
        result['diskUsedPercent']=100*(1-usage.free/usage.total)
        if usage.free<100*1024**3 or result['diskUsedPercent']>=95:
            result['failures'].append('DISK_PRESSURE')
    except Exception:
        result['failures'].append('MONITOR_READ_FAILED')
    result['status']='PASS' if not result['failures'] else 'FAIL'
    result['checkedAt']=time.time()
    return result


def write_atomic(path,data):
    path=pathlib.Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.tmp')
    with temp.open('w') as f:
        json.dump(data,f,sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    temp.chmod(0o644)
    temp.replace(path)


def emit_cloudwatch(settings,result):
    import boto3
    from botocore.config import Config
    cfg=Config(connect_timeout=2,read_timeout=3,retries={'max_attempts':1})
    logs=boto3.client('logs',region_name=settings['region'],config=cfg)
    stream='node-health'
    try:logs.create_log_stream(logGroupName=settings['logGroup'],logStreamName=stream)
    except logs.exceptions.ResourceAlreadyExistsException:pass
    logs.put_log_events(logGroupName=settings['logGroup'],logStreamName=stream,
        logEvents=[{'timestamp':int(time.time()*1000),'message':json.dumps(result,sort_keys=True)}])
    metrics=[{'MetricName':'Ready','Value':int(result['status']=='PASS'),'Unit':'Count'},
             {'MetricName':'DiskUsedPercent','Value':result.get('diskUsedPercent',0),'Unit':'Percent'}]
    for row in metrics:row['Dimensions']=[{'Name':'Node','Value':settings['nodeName']}]
    boto3.client('cloudwatch',region_name=settings['region'],config=cfg).put_metric_data(
        Namespace='OMEGA/PolygonNode',MetricData=metrics)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--settings',default='/etc/omega-polygon/settings.json')
    p.add_argument('--heimdall-only',action='store_true')
    args=p.parse_args()
    if args.heimdall_only:
        try:return 0 if heimdall_ready(read_heimdall()) else 1
        except Exception:return 1
    settings=json.loads(pathlib.Path(args.settings).read_text())
    # A one-shot timer retries while Heimdall is catching up. Bor starts only
    # after this check passes; its systemd precondition repeats at every restart.
    try:
        if heimdall_ready(read_heimdall()):
            subprocess.run(['systemctl','start','--no-block','bor.service'],check=True)
    except Exception:pass
    result=check(settings['referenceUrl'])
    result['sourceCommit']=settings['sourceCommit']
    write_atomic('/run/omega-polygon/readiness.json',result)
    print(json.dumps(result,sort_keys=True),flush=True)
    try:emit_cloudwatch(settings,result)
    except Exception:print('{"event":"CLOUDWATCH_EXPORT_FAILED"}',flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
