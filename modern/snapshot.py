#!/usr/bin/env python3
"""Pinned community state bootstrap; transport identity is NOT a signed state proof.

Extract database files only, as the unprivileged client user. Independent chain
corroboration remains mandatory before the gateway admits any request.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile
import time
import urllib.request

ROOT=Path(__file__).resolve().parent


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        while block:=f.read(16*1024*1024):h.update(block)
    return h.hexdigest()


def validate_headers(headers,status,offset,spec):
    if headers.get('ETag')!=spec['etag']:raise ValueError('SNAPSHOT_OBJECT_CHANGED')
    if offset:
        if status!=206:raise ValueError('SNAPSHOT_RESUME_NOT_SUPPORTED')
        expected=f'bytes {offset}-{spec["compressedBytes"]-1}/{spec["compressedBytes"]}'
        if headers.get('Content-Range')!=expected:raise ValueError('SNAPSHOT_RANGE_MISMATCH')
    elif status!=200 or int(headers.get('Content-Length','-1'))!=spec['compressedBytes']:
        raise ValueError('SNAPSHOT_SIZE_MISMATCH')


def fetch(spec,path):
    path=Path(path)
    record=path.with_suffix('.json')
    if path.exists():
        saved=json.loads(record.read_text())
        if saved['etag']!=spec['etag'] or path.stat().st_size!=spec['compressedBytes']:
            raise ValueError('EXISTING_SNAPSHOT_IDENTITY_MISMATCH')
        if digest(path)!=saved['sha256']:raise ValueError('LOCAL_SNAPSHOT_CORRUPTION')
        return saved
    partial=path.with_suffix('.part')
    offset=partial.stat().st_size if partial.exists() else 0
    if offset>spec['compressedBytes']:raise ValueError('SNAPSHOT_PARTIAL_OVERSIZED')
    if offset<spec['compressedBytes']:
        headers={'User-Agent':'Mozilla/5.0','If-Match':spec['etag']}
        if offset:headers['Range']=f'bytes={offset}-'
        request=urllib.request.Request(spec['url'],headers=headers)
        with urllib.request.urlopen(request,timeout=120) as response:
            if not response.url.startswith('https://'):raise ValueError('SNAPSHOT_HTTPS_REQUIRED')
            validate_headers(response.headers,response.status,offset,spec)
            with partial.open('ab' if offset else 'wb') as output:
                last=time.monotonic()
                while block:=response.read(8*1024*1024):
                    offset+=len(block)
                    if offset>spec['compressedBytes']:raise ValueError('SNAPSHOT_DOWNLOAD_OVERSIZED')
                    output.write(block)
                    if time.monotonic()-last>=30:
                        print(json.dumps({'event':'SNAPSHOT_DOWNLOAD','component':spec['component'],
                                          'bytes':offset,'totalBytes':spec['compressedBytes']}),flush=True)
                        last=time.monotonic()
                output.flush();os.fsync(output.fileno())
    if partial.stat().st_size!=spec['compressedBytes']:raise ValueError('SNAPSHOT_DOWNLOAD_INCOMPLETE')
    result={'etag':spec['etag'],'sha256':digest(partial),'bytes':partial.stat().st_size,
            'provenance':'PublicNode community snapshot; locally measured SHA256, not publisher signature',
            'height':spec['height'],'downloadedAt':time.time()}
    # The record precedes the atomic move; an interrupted download can be resumed.
    record.write_text(json.dumps(result,sort_keys=True));record.chmod(0o644)
    partial.chmod(0o644);partial.replace(path)
    return result


def extract_tar(stream,destination,prefix,max_bytes):
    destination=Path(destination)
    root=PurePosixPath(prefix)
    total=0;count=0
    with tarfile.open(fileobj=stream,mode='r|') as archive:
        for member in archive:
            count+=1
            name=PurePosixPath(member.name)
            if (count>1000000 or name.is_absolute() or '..' in name.parts
                or not name.is_relative_to(root) or not (member.isdir() or member.isreg())):
                raise ValueError('UNSAFE_SNAPSHOT_MEMBER')
            total+=member.size
            if total>max_bytes:raise ValueError('SNAPSHOT_EXPANSION_LIMIT')
            # Never import someone else's validator state or keys.
            if name.name in ('priv_validator_state.json','priv_validator_key.json','node_key.json'):
                continue
            target=destination.joinpath(*name.parts)
            if member.isdir():target.mkdir(parents=True,exist_ok=True,mode=0o700)
            else:
                target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
                with target.open('xb') as output,archive.extractfile(member) as source:
                    shutil.copyfileobj(source,output,1024*1024)
                target.chmod(0o600)
    return {'files':count,'uncompressedBytes':total}


def extract(archive,stage,prefix,max_bytes):
    with subprocess.Popen(['lz4','-d','-c',str(archive)],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL) as proc:
        try:result=extract_tar(proc.stdout,stage,prefix,max_bytes)
        except Exception:
            proc.kill();proc.wait();raise
        # Consume trailer to validate the complete compression stream.
        while proc.stdout.read(1024*1024):pass
        if proc.wait()!=0:raise ValueError('LZ4_INTEGRITY_FAILURE')
    return result


def install(component):
    spec=json.loads((ROOT/'snapshot-lock.json').read_text())[component]
    base=Path('/data')/component
    target=base/'data' if component=='heimdall' else base/'data/bor/chaindata'
    marker=target/'.omega-snapshot.json'
    if marker.exists():
        if json.loads(marker.read_text())['etag']!=spec['etag']:raise ValueError('SNAPSHOT_UPGRADE_REQUIRES_REVIEW')
        return
    if target.exists() and any(p.name!='priv_validator_state.json' for p in target.iterdir()):
        raise ValueError('REFUSE_SNAPSHOT_OVER_EXISTING_DATABASE')
    cache=Path('/data/releases')/f'{component}-snapshot.tar.lz4'
    evidence=fetch(spec,cache)
    stage=Path('/data/snapshot-work')/component
    if stage.exists():shutil.rmtree(stage)
    stage.mkdir(parents=True,mode=0o700)
    subprocess.run(['chown',f'{component}:nogroup',str(stage)],check=True)
    subprocess.run(['sudo','-u',component,'/usr/bin/python3',str(ROOT/'snapshot.py'),
                    '--extract',str(cache),'--stage',str(stage),'--prefix',spec['prefix'],
                    '--max-bytes',str(spec['maxUncompressedBytes'])],check=True)
    restored=stage/spec['prefix']
    if not restored.is_dir():raise ValueError('SNAPSHOT_DATABASE_MISSING')
    if component=='heimdall' and target.exists() and (target/'priv_validator_state.json').exists():
        shutil.copy2(target/'priv_validator_state.json',restored/'priv_validator_state.json')
        subprocess.run(['chown','heimdall:nogroup',str(restored/'priv_validator_state.json')],check=True)
    evidence.update({'component':component,'installedAt':time.time(),'canonicalStateVerified':False})
    (restored/'.omega-snapshot.json').write_text(json.dumps(evidence,sort_keys=True))
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():target.rename(target.with_name(target.name+'.pre-snapshot'))
    restored.rename(target)
    # Parents created as root must be writable by the database process.
    for parent in (base,base/'data',base/'data/bor'):
        if parent.exists():subprocess.run(['chown',f'{component}:nogroup',str(parent)],check=True)
    print(json.dumps({'event':'SNAPSHOT_INSTALLED',**evidence}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--extract',required=True)
    parser.add_argument('--stage',required=True)
    parser.add_argument('--prefix',required=True)
    parser.add_argument('--max-bytes',type=int,required=True)
    args=parser.parse_args()
    print(json.dumps(extract(args.extract,args.stage,args.prefix,args.max_bytes)),flush=True)
