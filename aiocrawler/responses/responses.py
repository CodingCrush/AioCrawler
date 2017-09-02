from lxml import etree
from pyquery import PyQuery
from aiocrawler.exceptions import JsonDecodeError

try:
    from ujson import loads as json_loads
except ImportError:
    import sys
    import json
    # PY35 only support str not bytes.
    if sys.version_info[:2] == (3, 5):
        def json_loads(data):
            return json.loads(data.decode())
    else:
        json_loads = json.loads


class _BaseResponse(object):

    def __init__(self, response):
        self.__dict__.update(
            content_type=response.content_type,
            charset=response.charset,
            method=response.method,
            content=response.content,
            request_info=response.__dict__["_request_info"],
            url=response.__dict__["_url"],
            status=response.__dict__["status"],
            cookies=response.__dict__["cookies"],
            headers=response.__dict__["headers"],
            raw_headers=response.__dict__["raw_headers"],
            reason=response.reason
        )


class JsonResponse(_BaseResponse):

    def __init__(self, response=None):
        super(self.__class__, self).__init__(response=response)
        self.text = response.text
        self.type = "json"
        self._json = None

    @property
    def json(self):
        if self._json is None:
            try:
                self._json = json_loads(self.text)
            # ujson decode exception
            except (ValueError, SyntaxError) as e:
                raise JsonDecodeError(e)
            # json decode exception
            except json.JSONDecodeError as e:
                raise JsonDecodeError(e)
        return self._json


class HtmlResponse(_BaseResponse):

    def __init__(self, response=None):
        super(self.__class__, self).__init__(response=response)
        self.text = response.text
        self._etree = None
        self._py_query_doc = None
        self.type = "html"

    @property
    def etree(self):
        if self._etree is None:
            self._etree = etree.HTML(self.text)
        return self._etree

    @property
    def doc(self):
        if self._py_query_doc is None:
            self._py_query_doc = PyQuery(self.text)
        return self._py_query_doc

    def xpath(self, path):
        return self.etree.xpath(path)

    def selector(self, rule):
        return self.doc(rule)


class XmlResponse(HtmlResponse):
    pass
