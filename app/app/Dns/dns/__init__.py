import ipaddress
from dnslib import A,QTYPE,RCODE,RR
from dnslib.proxy import ProxyResolver
from dnslib.server import BaseResolver
class MyResolver(BaseResolver):
  def __init__(
    self,
    hostnameIpa,
    upstreamHost,
    upstreamPort,
    timeout,
  ):
    self.proxy=ProxyResolver(upstreamHost,upstreamPort,timeout=timeout)
    self.aRec={
      k+'.':str(ipaddress.IPv4Address(v))
      for k,v in hostnameIpa.items()
    }
  def resolve(self,request,handler):
    qname=str(request.q.qname)
    if request.q.qtype in(QTYPE.A,QTYPE.ANY)and qname in self.aRec:
      reply=request.reply()
      reply.header.aa=1
      reply.add_answer(RR(
        rname=qname,
        rtype=QTYPE.A,
        ttl=60,
        rdata=A(self.aRec[qname]),
      ))
      return reply
    try:
      return self.proxy.resolve(request,handler)
    except Exception:
      reply=request.reply()
      reply.header.rcode=RCODE.SERVFAIL
      return reply
