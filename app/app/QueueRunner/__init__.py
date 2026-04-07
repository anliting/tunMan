import asyncio
class QueueRunner:
  def __init__(self):
    self._q=asyncio.Queue()
    async def _():
      while 1:
        c,f=await self._q.get()
        try:
          f.set_result(await c)
        except Exception as e:
          f.set_exception(e)
    self._runner=asyncio.gather(_(),return_exceptions=True)
  async def __aenter__(self):
    return self
  async def __aexit__(self,exc_type,exc,tb):
    self.close()
    await self.wait_closed()
  close=lambda self:self._q.shutdown()
  def put(self,c):
    f=asyncio.get_running_loop().create_future()
    self._q.put_nowait([c,f])
    return f
  wait_closed=lambda self:self._runner
