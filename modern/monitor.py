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

MAINTENANCE_PATH = pathlib.Path('/etc/omega-polygon/maintenance.json')
RESTORE_PROGRESS_PATH = pathlib.Path('/data/bor/full-restore/progress.json')


def bor_start_allowed(raw, *, maintenance_path=MAINTENANCE_PATH, now=None):
    return not pathlib.Path(maintenance_path).exists() and heimdall_ready(raw, now=now)


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
    # Storage observability is essential *during* multi-terabyte restoration.
    # Never skip this on the maintenance short-circuit or synthesize 0% use.
    try:
        usage = shutil.disk_usage('/data')
        if usage.total <= 0 or usage.free < 0 or usage.free > usage.total:
            raise ValueError('INVALID_DISK_USAGE')
        result['diskUsedPercent'] = 100 * (1 - usage.free / usage.total)
        result['diskFreeGiB'] = usage.free / 1024**3
        if usage.free < 100 * 1024**3 or result['diskUsedPercent'] >= 95:
            result['failures'].append('DISK_PRESSURE')
    except (OSError, ValueError, ZeroDivisionError):
        result['failures'].append('DISK_TELEMETRY_UNAVAILABLE')
    try:
        heimdall = read_heimdall()
        sync = heimdall['result']['sync_info']
        result['heimdall'] = {'height': int(sync['latest_block_height']),
            'catchingUp': sync['catching_up'], 'blockTime': sync['latest_block_time'],
            'blockHash': sync['latest_block_hash'], 'ready': heimdall_ready(heimdall)}
        with urllib.request.urlopen('http://127.0.0.1:26657/net_info', timeout=4) as response:
            result['heimdall']['peers'] = int(json.loads(response.read(1024*1024))['result']['n_peers'])
        if not result['heimdall']['ready'] or result['heimdall']['peers'] < 1:
            result['failures'].append('HEIMDALL_NOT_READY')
        if MAINTENANCE_PATH.exists():
            result['failures'].append('NODE_MAINTENANCE')
            try:
                result['maintenance'] = json.loads(MAINTENANCE_PATH.read_text())
                progress = RESTORE_PROGRESS_PATH
                if progress.exists():
                    result['restore'] = json.loads(progress.read_text())
                    payload = result['restore']
                    if not isinstance(payload, dict):
                        raise ValueError('RESTORE_PROGRESS_RECORD_INVALID')
                    if payload.get('status') == 'RESTORING':
                        checked = payload.get('checkedAt')
                        age = time.time() - checked if type(checked) in (int, float) else float('inf')
                        result['restoreProgressAgeSeconds'] = round(age, 3) if age != float('inf') else None
                        if not -30 <= age <= 180:
                            result['failures'].append('RESTORE_PROGRESS_STALE')
                        read, total = payload.get('compressedBytesRead'), payload.get('componentBytes')
                        if type(read) is int and type(total) is int and total > 0 and 0 <= read <= total:
                            result['restoreComponentPercent'] = 100 * read / total
                        else:
                            result['failures'].append('RESTORE_PROGRESS_INVALID')
                else:
                    result['failures'].append('RESTORE_PROGRESS_MISSING')
            except (OSError, ValueError, TypeError): result['failures'].append('MAINTENANCE_EVIDENCE_UNREADABLE')
            result['checkedAt'] = time.time()
            return result
        gate=evaluate_rpc_gate('http://127.0.0.1:18545',reference,timeout_seconds=4)
        result.update({k:v for k,v in gate.items() if k not in ('failures','status')})
        result['failures']+=gate['failures']
        peers=height(rpc_query('http://127.0.0.1:18545','net_peerCount',[],4))
        result['peerCount']=peers
        if peers<1:result['failures'].append('NO_BOR_PEERS')
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


def cloudwatch_metrics(result, node_name):
    """Missing disk measurements never become zero-usage measurements."""
    metrics=[{'MetricName':'Ready','Value':int(result['status']=='PASS'),'Unit':'Count'},
             {'MetricName':'DiskTelemetryHealthy','Value':int('diskUsedPercent' in result),'Unit':'Count'}]
    if 'diskUsedPercent' in result:
        metrics.append({'MetricName':'DiskUsedPercent','Value':result['diskUsedPercent'],'Unit':'Percent'})
    if 'diskFreeGiB' in result:
        metrics.append({'MetricName':'DiskFreeGiB','Value':result['diskFreeGiB'],'Unit':'Gigabytes'})
    if result.get('restoreProgressAgeSeconds') is not None:
        metrics.append({'MetricName':'RestoreProgressAgeSeconds',
                        'Value':max(0, result['restoreProgressAgeSeconds']),'Unit':'Seconds'})
    if 'restoreComponentPercent' in result:
        metrics.append({'MetricName':'RestoreComponentPercent',
                        'Value':result['restoreComponentPercent'],'Unit':'Percent'})
    for row in metrics:row['Dimensions']=[{'Name':'Node','Value':node_name}]
    return metrics


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
    boto3.client('cloudwatch',region_name=settings['region'],config=cfg).put_metric_data(
        Namespace='OMEGA/PolygonNode',MetricData=cloudwatch_metrics(result,settings['nodeName']))


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--settings',default='/etc/omega-polygon/settings.json')
    p.add_argument('--heimdall-only',action='store_true')
    p.add_argument('--bor-start-allowed',action='store_true')
    args=p.parse_args()
    if args.heimdall_only:
        try:return 0 if heimdall_ready(read_heimdall()) else 1
        except Exception:return 1
    if args.bor_start_allowed:
        try:return 0 if bor_start_allowed(read_heimdall()) else 1
        except Exception:return 1
    settings=json.loads(pathlib.Path(args.settings).read_text())
    # A one-shot timer retries while Heimdall is catching up. Bor starts only
    # after this check passes; its systemd precondition repeats at every restart.
    try:
        if bor_start_allowed(read_heimdall()):
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
