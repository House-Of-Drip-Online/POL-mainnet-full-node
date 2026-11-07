// Run in an isolated task using Asset Hunter's image and network, without its
// database credentials, application command, runtime role, or producer worker.
const target = process.env.OMEGA_NODE_RPC_URL;
if (!target || !/^http:\/\/10\./.test(target)) throw new Error('PRIVATE_TARGET_REQUIRED');
(async () => {
  const started = performance.now();
  try {
    const response = await fetch(target, {
      method: 'POST', signal: AbortSignal.timeout(10000),
      headers: { 'Content-Type': 'application/json', 'User-Agent': 'OMEGA-PolygonNode/1.0' },
      body: JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'eth_chainId', params: [] }),
    });
    const payload = await response.json();
    const chainVerified = response.ok && payload.id === 1 && payload.result === '0x89';
    console.log(JSON.stringify({ schema: 'omega.node.consumer-network-probe.v1',
      checkedAt: new Date().toISOString(), httpStatus: response.status,
      transportReachable: true, chainVerified, readinessCertified: false,
      latencyMs: Math.round(performance.now() - started), executionAuthorized: false }));
    process.exitCode = chainVerified ? 0 : 2;
  } catch (error) {
    console.log(JSON.stringify({ schema: 'omega.node.consumer-network-probe.v1',
      checkedAt: new Date().toISOString(), transportReachable: false,
      chainVerified: false, readinessCertified: false, executionAuthorized: false,
      errorType: error.name }));
    process.exitCode = 1;
  }
})();
