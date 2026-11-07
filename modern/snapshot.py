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
from concurrent.futures import ThreadPoolExecutor, as_completed

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


def parallel_download(spec,path,*,chunk_bytes=64*1024*1024,workers=8):
    """Bounded range transfer; every range proves the same pinned object identity."""
    if not 1<=workers<=8 or chunk_bytes<1:raise ValueError('INVALID_DOWNLOAD_CONCURRENCY')
    path=Path(path);parts=path.with_suffix('.chunks');parts.mkdir(exist_ok=True)
    identity=json.dumps({'url':spec['url'],'etag':spec['etag'],
                         'bytes':spec['compressedBytes'],'chunkBytes':chunk_bytes},sort_keys=True)
    manifest=parts/'source.json'
    if manifest.exists() and manifest.read_text()!=identity:raise ValueError('SNAPSHOT_CHUNK_SOURCE_CHANGED')
    manifest.write_text(identity)
    ranges=[(start,min(start+chunk_bytes,spec['compressedBytes'])-1)
            for start in range(0,spec['compressedBytes'],chunk_bytes)]
    def part(item):
        start,end=item;size=end-start+1;target=parts/f'{start}-{end}'
        if target.exists() and target.stat().st_size==size:return size
        for attempt in range(3):
            try:
                req=urllib.request.Request(spec['url'],headers={'User-Agent':'Mozilla/5.0',
                    'If-Match':spec['etag'],'Range':f'bytes={start}-{end}'})
                with urllib.request.urlopen(req,timeout=120) as response:
                    if not response.url.startswith('https://'):raise ValueError('SNAPSHOT_HTTPS_REQUIRED')
                    if (response.status!=206 or response.headers.get('ETag')!=spec['etag']
                        or response.headers.get('Content-Range')!=f'bytes {start}-{end}/{spec["compressedBytes"]}'
                        or int(response.headers.get('Content-Length','-1'))!=size):
                        raise ValueError('SNAPSHOT_RANGE_IDENTITY_MISMATCH')
                    temporary=target.with_suffix('.tmp');written=0
                    with temporary.open('wb') as output:
                        while block:=response.read(min(8*1024*1024,size-written+1)):
                            written+=len(block)
                            if written>size:raise ValueError('SNAPSHOT_RANGE_OVERSIZED')
                            output.write(block)
                        output.flush();os.fsync(output.fileno())
                    if written!=size:raise OSError('SNAPSHOT_RANGE_INCOMPLETE')
                    temporary.replace(target)
                    return size
            except ValueError:raise
            except OSError:
                if attempt==2:raise
                time.sleep(2**attempt)
    total=0;last=time.monotonic()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures=[pool.submit(part,item) for item in ranges]
        try:
            for future in as_completed(futures):
                total+=future.result()
                if time.monotonic()-last>=30:
                    print(json.dumps({'event':'SNAPSHOT_PARALLEL_DOWNLOAD','component':spec['component'],
                        'bytes':total,'totalBytes':spec['compressedBytes'],'connections':workers}),flush=True)
                    last=time.monotonic()
        except Exception:
            for future in futures:future.cancel()
            raise
    assembling=path.with_suffix('.assembling')
    with assembling.open('wb') as output:
        for start,end in ranges:
            with (parts/f'{start}-{end}').open('rb') as source:shutil.copyfileobj(source,output,8*1024*1024)
        output.flush();os.fsync(output.fileno())
    if assembling.stat().st_size!=spec['compressedBytes']:raise ValueError('SNAPSHOT_ASSEMBLY_INCOMPLETE')
    assembling.replace(path)


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
    if spec['component']=='bor' and offset<spec['compressedBytes']:
        parallel_download(spec,partial)
        offset=partial.stat().st_size
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
    chunks=partial.with_suffix('.chunks')
    if chunks.exists():shutil.rmtree(chunks)
    return result


def extract_tar(stream,destination,prefix,max_bytes):
    destination=Path(destination)
    root=PurePosixPath(prefix)
    total=0;count=0
    with tarfile.open(fileobj=stream,mode='r|') as archive:
        for member in archive:
            count+=1
            name=PurePosixPath(member.name)
            # PublicNode includes this regular file at archive root. Keep the
            # locally generated validator state; never restore another identity.
            if name==PurePosixPath('priv_validator_state.json') and member.isreg():
                continue
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
