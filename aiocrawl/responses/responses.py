import io
from lxml import etree
from pyquery import PyQuery


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

    def __repr__(self):
        out = io.StringIO()
        ascii_encodable_url = str(self.url)
        if self.reason:
            ascii_encodable_reason = self.reason.encode(
                'ascii', 'backslashreplace').decode('ascii')
        else:
            ascii_encodable_reason = self.reason
        print('<{}({}) [{} {}]>'.format(
            self.__class__.__name__,
            ascii_encodable_url, self.status, ascii_encodable_reason),
            file=out)
        return out.getvalue()


class JsonResponse(_BaseResponse):

    def __init__(self, response=None):
        super(self.__class__, self).__init__(response=response)
        self.json = response.json
        self.type = "json"


class HtmlResponse(_BaseResponse):

    def __init__(self, response=None):
        super(self.__class__, self).__init__(response=response)
        self.text = response.text
        self._e_doc = None
        self._p_doc = None
        self.type = "html"

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


class XmlResponse(HtmlResponse):
    pass
