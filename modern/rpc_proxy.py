#!/usr/bin/env python3
"""Bounded, read-only HTTP/WebSocket RPC gateway for the private node.

Bor's privileged RPC binds to loopback. Security groups restrict this gateway
to named consumer security groups. Readiness is continuously fail-closed.
"""
from __future__ import annotations

import argparse
import asyncio
import ipaddress
import json
import pathlib
import time

from aiohttp import ClientSession, ClientTimeout, TCPConnector, WSMsgType, web

READ_METHODS = frozenset({
    'web3_clientVersion','net_version','net_listening','net_peerCount',
    'eth_chainId','eth_blockNumber','eth_syncing','eth_call','eth_estimateGas',
    'eth_getBalance','eth_getCode','eth_getStorageAt','eth_getTransactionCount',
    'eth_getBlockByNumber','eth_getBlockByHash','eth_getTransactionByHash',
    'eth_getTransactionReceipt','eth_getLogs','eth_gasPrice','eth_maxPriorityFeePerGas',
    'eth_feeHistory','eth_getProof','eth_getBlockReceipts',
})
MAX_BATCH=50
MAX_BODY=2*1024*1024
MAX_RESPONSE=32*1024*1024


def validate_request(row, *, websocket=False):
    if not isinstance(row,dict) or row.get('jsonrpc')!='2.0':
        raise ValueError('INVALID_REQUEST')
    if type(row.get('id')) not in (int,str) or not isinstance(row.get('params'),list):
        raise ValueError('ID_AND_POSITIONAL_PARAMS_REQUIRED')
    method=row.get('method')
    params=row['params']
    if websocket and method=='eth_subscribe':
        if not params or params[0] not in ('newHeads','logs') or len(params)>2:
            raise ValueError('SUBSCRIPTION_NOT_ALLOWED')
        if len(params)==2 and (params[0]!='logs' or not isinstance(params[1],dict)):
            raise ValueError('INVALID_SUBSCRIPTION_FILTER')
        return
    if websocket and method=='eth_unsubscribe':
        if len(params)!=1 or not isinstance(params[0],str):
            raise ValueError('INVALID_UNSUBSCRIBE')
        return
    if method not in READ_METHODS:
        raise ValueError('METHOD_NOT_ALLOWED')
    if method=='eth_getLogs':
        if len(params)!=1 or not isinstance(params[0],dict):
            raise ValueError('INVALID_LOG_FILTER')
        filt=params[0]
        if 'blockHash' in filt:
            if 'fromBlock' in filt or 'toBlock' in filt:
                raise ValueError('AMBIGUOUS_LOG_FILTER')
            if not isinstance(filt['blockHash'],str) or len(filt['blockHash'])!=66:
                raise ValueError('INVALID_BLOCK_HASH')
        else:
            try:
                start,end=(int(filt[k],16) for k in ('fromBlock','toBlock'))
            except (ValueError,KeyError,TypeError):
                raise ValueError('EXPLICIT_LOG_WINDOW_REQUIRED') from None
            if start<0 or end<start or end-start>=2000:
                raise ValueError('LOG_WINDOW_LIMIT')
    if method=='eth_feeHistory':
        try:
            if not 1<=int(params[0],16)<=1024: raise ValueError()
        except (ValueError,TypeError,IndexError):
            raise ValueError('FEE_HISTORY_LIMIT') from None


def validate_payload(payload, *, websocket=False):
    rows=payload if isinstance(payload,list) else [payload]
    if not 1<=len(rows)<=MAX_BATCH:
        raise ValueError('BATCH_LIMIT')
    for row in rows:
        validate_request(row,websocket=websocket)
    return len(rows)


def is_ready(path, *, now=None):
    try:
        data=json.loads(pathlib.Path(path).read_text())
        age=(time.time() if now is None else now)-data['checkedAt']
        return data['status']=='PASS' and 0<=age<=30
    except (OSError,ValueError,TypeError,KeyError):
        return False


def create_app(readiness_path, upstream_http='http://127.0.0.1:18545',
               upstream_ws='http://127.0.0.1:18546'):
    app=web.Application(client_max_size=MAX_BODY)
    semaphore=asyncio.Semaphore(64)
    sockets=set()
    # Aggregate limit and concurrency bound prevent unbounded per-IP state.
    tokens=400.0
    tick=time.monotonic()

    def admit(weight):
        nonlocal tokens,tick
        now=time.monotonic()
        tokens=min(400.0,tokens+(now-tick)*200)
        tick=now
        if tokens<weight:return False
        tokens-=weight
        return True

    async def lifecycle(app):
        session=ClientSession(timeout=ClientTimeout(total=15),connector=TCPConnector(limit=80))
        app[SESSION]=session
        yield
        for ws in tuple(sockets):await ws.close(code=1012)
        await session.close()

    async def health(request):
        ready=is_ready(readiness_path)
        return web.json_response({'status':'PASS' if ready else 'SYNCING_OR_UNAVAILABLE'},
            status=200 if request.path=='/healthz' or ready else 503)

    async def handle(request):
        if request.headers.get('Origin'):
            raise web.HTTPForbidden(text='BROWSER_ORIGIN_NOT_ALLOWED')
        if not is_ready(readiness_path):
            raise web.HTTPServiceUnavailable(text='NODE_NOT_READY')
        if request.headers.get('Upgrade','').lower()=='websocket':
            return await websocket(request)
        if request.method!='POST':raise web.HTTPMethodNotAllowed(request.method,['POST'])
        try:
            payload=await request.json()
            weight=validate_payload(payload)
        except (ValueError,TypeError):
            return web.json_response({'jsonrpc':'2.0','id':None,'error':{'code':-32600,'message':'REQUEST_REJECTED'}},status=400)
        if not admit(weight) or semaphore.locked():raise web.HTTPTooManyRequests(text='CAPACITY_LIMIT')
        try:
            async with semaphore:
                async with app[SESSION].post(upstream_http,json=payload) as response:
                    response.raise_for_status()
                    data=bytearray()
                    async for chunk in response.content.iter_chunked(65536):
                        data.extend(chunk)
                        if len(data)>MAX_RESPONSE:raise ValueError('RESPONSE_LIMIT')
                    json.loads(data)
                    if not is_ready(readiness_path):raise ValueError('READINESS_LOST')
                    return web.Response(body=bytes(data),content_type='application/json')
        except Exception:
            # Never echo upstream exception text, endpoints, or calldata.
            raise web.HTTPBadGateway(text='UPSTREAM_UNAVAILABLE') from None

    async def websocket(request):
        if len(sockets)>=16 or not admit(1):raise web.HTTPTooManyRequests(text='SOCKET_LIMIT')
        client=web.WebSocketResponse(max_msg_size=MAX_BODY,heartbeat=20)
        await client.prepare(request)
        sockets.add(client)
        try:
            async with app[SESSION].ws_connect(upstream_ws,heartbeat=20,max_msg_size=MAX_RESPONSE) as upstream:
                async def outbound():
                    subscriptions=0
                    async for msg in client:
                        if msg.type!=WSMsgType.TEXT:break
                        payload=json.loads(msg.data)
                        weight=validate_payload(payload,websocket=True)
                        rows=payload if isinstance(payload,list) else [payload]
                        subscriptions+=sum(r['method']=='eth_subscribe' for r in rows)
                        if subscriptions>32 or not admit(weight) or not is_ready(readiness_path):break
                        await upstream.send_str(msg.data)
                async def inbound():
                    async for msg in upstream:
                        if msg.type!=WSMsgType.TEXT or not is_ready(readiness_path):break
                        await client.send_str(msg.data)
                async def watchdog():
                    while is_ready(readiness_path):await asyncio.sleep(2)
                tasks=[asyncio.create_task(f()) for f in (outbound,inbound,watchdog)]
                try:
                    await asyncio.wait(tasks,return_when=asyncio.FIRST_COMPLETED)
                finally:
                    for task in tasks:task.cancel()
                    await asyncio.gather(*tasks,return_exceptions=True)
        except Exception:
            pass
        finally:
            sockets.discard(client)
            await client.close(code=1012,message=b'RECONNECT_AND_REVALIDATE')
        return client

    app.cleanup_ctx.append(lifecycle)
    app.router.add_get('/healthz',health)
    app.router.add_get('/readyz',health)
    app.router.add_route('*','/',handle)
    return app


SESSION=web.AppKey('session',ClientSession)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--bind',required=True)
    p.add_argument('--readiness',default='/run/omega-polygon/readiness.json')
    args=p.parse_args()
    ip=ipaddress.ip_address(args.bind)
    if not ip.is_private or ip.is_unspecified:raise SystemExit('PRIVATE_BIND_REQUIRED')
    web.run_app(create_app(args.readiness),host=args.bind,port=8545,access_log=None)


if __name__=='__main__':main()
