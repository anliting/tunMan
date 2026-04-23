import asyncio
import declare
import ipaddress
import json
from pyroute2 import AsyncIPRoute
import signal
import traceback
from .Dns import Dns
from .QueueRunner import QueueRunner
from .Ssh import Ssh
from .watchFile import watchFile
@declare.scope
def NetworkInterface(queueRunner):
  ip=AsyncIPRoute()
  async def _():
    await ip.link('add',ifname='dummy0',kind='dummy')
  queueRunner.put(_())
  yield
  async def _():
    idx=(await ip.link_lookup(ifname='dummy0'))[0]
    await ip.link('del',index=idx)
  queueRunner.put(_())
@declare.scope
def Ipa(queueRunner,ipa,networkPrefix):
  ip=AsyncIPRoute()
  async def _():
    idx=(await ip.link_lookup(ifname='dummy0'))[0]
    await ip.addr('add',
      index=idx,
      address=str(ipaddress.IPv4Address(ipa)),
      prefixlen=networkPrefix
    )
  queueRunner.put(_())
  yield
  async def _():
    idx=(await ip.link_lookup(ifname='dummy0'))[0]
    await ip.addr('del',
      index=idx,
      address=str(ipaddress.IPv4Address(ipa)),
      prefixlen=networkPrefix
    )
  queueRunner.put(_())
@declare.component
def App(queueRunner,taskSet):
  hostnameIpa=declare.ref({})
  cfgMain,setCfgMain=declare.state(None)
  @declare.effect
  def _():
    def trySetCfgMain(s):
      try:
        setCfgMain(json.loads(s))
      except json.decoder.JSONDecodeError:
        traceback.print_exc()
    async def _():
      async def _(path):
        trySetCfgMain(path.read_text())
      await watchFile('cfg/main',_)
    t=taskSet.create_task(_())
    with open('cfg/main','r')as f:
      trySetCfgMain(f.read())
    yield
    t.cancel()
  if not cfgMain:
    return NetworkInterface(queueRunner=queueRunner)
  hostnameSet=set(
    v
    for ssh in cfgMain['ssh']
    for k,v in ssh.items()
    if k=='fromHost'
  )
  networkAddress=int(ipaddress.IPv4Address(cfgMain['networkAddress']))
  for hostname in[*hostnameIpa.val]:
    if(
        hostnameIpa.val[hostname]>>32-cfgMain['networkPrefix']!=
        networkAddress>>32-cfgMain['networkPrefix']
      or
        hostname not in hostnameSet
    ):
      del hostnameIpa.val[hostname]
  for hostname in hostnameSet-set(hostnameIpa.val.keys()):
    for ipa in range(
      networkAddress+2,
      networkAddress+2**(32-cfgMain['networkPrefix'])
    ):
      if ipa not in hostnameIpa.val.values():
        break
    else:
      break
    hostnameIpa.val[hostname]=ipa
  return NetworkInterface(
    Ipa(
      Dns(
        queueRunner=queueRunner,
        ipa=networkAddress+1,
        hostnameIpa={**hostnameIpa.val},
      ),
      [
        Ipa(
          [
            Ssh(
              queueRunner=queueRunner,
              taskSet=taskSet,
              cfg={
                k:str(ipaddress.IPv4Address(
                  hostnameIpa.val.get(v,v)
                ))if k=='fromHost'else v
                for k,v in ssh.items()
              },
            )
            for ssh in cfgMain['ssh']
            if ssh['fromHost']==hostname
          ],
          key=ipa,
          queueRunner=queueRunner,
          ipa=ipa,
          networkPrefix=cfgMain['networkPrefix'],
        )
        for hostname,ipa in hostnameIpa.val.items()
      ],
      queueRunner=queueRunner,
      ipa=networkAddress+1,
      networkPrefix=cfgMain['networkPrefix'],
    ),
    queueRunner=queueRunner,
  )
async def _():
  stop=asyncio.Event()
  asyncio.get_running_loop().add_signal_handler(signal.SIGTERM,stop.set)
  async with QueueRunner()as queueRunner,declare.TaskSet()as taskSet:
    with declare.Root(App(queueRunner,taskSet)):
      await stop.wait()
asyncio.run(_())
