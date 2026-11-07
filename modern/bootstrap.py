#!/usr/bin/env python3
"""Idempotent first-host bootstrap. Existing disk signatures are never erased."""
from __future__ import annotations
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import urllib.request

ROOT=Path(__file__).resolve().parent


def configure_bor(config):
    config.update({'chain':'mainnet','datadir':'/var/lib/bor/data','syncmode':'snap',
        'gcmode':'full','db.engine':'pebble','state.scheme':'path',
        'rpc.batch-request-limit':50,'rpc.batch-response-max-size':32*1024*1024,
        'rpc.returndatalimit':32*1024*1024})
    config.setdefault('p2p',{}).update({'maxpeers':100,'maxpendpeers':50,'port':30303})
    config.setdefault('miner',{}).update({'mine':False})
    config['heimdall']={'url':'http://127.0.0.1:1317','bor.without':False}
    config['accounts']={'unlock':[],'allow-insecure-unlock':False,'disable-bor-wallet':True}
    config['relay']={'enable-preconfs':False,'enable-private-tx':False}
    config['jsonrpc']={'ipcpath':'/var/lib/bor/bor.ipc','gascap':50000000,
        'evmtimeout':'5s','rangelimit':2000,'logquerylimit':1000,
        'http':{'enabled':True,'port':18545,'host':'127.0.0.1',
                'api':['eth','net','web3','bor','debug'],'vhosts':['localhost','127.0.0.1'],
                'corsdomain':[],'ep-size':64,'ep-requesttimeout':'10s'},
        'ws':{'enabled':True,'port':18546,'host':'127.0.0.1',
              'api':['eth','net','web3'],'origins':['http://localhost']},
        'timeouts':{'read':'15s','write':'20s','idle':'60s'}}
    config['grpc']={'addr':'127.0.0.1:3131'}
    config.setdefault('cache',{}).update({'cache':16384,'gomemlimit':'40GiB'})
    config['history']={'state':90000,'logs':0,'transactions':2350000}
    config['telemetry']={'metrics':True,'prometheus-addr':'127.0.0.1:7071'}
    return config


def configure_heimdall(config,app):
    config['moniker']='omega-polygon-137'
    config.setdefault('p2p',{})['external_address']=''
    config.setdefault('rpc',{}).update({'laddr':'tcp://127.0.0.1:26657','unsafe':False})
    config['pprof_laddr']=''
    config.setdefault('instrumentation',{}).update({'prometheus':True,'prometheus_listen_addr':'127.0.0.1:26660'})
    app.setdefault('api',{}).update({'enable':True,'address':'tcp://127.0.0.1:1317','enabled-unsafe-cors':False})
    app.setdefault('grpc',{})['address']='127.0.0.1:9090'
    app.setdefault('custom',{}).update({'bor_rpc_url':'http://127.0.0.1:18545',
        'comet_bft_rpc_url':'http://127.0.0.1:26657'})
    return config,app


def verify_file(path, expected):
    if not re.fullmatch('[0-9a-f]{64}',expected):raise ValueError('INVALID_SHA256')
    digest=hashlib.sha256()
    with Path(path).open('rb') as f:
        while chunk:=f.read(8*1024*1024):digest.update(chunk)
    if digest.hexdigest()!=expected:raise ValueError('ARTIFACT_HASH_MISMATCH')


def download(artifact, destination):
    destination=Path(destination)
    if destination.exists():
        verify_file(destination,artifact['sha256'])
        return
    if not artifact['url'].startswith('https://'):raise ValueError('HTTPS_REQUIRED')
    destination.parent.mkdir(parents=True,exist_ok=True)
    partial=destination.with_suffix(destination.suffix+'.part')
    # Retry is handled by the bootstrap systemd unit; resume large downloads.
    offset=partial.stat().st_size if partial.exists() else 0
    headers={'Range':f'bytes={offset}-'} if offset else {}
    with urllib.request.urlopen(urllib.request.Request(artifact['url'],headers=headers),timeout=60) as response:
        resumed=offset>0 and response.status==206
        if resumed and not response.headers.get('Content-Range','').startswith(f'bytes {offset}-'):
            raise ValueError('INVALID_DOWNLOAD_RANGE')
        with partial.open('ab' if resumed else 'wb') as f:
            shutil.copyfileobj(response,f,8*1024*1024)
            f.flush();os.fsync(f.fileno())
    verify_file(partial,artifact['sha256'])
    if artifact.get('size') and partial.stat().st_size!=artifact['size']:
        raise ValueError('ARTIFACT_SIZE_MISMATCH')
    partial.chmod(0o644)
    partial.replace(destination)


def run(*args):
    return subprocess.run(args,check=True,text=True,capture_output=True).stdout.strip()


def may_format(info):
    disks=info.get('blockdevices',[])
    return (len(disks)==1 and disks[0].get('type')=='disk'
        and not disks[0].get('fstype') and not disks[0].get('children')
        and not any(disks[0].get('mountpoints') or []))


def mount_volume(volume_id):
    if not re.fullmatch(r'vol-[0-9a-f]{8,17}',volume_id):raise ValueError('INVALID_VOLUME_ID')
    disks=json.loads(run('lsblk','--json','-o','PATH,TYPE,FSTYPE,SERIAL,MOUNTPOINTS'))['blockdevices']
    matches=[x for x in disks if x.get('serial')==volume_id.replace('-','')]
    if len(matches)!=1:raise ValueError('EXPECTED_EBS_VOLUME_NOT_ATTACHED')
    disk=matches[0];device=disk['path']
    signatures=json.loads(run('wipefs','--no-act','--json',device)).get('signatures',[])
    if not signatures and may_format({'blockdevices':[disk]}):
        run('mkfs.xfs','-L','omega-polygon',device)
    elif disk.get('fstype')!='xfs' or disk.get('children'):
        raise ValueError('REFUSE_TO_REFORMAT_EXISTING_DATA')
    uuid=run('blkid','-s','UUID','-o','value',device)
    label=run('blkid','-s','LABEL','-o','value',device)
    if label!='omega-polygon':raise ValueError('VOLUME_OWNERSHIP_LABEL_MISMATCH')
    Path('/data').mkdir(exist_ok=True)
    fstab=Path('/etc/fstab');body=fstab.read_text()
    entry=f'UUID={uuid} /data xfs defaults,noatime 0 2'
    if entry not in body:
        if any(line.split()[1:2]==['/data'] for line in body.splitlines() if not line.startswith('#')):
            raise ValueError('EXISTING_MOUNT_CONFLICT')
        fstab.write_text(body+'\n'+entry+'\n')
    if not os.path.ismount('/data'):run('mount','/data')
    if run('findmnt','-n','-o','UUID','/data')!=uuid:raise ValueError('WRONG_MOUNTED_VOLUME')


def atomic_text(path,text,mode=0o644):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(text);temporary.chmod(mode);temporary.replace(path)


def install(settings):
    import tomlkit
    if os.geteuid()!=0:raise ValueError('HOST_ROOT_REQUIRED')
    if run('dpkg','--print-architecture')!='amd64':raise ValueError('AMD64_REQUIRED')
    mount_volume(settings['volumeId'])
    lock=json.loads((ROOT/'release-lock.json').read_text())
    if lock['chainId']!=137:raise ValueError('CHAIN_MISMATCH')
    for name in ('bor','heimdall'):
        data=Path('/data')/name;data.mkdir(exist_ok=True)
        link=Path('/var/lib')/name
        if not link.exists():link.symlink_to(data,target_is_directory=True)
        if not link.is_symlink() or link.resolve()!=data:raise ValueError('EXISTING_DATA_PATH_CONFLICT')
    cache=Path('/data/releases');cache.mkdir(exist_ok=True)
    marker=Path('/data/.packages-installed')
    fingerprint=hashlib.sha256((ROOT/'release-lock.json').read_bytes()).hexdigest()
    if marker.exists() and marker.read_text()!=fingerprint:raise ValueError('EXPLICIT_RELEASE_UPGRADE_REQUIRED')
    if not marker.exists():
        for component in ('heimdall','bor'):
            for artifact in lock[component]['artifacts']:
                destination=cache/artifact['name']
                download(artifact,destination)
                run('dpkg','-i',str(destination))
        atomic_text(marker,fingerprint)
    genesis=json.loads((ROOT/'genesis-lock.json').read_text())
    genesis_marker=Path('/data/.genesis-installed')
    genesis_path=Path('/var/lib/heimdall/config/genesis.json')
    if not genesis_marker.exists():
        state=Path('/var/lib/heimdall/data')
        if state.exists() and any(p.name!='priv_validator_state.json' for p in state.iterdir()):
            raise ValueError('REFUSE_GENESIS_REPLACEMENT_WITH_EXISTING_CHAIN_DATA')
        download(genesis,cache/'heimdall-genesis.json')
        shutil.copyfile(cache/'heimdall-genesis.json',genesis_path.with_suffix('.new'))
        genesis_path.with_suffix('.new').replace(genesis_path)
        atomic_text(genesis_marker,genesis['sha256'])
    if genesis_marker.read_text()!=genesis['sha256']:raise ValueError('GENESIS_LOCK_CHANGED')
    verify_file(genesis_path,genesis['sha256'])
    bor_path=Path('/var/lib/bor/config.toml')
    bor=configure_bor(tomlkit.parse(bor_path.read_text()))
    atomic_text(bor_path,tomlkit.dumps(bor))
    config_path=Path('/var/lib/heimdall/config/config.toml')
    app_path=Path('/var/lib/heimdall/config/app.toml')
    config,app=configure_heimdall(tomlkit.parse(config_path.read_text()),tomlkit.parse(app_path.read_text()))
    atomic_text(config_path,tomlkit.dumps(config));atomic_text(app_path,tomlkit.dumps(app))
    # Top-level paths only; existing multi-terabyte state is not recursively scanned.
    for name in ('bor','heimdall'):
        run('chown',f'{name}:nogroup',f'/data/{name}')
    for path in (bor_path,config_path,app_path):
        owner='bor' if path==bor_path else 'heimdall'
        run('chown',f'{owner}:nogroup',str(path))
    from snapshot import install as install_snapshot
    for component in ('heimdall','bor'):
        install_snapshot(component)
    ip=ipaddress.ip_address(settings['privateIp'])
    if not ip.is_private or ip.is_unspecified:raise ValueError('PRIVATE_RPC_BIND_REQUIRED')
    for source in (ROOT/'templates').glob('*.service'):
        text=source.read_text().replace('@PRIVATE_IP@',str(ip))
        atomic_text(Path('/etc/systemd/system')/source.name,text)
    for source in (ROOT/'templates').glob('*.timer'):
        atomic_text(Path('/etc/systemd/system')/source.name,source.read_text())
    # Runtime services are deliberately separate from the root installer.
    run('id','omega-rpc')
    Path('/run/omega-polygon').mkdir(mode=0o755,exist_ok=True)
    run('systemctl','daemon-reload')
    run('systemctl','enable','heimdalld.service','omega-rpc.service','omega-monitor.timer')
    run('systemctl','start','heimdalld.service','omega-rpc.service','omega-monitor.timer')
    atomic_text('/data/bootstrap-complete.json',json.dumps({'sourceCommit':settings['sourceCommit'],
        'installedAt':time.time(),'state':'SYNCING','executionAuthorized':False},sort_keys=True))


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--settings',default='/etc/omega-polygon/settings.json')
    args=p.parse_args()
    settings=json.loads(Path(args.settings).read_text())
    try:install(settings)
    except Exception as exc:
        # Commands can contain credentials on other systems; emit type only.
        print(json.dumps({'event':'BOOTSTRAP_FAILED','errorType':type(exc).__name__}),flush=True)
        raise SystemExit(1) from None


if __name__=='__main__':main()
