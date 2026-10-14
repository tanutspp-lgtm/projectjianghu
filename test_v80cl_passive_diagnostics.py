"""v8.0CL diagnostic tests; no production credentials/network involved."""
import asyncio, contextlib, io, json, os, subprocess, sys, time, unittest
import websockets
import server

class TestRenderDiag(unittest.TestCase):
    def test_anonymous_rollup_and_reset(self):
        previous = (server._diag_last,server._diag_process_cpu,server._diag_sent,server._diag_overwritten)
        buf=io.StringIO()
        try:
            server._diag_last=time.monotonic()-16
            server._diag_sent=15
            server._diag_overwritten=3
            server._diag_send_durations.extend([1,2,5])
            with contextlib.redirect_stdout(buf):server.report_performance_to_render(time.monotonic())
            raw=buf.getvalue().strip()
            self.assertTrue(raw.startswith('JIANGHU_DIAG '))
            d=json.loads(raw[len('JIANGHU_DIAG '):])
            self.assertEqual(d['snapSent'],15)
            self.assertEqual(d['snapOverwritten'],3)
            self.assertEqual(d['wsSendMaxMs'],5)
            for k in ['browserCount','guests','tickP95Ms','loopP95Ms','encodeP95Ms','cpuCorePct','boot','ts']:
                self.assertIn(k,d)
            self.assertFalse(any(k in d for k in ('id','name','ip','x','y','avatar','inventory')))
            self.assertEqual(server._diag_sent,0)
            self.assertEqual(server._diag_overwritten,0)
        finally:
            server._diag_last,server._diag_process_cpu,server._diag_sent,server._diag_overwritten=previous
            server._diag_send_durations.clear()

    def test_client_perf_protocol_does_not_interrupt_inputs(self):
        async def client(port):
            async with websockets.connect(f'ws://127.0.0.1:{port}/ws',max_size=2_000_000) as ws:
                await ws.send(json.dumps({'t':'join','avatar':'male_hair_01_black','protocol':'aoi-delta-v80by'}))
                w=json.loads(await asyncio.wait_for(ws.recv(),3))
                self.assertIn('client-perf-v80cl',w['features'])
                await ws.send(json.dumps({'t':'client_perf','fps':165,'pingMs':47,'gapP95Ms':103.1,'gapMaxMs':284,'frameMs':6.1}))
                await ws.send(json.dumps({'t':'input','seq':1,'buttons':2,'pressed':[]}))
                await ws.send(json.dumps({'t':'ping','nonce':1234}))
                for _ in range(20):
                    msg=json.loads(await asyncio.wait_for(ws.recv(),3))
                    if msg['t']=='pong':
                        self.assertEqual(msg['nonce'],1234)
                        return
                self.fail('input/ping failed after telemetry')
        port=19861
        env={**os.environ,'PORT':str(port),'SUPABASE_URL':'','PYTHONDONTWRITEBYTECODE':'1'}
        proc=subprocess.Popen([sys.executable,'-u','server.py'],cwd=os.path.dirname(__file__),env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        try:
            time.sleep(.85)
            self.assertIsNone(proc.poll(), 'server process died')
            asyncio.run(client(port))
        finally:
            proc.terminate()
            try:proc.wait(3)
            except subprocess.TimeoutExpired:proc.kill()

if __name__=='__main__':unittest.main()
