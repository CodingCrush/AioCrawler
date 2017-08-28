from lxml import etree
from pyquery import PyQuery


class EnhancedResponse(object):
    def __init__(self, response=None):
        self.response = response
        self.request = response.request_info
        self.doc = None
        self.text = None
        self.pq_doc = None

    async def ready(self):
        self.text = await self.response.text()
        self.__dict__.update(self.response.__dict__)
        self.__dict__ = {k: v for k, v in self.__dict__.items()
                         if not k.startswith("_")}

    def xpath(self, path):
        if self.doc is None:
            self.doc = etree.HTML(self.text)
        try:
            return self.doc.xpath(path)
        except IndexError:
            return

    def css(self):
        if self.pq_doc is None:
            self.pq_doc = PyQuery(self.text)
        return self.pq_doc
