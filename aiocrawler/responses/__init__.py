from .responses import JsonResponse, HtmlResponse, XmlResponse
from .wrap import ResponseTypes


__all__ = [JsonResponse, HtmlResponse, XmlResponse]


async def wrap_response(response):
    wrapped_response = await ResponseTypes.construct(response)
    return wrapped_response
