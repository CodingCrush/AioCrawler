from aiohttp.client import ClientResponse as ParResponse
from mimetypes import guess_type
from .responses import HtmlResponse, JsonResponse, XmlResponse


class ResponseTypes(object):

    _CONTENT_TYPE_TO_RESPONSE = {
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

    def _lookup(self, response):
        assert isinstance(response, ParResponse)
        try:
            return self._lookup_mime_type(response)
        except KeyError:
            try:
                return self._lookup_content_type(response)
            except KeyError:
                pass

        return self._default_type(response)

    def _lookup_mime_type(self, response):
        guessed_type, _ = guess_type(str(response.url))
        return self._CONTENT_TYPE_TO_RESPONSE[guessed_type](response)

    def _lookup_content_type(self, response):
        content_type = response.content_type
        return self._CONTENT_TYPE_TO_RESPONSE[content_type](response)

    @staticmethod
    def _default_type(response):
        return HtmlResponse(response)

    @staticmethod
    async def _ready(selected):
        if isinstance(selected, JsonResponse):
            selected.json = await selected.json()
        else:
            selected.text = await selected.text()
        return selected

    async def select(self, response):
        selected = self._lookup(response)
        return await self._ready(selected)

response_types = ResponseTypes()
