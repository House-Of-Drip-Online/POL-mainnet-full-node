import asyncio
import json
import pathlib
import sys
import tempfile
import time
import unittest

from aiohttp import ClientSession, WSMsgType, web

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from rpc_proxy import create_app


class GatewayIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.ready=pathlib.Path(self.directory.name)/'ready.json'
        self.ready.write_text(json.dumps({'status':'PASS','checkedAt':time.time()}))
        self.received=[]
        async def upstream(request):
            if request.headers.get('Upgrade','').lower()=='websocket':
                socket=web.WebSocketResponse()
                await socket.prepare(request)
                async for message in socket:
                    if message.type==WSMsgType.TEXT:
                        row=json.loads(message.data);self.received.append(row)
                        await socket.send_json({'jsonrpc':'2.0','id':row['id'],'result':'0xsubscription'})
                return socket
            row=await request.json();self.received.append(row)
            return web.json_response({'jsonrpc':'2.0','id':row['id'],'result':'0x89'})
        backend=web.Application();backend.router.add_route('*','/',upstream)
        self.backend=web.AppRunner(backend);await self.backend.setup()
        site=web.TCPSite(self.backend,'127.0.0.1',0);await site.start()
        self.upstream_url='http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1])
        self.proxy=web.AppRunner(create_app(self.ready,self.upstream_url,self.upstream_url));await self.proxy.setup()
        site=web.TCPSite(self.proxy,'127.0.0.1',0);await site.start()
        self.url='http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1])
        self.session=ClientSession()

    async def asyncTearDown(self):
        await self.session.close();await self.proxy.cleanup();await self.backend.cleanup()
        self.directory.cleanup()

    async def test_http_read_and_mixed_batch_rejection(self):
        read={'jsonrpc':'2.0','id':1,'method':'eth_chainId','params':[]}
        async with self.session.post(self.url,json=read) as response:
            self.assertEqual(response.status,200)
            self.assertEqual((await response.json())['result'],'0x89')
        forbidden={**read,'method':'eth_sendRawTransaction','params':['0x01']}
        async with self.session.post(self.url,json=[read,forbidden]) as response:
            self.assertEqual(response.status,400)
        self.assertEqual(self.received,[read])

    async def test_expired_health_blocks_traffic(self):
        self.ready.write_text(json.dumps({'status':'PASS','checkedAt':time.time()-31}))
        async with self.session.post(self.url,json={}) as response:self.assertEqual(response.status,503)
        self.assertEqual(self.received,[])

    async def test_websocket_closes_on_lost_readiness(self):
        async with self.session.ws_connect(self.url) as socket:
            await socket.send_json({'jsonrpc':'2.0','id':1,'method':'eth_subscribe','params':['newHeads']})
            response=await socket.receive(timeout=3)
            self.assertEqual(json.loads(response.data)['result'],'0xsubscription')
            self.ready.write_text(json.dumps({'status':'FAIL','checkedAt':time.time()}))
            response=await socket.receive(timeout=4)
            self.assertIn(response.type,(WSMsgType.CLOSE,WSMsgType.CLOSED))


if __name__=='__main__':unittest.main()
