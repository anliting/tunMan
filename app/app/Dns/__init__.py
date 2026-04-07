import declare
import ipaddress
from dnslib.server import DNSServer,DNSLogger
from .dns import MyResolver
@declare.scope
def Dns(queueRunner,ipa,hostnameIpa):
  udp_server=tcp_server=None
  async def _():
    nonlocal udp_server
    nonlocal tcp_server
    resolver=MyResolver(
      hostnameIpa,
      upstreamHost='1.1.1.1',
      upstreamPort=53,
      timeout=5,
    )
    logger=DNSLogger(logf=lambda s:None)
    udp_server=DNSServer(
      resolver,
      address=str(ipaddress.IPv4Address(ipa)),
      logger=logger,
    )
    tcp_server=DNSServer(
      resolver,
      address=str(ipaddress.IPv4Address(ipa)),
      logger=logger,
      tcp=True,
    )
    udp_server.start_thread()
    tcp_server.start_thread()
  queueRunner.put(_())
  yield
  async def _():
    udp_server.stop()
    tcp_server.stop()
    udp_server.server.server_close()
    tcp_server.server.server_close()
  queueRunner.put(_())
