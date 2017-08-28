from lxml import etree
from pyquery import PyQuery


class _BaseResponse(object):

    def __init__(self, response=None):
        self.__dict__.update(
            content_type=response.content_type,
            charset=response.charset,
            method=response.method,
            request=response.__dict__["_request_info"],
            url=response.__dict__["_url"],
            status=response.__dict__["status"],
            cookies=response.__dict__["cookies"],
            headers=response.__dict__["headers"],
            raw_headers=response.__dict__["raw_headers"],
        )

    async def ready(self):
        raise NotImplementedError


class JsonResponse(_BaseResponse):

    def __init__(self, response=None):
        super(self.__class__, self).__init__(response=response)
        self.json = response.json
        self.type = "json"

    async def ready(self):
        self.json = await self.json()


class HTMLResponse(_BaseResponse):

    def __init__(self, response=None):
        super(self.__class__, self).__init__(response=response)
        self.text = response.text
        self.doc = None
        self.pq_doc = None
        self.type = "html"

    async def ready(self):
        self.text = await self.text()

    def xpath(self, path):
        if self.doc is None:
            self.doc = etree.HTML(self.text)
        try:
            return self.doc.xpath(path)
        except IndexError:
            return

    def css(self, rule):
        if self.pq_doc is None:
            self.pq_doc = PyQuery(self.text)
        if rule is None:
            return self.pq_doc
        return self.pq_doc(rule)
