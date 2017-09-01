from .wrap import response_types
from .responses import JsonResponse, HtmlResponse, XmlResponse


__all__ = [JsonResponse, HtmlResponse, XmlResponse]


async def wrap_response(response):
    wrapped_response = await response_types.select(response)
    return wrapped_response
