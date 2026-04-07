import asyncio
from pathlib import Path
from inotify_simple import INotify,flags
async def watchFile(path,callback):
  target=Path(path).resolve()
  inotify=INotify()
  wd=inotify.add_watch(
    str(target.parent),
    flags.CLOSE_WRITE|flags.MOVED_TO,
  )
  loop=asyncio.get_running_loop()
  queue=asyncio.Queue()
  def _():
    for event in inotify.read(timeout=0):
      if(
        event.name==target.name and
        event.mask&(flags.CLOSE_WRITE|flags.MOVED_TO)
      ):
        queue.put_nowait(None)
  loop.add_reader(inotify.fileno(),_)
  try:
    while 1:
      await queue.get()
      await callback(target)
  finally:
    loop.remove_reader(inotify.fileno())
    inotify.rm_watch(wd)
    inotify.close()
