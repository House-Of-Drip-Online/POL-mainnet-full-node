#!/usr/bin/env python3
"""Bounded full-history restore, isolated from the active Bor database.

Pinned TLS object identity and locally measured SHA256 are transport evidence,
not chain certification. The normal native-client and independent RPC gates
remain mandatory after promotion. No consensus or pruning metadata is edited.
"""
from __future__ import annotations
import argparse
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import os
import re
from urllib.parse import urlsplit
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile
import threading
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent
WORK = Path('/data/bor/full-restore')
MAINTENANCE = Path('/etc/omega-polygon/maintenance.json')


def atomic_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    with temporary.open('w') as file:
        json.dump(value, file, sort_keys=True); file.flush(); os.fsync(file.fileno())
    temporary.chmod(0o644); temporary.replace(path)


class RangeReader(io.RawIOBase):
    """Ordered stream: workers pending ranges plus one current range at most."""
    def __init__(self, spec, *, workers=8, chunk_bytes=64*1024*1024):
        super().__init__()
        if not 1 <= workers <= 8 or chunk_bytes < 1:
            raise ValueError('INVALID_DOWNLOAD_BOUNDS')
        self.spec = spec; self.chunk_bytes = chunk_bytes
        self.pool = ThreadPoolExecutor(max_workers=workers)
        self.next_start = 0; self.pending = deque(); self.current = memoryview(b'')
        self.peak_pending = 0
        for _ in range(workers): self.submit()

    def submit(self):
        start = self.next_start
        if start >= self.spec['compressedBytes']: return
        end = min(start + self.chunk_bytes, self.spec['compressedBytes']) - 1
        self.next_start = end + 1
        self.pending.append(self.pool.submit(self.fetch, start, end))
        self.peak_pending = max(self.peak_pending, len(self.pending))

    def fetch(self, start, end):
        size = end - start + 1
        for attempt in range(5):
            try:
                request = urllib.request.Request(self.spec['url'], headers={
                    'User-Agent': 'OMEGA-PolygonNode/1.0', 'If-Match': self.spec['etag'],
                    'Range': f'bytes={start}-{end}'})
                with urllib.request.urlopen(request, timeout=120) as response:
                    if (not response.url.startswith('https://') or response.status != 206
                        or response.headers.get('ETag') != self.spec['etag']
                        or response.headers.get('Content-Length') != str(size)
                        or response.headers.get('Content-Range') !=
                           f'bytes {start}-{end}/{self.spec["compressedBytes"]}'):
                        raise ValueError('FULL_SNAPSHOT_RANGE_IDENTITY_MISMATCH')
                    data = response.read(size + 1)
                    if len(data) != size: raise OSError('FULL_SNAPSHOT_SHORT_RANGE')
                    return data
            except urllib.error.HTTPError as error:
                if error.code not in (408, 429, 500, 502, 503, 504): raise
                if attempt == 4: raise
            except OSError:
                if attempt == 4: raise
            time.sleep(min(2**attempt, 8))

    def readable(self): return True

    def readinto(self, buffer):
        if not self.current:
            if not self.pending: return 0
            self.current = memoryview(self.pending.popleft().result())
            self.submit()
        count = min(len(buffer), len(self.current))
        buffer[:count] = self.current[:count]
        self.current = self.current[count:]
        return count

    def close(self):
        if not self.closed:
            for future in self.pending: future.cancel()
            self.pool.shutdown(wait=True, cancel_futures=True)
        super().close()


def extract_resumable(stream, destination, max_bytes):
    """Resume only byte-identical completed members; never import foreign paths."""
    destination = Path(destination)
    total = count = 0
    with tarfile.open(fileobj=stream, mode='r|') as archive:
        for member in archive:
            count += 1
            name = PurePosixPath(member.name)
            if (count > 1000000 or name.is_absolute() or '..' in name.parts
                or not name.is_relative_to(PurePosixPath('bor/chaindata'))
                or not (member.isdir() or member.isreg())
                or any(p in ('nodekey', 'node_key.json', 'priv_validator_key.json') for p in name.parts)):
                raise ValueError('UNSAFE_FULL_SNAPSHOT_MEMBER')
            total += member.size
            if total > max_bytes: raise ValueError('FULL_SNAPSHOT_EXPANSION_LIMIT')
            target = destination.joinpath(*name.parts)
            # Reject pre-existing links even though our extractor never creates them.
            for parent in (target, *target.parents):
                if parent == destination.parent: break
                if parent.is_symlink(): raise ValueError('FULL_SNAPSHOT_LOCAL_SYMLINK')
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True, mode=0o700); continue
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with archive.extractfile(member) as source:
                if target.exists():
                    if not target.is_file() or target.stat().st_size != member.size:
                        raise ValueError('EXISTING_FILE_DIFFERS')
                    with target.open('rb') as previous:
                        while data := source.read(1024*1024):
                            if data != previous.read(len(data)):
                                raise ValueError('EXISTING_FILE_DIFFERS')
                else:
                    temporary = target.with_name(target.name + '.omega-part')
                    if temporary.is_symlink(): raise ValueError('FULL_SNAPSHOT_LOCAL_SYMLINK')
                    with temporary.open('wb') as output:
                        shutil.copyfileobj(source, output, 1024*1024)
                        output.flush(); os.fsync(output.fileno())
                    if temporary.stat().st_size != member.size:
                        raise ValueError('FULL_SNAPSHOT_MEMBER_INCOMPLETE')
                    temporary.chmod(0o600); temporary.replace(target)
    return {'files': count, 'uncompressedBytes': total}


def file_digest(path):
    with Path(path).open('rb') as file: return hashlib.file_digest(file, 'sha256').hexdigest()


def merge_database(source, destination, on_item=None):
    """Same-filesystem moves; conflicting base/increment bytes stop promotion."""
    source = Path(source); destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    for item in source.iterdir():
        target = destination/item.name
        if item.is_symlink() or target.is_symlink(): raise ValueError('FULL_SNAPSHOT_LOCAL_SYMLINK')
        if item.is_dir(): merge_database(item, target, on_item)
        elif target.exists():
            if target.stat().st_size != item.stat().st_size or file_digest(target) != file_digest(item):
                raise ValueError('FULL_SNAPSHOT_COMPONENT_OVERLAP')
            item.unlink()  # An independently byte-verified duplicate only.
        else: item.rename(target)
        if on_item: on_item()



def validate_snapshot_plan(lock):
    """Reject overlapping/missing block ranges or unbounded transport objects."""
    if not isinstance(lock, dict) or lock.get('chainId') != 137:
        raise ValueError('FULL_SNAPSHOT_CHAIN_MISMATCH')
    components = lock.get('components')
    if not isinstance(components, list) or not 2 <= len(components) <= 16:
        raise ValueError('FULL_SNAPSHOT_COMPONENTS_INVALID')
    previous_end = -1
    names = set()
    for spec in components:
        if not isinstance(spec, dict):
            raise ValueError('FULL_SNAPSHOT_COMPONENT_INVALID')
        name = spec.get('name')
        if (not isinstance(name, str)
            or not re.fullmatch(r'[a-z][a-z0-9_-]{0,60}', name)
            or name in names):
            raise ValueError('FULL_SNAPSHOT_COMPONENT_ID_INVALID')
        names.add(name)
        start, end = spec.get('firstBlock'), spec.get('lastBlock')
        if (type(start) is not int or type(end) is not int
            or start != previous_end + 1 or end < start):
            raise ValueError('FULL_SNAPSHOT_BLOCK_RANGE_GAP_OR_OVERLAP')
        previous_end = end
        compressed, upper = spec.get('compressedBytes'), spec.get('maxUncompressedBytes')
        if (type(compressed) is not int or type(upper) is not int
            or not 0 < compressed <= 16 * 1024**4
            or not 0 < upper <= 16 * 1024**4):
            raise ValueError('FULL_SNAPSHOT_SIZE_BOUNDS_INVALID')
        url = spec.get('url')
        if not isinstance(url, str):
            raise ValueError('FULL_SNAPSHOT_URL_INVALID')
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
            raise ValueError('FULL_SNAPSHOT_URL_INVALID')
        etag = spec.get('etag')
        if not isinstance(etag, str) or len(etag) < 4 or not etag.startswith('"') or not etag.endswith('"'):
            raise ValueError('FULL_SNAPSHOT_ETAG_INVALID')
    return {'rangeStart': 0, 'rangeEnd': previous_end, 'components': len(components)}


def verify_ancient_layout(database):
    """Structural evidence only: contiguous segment families and Pebble manifest."""
    database = Path(database)
    current = database / 'CURRENT'
    if not current.is_file() or current.is_symlink() or not 0 < current.stat().st_size <= 128:
        raise ValueError('FULL_SNAPSHOT_DATABASE_CURRENT_MISSING')
    manifest_name = current.read_text(encoding='ascii').strip()
    if not re.fullmatch(r'MANIFEST-[0-9]{1,20}', manifest_name):
        raise ValueError('FULL_SNAPSHOT_MANIFEST_POINTER_INVALID')
    manifest = database / manifest_name
    if not manifest.is_file() or manifest.is_symlink() or manifest.stat().st_size == 0:
        raise ValueError('FULL_SNAPSHOT_MANIFEST_MISSING')
    directory = database / 'ancient' / 'chain'
    if not directory.is_dir() or directory.is_symlink():
        raise ValueError('FULL_SNAPSHOT_ANCIENT_DIRECTORY_MISSING')
    segments = {}
    for family in ('bodies', 'headers', 'receipts'):
        indices = []
        pattern = re.compile(re.escape(family) + r'\.(\d{4,6})\.cdat')
        for file in directory.glob(family + '.*.cdat'):
            match = pattern.fullmatch(file.name)
            if not match or file.is_symlink() or not file.is_file():
                raise ValueError('FULL_SNAPSHOT_ANCIENT_SEGMENT_INVALID')
            number = int(match.group(1))
            if number > 100000:
                raise ValueError('FULL_SNAPSHOT_ANCIENT_SEGMENT_UNBOUNDED')
            indices.append(number)
        if not indices or len(set(indices)) != len(indices):
            raise ValueError('FULL_SNAPSHOT_ANCIENT_FAMILY_MISSING')
        maximum = max(indices)
        if min(indices) != 0 or len(indices) != maximum + 1:
            raise ValueError('FULL_SNAPSHOT_ANCIENT_SEGMENT_GAP')
        segments[family] = {'first': 0, 'last': maximum, 'count': len(indices)}
    return {'manifest': manifest_name, 'ancient_segments': segments,
            'authority': 'STRUCTURAL_ONLY_NATIVE_CHAIN_PROOF_REQUIRED'}


def restore_component(spec, stage, progress_path, prefix_completed):
    marker = stage/'complete.json'
    identity = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()
    if marker.exists():
        record = json.loads(marker.read_text())
        if record['identity'] != identity: raise ValueError('FULL_SNAPSHOT_COMPONENT_IDENTITY_CHANGED')
        return record
    stage.mkdir(parents=True, exist_ok=True, mode=0o700)
    errors = []; digest = hashlib.sha256(); consumed = 0
    started = time.monotonic(); last = started
    proc = subprocess.Popen(['lz4', '-dc'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL)
    def pump():
        nonlocal consumed, last
        try:
            with RangeReader(spec) as raw, io.BufferedReader(raw, buffer_size=1024*1024) as reader:
                while data := reader.read(8*1024*1024):
                    proc.stdin.write(data); digest.update(data); consumed += len(data)
                    now = time.monotonic()
                    if now - last >= 20:
                        progress = {'status': 'RESTORING', 'component': spec['name'],
                            'compressedBytesRead': consumed, 'componentBytes': spec['compressedBytes'],
                            'completedComponentsBytes': prefix_completed,
                            'bytesPerSecond': int(consumed/(now-started)), 'checkedAt': time.time(),
                            'executionAuthorized': False, 'canonicalStateVerified': False}
                        atomic_json(progress_path, progress)
                        print(json.dumps(progress, sort_keys=True), flush=True); last = now
        except BaseException as error: errors.append(error)
        finally:
            try: proc.stdin.close()
            except BrokenPipeError: pass
    worker = threading.Thread(target=pump); worker.start()
    try:
        extracted = extract_resumable(proc.stdout, stage, spec['maxUncompressedBytes'])
        while proc.stdout.read(1024*1024): pass
        worker.join()
        if errors: raise errors[0]
        if proc.wait() != 0 or consumed != spec['compressedBytes']:
            raise ValueError('FULL_SNAPSHOT_COMPRESSION_OR_SIZE_FAILURE')
    except BaseException:
        proc.kill(); proc.wait(); worker.join(); raise
    record = {'identity': identity, 'url': spec['url'], 'etag': spec['etag'],
              'compressedBytes': consumed, 'sha256': digest.hexdigest(), **extracted,
              'completedAt': time.time(), 'canonicalStateVerified': False}
    atomic_json(marker, record)
    return record


def restore(lock):
    validate_snapshot_plan(lock)
    identity = hashlib.sha256(json.dumps(lock, sort_keys=True).encode()).hexdigest()
    stage = WORK/identity
    stage.mkdir(parents=True, exist_ok=True, mode=0o700)
    final = stage/'restored.json'
    if final.exists(): return json.loads(final.read_text())
    required = sum(s['maxUncompressedBytes'] for s in lock['components'])
    # Existing component bytes are already part of this requirement.
    allocated = sum(p.stat().st_size for p in stage.rglob('*') if p.is_file())
    if shutil.disk_usage(WORK).free < max(0, required-allocated) + 200*1024**3:
        raise ValueError('FULL_SNAPSHOT_CAPACITY_INSUFFICIENT')
    records = []; done = 0
    for spec in lock['components']:
        records.append(restore_component(spec, stage/spec['name'], WORK/'progress.json', done))
        done += spec['compressedBytes']
    combined = stage/'combined'
    progress_path = WORK/'progress.json'
    state = {'status': 'MERGING', 'checkedAt': time.time(), 'processedEntries': 0,
             'canonicalStateVerified': False, 'executionAuthorized': False}
    atomic_json(progress_path, state)
    last_report = [time.monotonic()]
    def report_item():
        state['processedEntries'] += 1
        now = time.monotonic()
        if now - last_report[0] >= 20:
            state['checkedAt'] = time.time()
            atomic_json(progress_path, state)
            last_report[0] = now
    for spec in lock['components']:
        merge_database(stage/spec['name']/'bor/chaindata', combined, report_item)
    layout = verify_ancient_layout(combined)
    record = {'schema': 'omega.bor.full-restore.v1', 'identity': identity,
              'database': str(combined), 'components': records, 'structuralEvidence': layout,
              'completedAt': time.time(),
              'canonicalStateVerified': False, 'executionAuthorized': False}
    atomic_json(final, record)
    atomic_json(WORK/'progress.json', {'status': 'RESTORED_PENDING_NATIVE_VALIDATION',
        'checkedAt': time.time(), 'compressedBytesRead': done, 'executionAuthorized': False})
    return record


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--worker', action='store_true')
    args = parser.parse_args()
    lock = json.loads((ROOT/'full-snapshot-lock.json').read_text())
    validate_snapshot_plan(lock)
    if args.worker:
        restore(lock); return
    if os.geteuid() != 0: raise ValueError('PROMOTION_REQUIRES_HOST_ROOT')
    identity = hashlib.sha256(json.dumps(lock, sort_keys=True).encode()).hexdigest()
    target = Path('/data/bor/data/bor/chaindata')
    promoted_marker = target/'.omega-full-snapshot.json'
    if promoted_marker.exists() and json.loads(promoted_marker.read_text()).get('identity') == identity:
        # A completed boot service must never rotate a promoted database again.
        if MAINTENANCE.exists() and json.loads(MAINTENANCE.read_text()).get('reason') == 'BOR_FULL_RESTORE_PENDING':
            MAINTENANCE.unlink()
        return
    if not MAINTENANCE.exists(): raise ValueError('EXPLICIT_RESTORE_MAINTENANCE_REQUIRED')
    maintenance = json.loads(MAINTENANCE.read_text())
    if maintenance.get('reason') != 'BOR_FULL_RESTORE_PENDING':
        raise ValueError('MAINTENANCE_OWNERSHIP_CONFLICT')
    subprocess.run(['systemctl', 'stop', 'bor.service'], check=True)
    WORK.mkdir(parents=True, exist_ok=True)
    subprocess.run(['chown', 'bor:nogroup', str(WORK)], check=True)
    subprocess.run(['runuser', '-u', 'bor', '--', '/usr/bin/python3', str(ROOT/'full_snapshot.py'), '--worker'], check=True)
    record = json.loads((WORK/identity/'restored.json').read_text())
    source = WORK/identity/'combined'
    if record['identity'] != identity or record['database'] != str(source):
        raise ValueError('RESTORE_PROMOTION_IDENTITY_MISMATCH')
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists(): target.rename(target.with_name('chaindata.rejected-'+str(time.time_ns())))
    source.rename(target)
    for path in (target.parent, target.parent.parent):
        subprocess.run(['chown', 'bor:nogroup', str(path)], check=True)
    atomic_json(target/'.omega-full-snapshot.json', record)
    # Never clear a maintenance condition installed by another operator.
    if json.loads(MAINTENANCE.read_text()) != maintenance:
        raise ValueError('MAINTENANCE_CHANGED_DURING_RESTORE')
    MAINTENANCE.unlink()
    subprocess.run(['systemctl', 'start', 'omega-monitor.timer'], check=True)
    subprocess.run(['systemctl', 'start', '--no-block', 'bor.service'], check=True)


if __name__ == '__main__':
    try: main()
    except Exception as error:
        print(json.dumps({'event': 'FULL_RESTORE_FAILED', 'type': type(error).__name__,
                          'reason': str(error), 'executionAuthorized': False}), flush=True)
        raise SystemExit(1) from None
