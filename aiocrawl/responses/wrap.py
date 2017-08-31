from aiohttp.web_response import Response as ParResponse
from mimetypes import guess_type
from .responses import HtmlResponse, JsonResponse, XmlResponse


async def wrap_response(response):
    wrapped_response = ResponseTypes(response)
    return await wrapped_response.ready()


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

    def __init__(self, response):
        self._response = response

    def lookup(self):
        assert issubclass(self._response, ParResponse)
        try:
            return self.lookup_mime_type()
        except KeyError:
            try:
                return self.lookup_content_type()
            except KeyError:
                pass

        return self.default_type()

    def lookup_mime_type(self):
        guessed_type, _ = guess_type(self._response)
        if guessed_type is not None:
            try:
                url = self._response.url
                return self._CONTENT_TYPE_TO_RESPONSE[guessed_type](url)
            except KeyError:
                pass
        else:
            raise KeyError

    def lookup_content_type(self):
        try:
            content_type = self._response.content_type
            return self._CONTENT_TYPE_TO_RESPONSE[content_type](self._response)
        except KeyError:
            pass

    def default_type(self):
        return HtmlResponse(self._response)

    async def ready(self):
        self.lookup()

        if isinstance(self._response, JsonResponse):
            self._response.json = await self._response.json()
        else:
            self._response.text = await self._response.text()
        return self._response
