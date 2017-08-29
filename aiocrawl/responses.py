from lxml import etree
from pyquery import PyQuery


class _BaseResponse(object):

    def __init__(self, response):
        self.__dict__.update(
            content_type=response.content_type,
            charset=response.charset,
            method=response.method,
            content=response.content,
            request=response.__dict__["_request_info"],
            url=response.__dict__["_url"],
            status=response.__dict__["status"],
            cookies=response.__dict__["cookies"],
            headers=response.__dict__["headers"],
            raw_headers=response.__dict__["raw_headers"]
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
        self._e_doc = None
        self._p_doc = None
        self.type = "html"

    async def ready(self):
        self.text = await self.text()

    @property
    def e_doc(self):
        if self._e_doc is None:
            self._e_doc = etree.HTML(self.text)
        return self._e_doc

    @property
    def p_doc(self):
        if self._p_doc is None:
            self._p_doc = PyQuery(self.text)
        return self._p_doc

    def xpath(self, path):
        try:
            return self.e_doc.xpath(path)
        except IndexError:
            return

    def selector(self, rule):
        return self.p_doc(rule)
