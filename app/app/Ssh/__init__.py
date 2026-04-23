import asyncio
import aiofiles
import declare
@declare.scope
def Ssh(queueRunner,taskSet,cfg):
  async def tun():
    while 1:
      async with aiofiles.tempfile.TemporaryDirectory()as tmpDirName:
        async with aiofiles.open(f'{tmpDirName}/config','w')as f:
          await f.write('\n'.join(cfg['config']))
        try:
          p=await asyncio.create_subprocess_exec(
            'ssh',
            '-F',f'{tmpDirName}/config',
            '-L',f'{cfg['fromHost']}:{cfg['fromPort']}:{cfg['toHost']}:{cfg['toPort']}',
            '-N',
            '-o','ExitOnForwardFailure=yes',
            '-o','ServerAliveCountMax=3',
            '-o','ServerAliveInterval=15',
            '-o','StrictHostKeyChecking=no',
            cfg['host'],
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
          )
          await p.wait()
        finally:
          if p.returncode is None:
            p.terminate()
            try:
              await asyncio.wait_for(p.wait(),timeout=5)
            except asyncio.TimeoutError:
              p.kill()
              await p.wait()
      await asyncio.sleep(1)
  t=None
  async def _():
    nonlocal t
    t=taskSet.create_task(tun())
  queueRunner.put(_())
  yield
  async def _():
    t.cancel()
    await asyncio.gather(t,return_exceptions=True)
  queueRunner.put(_())
