from aiohttp.client import ClientResponse as ParResponse
from mimetypes import guess_type
from .responses import HtmlResponse, JsonResponse, XmlResponse


class ResponseTypes(object):

    CONTENT_TYPES = {
        'text/html': HtmlResponse,
        'application/atom+xml': XmlResponse,
        'application/rdf+xml': XmlResponse,
        'application/rss+xml': XmlResponse,
        'application/xhtml+xml': HtmlResponse,
        'application/vnd.wap.xhtml+xml': HtmlResponse,
        'application/xml': XmlResponse,
        'application/json': JsonResponse,
        'application/x-json': JsonResponse,
        'application/json-amazonui-streaming': JsonResponse,
        'application/javascript': JsonResponse,
        'application/x-javascript': JsonResponse,
        'text/xml': XmlResponse,
        'text/*': HtmlResponse,
    }

    @classmethod
    def lookup(cls, raw_response):
        assert isinstance(raw_response, ParResponse)
        try:
            return cls._lookup_mime_type(raw_response)
        except KeyError:
            pass
        try:
            return cls._lookup_header_content_type(raw_response)
        except KeyError:
            pass
        try:
            return cls._lookup_content_type(raw_response)
        except KeyError:
            pass
        return HtmlResponse

    @classmethod
    def _lookup_mime_type(cls, raw_response):
        guessed_type, _ = guess_type(str(raw_response.url))
        return cls.CONTENT_TYPES[guessed_type]

    @classmethod
    def _lookup_header_content_type(cls, raw_response):
        found_content_type = None
        # if not exists, .get_all() raise KeyError
        for content_type in raw_response.headers.getall("Content-Type"):
            if content_type in cls.CONTENT_TYPES:
                found_content_type = content_type
                break
        return cls.CONTENT_TYPES[found_content_type]

    @classmethod
    def _lookup_content_type(cls, raw_response):
        content_type = raw_response.content_type
        return cls.CONTENT_TYPES[content_type]

    @classmethod
    async def construct(cls, raw_response):
        factory_cls = cls.lookup(raw_response)
        response = factory_cls(raw_response)
        response.text = await response.text()
        return response
