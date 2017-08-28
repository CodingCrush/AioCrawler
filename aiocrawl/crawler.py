import asyncio
import aiohttp
import async_timeout
from aiohttp import hdrs
from datetime import datetime
from .responses import EnhancedResponse

try:
    import uvloop as async_loop
    asyncio.set_event_loop_policy(async_loop.EventLoopPolicy())
except ImportError:
    async_loop = asyncio


class AioCrawl(object):
    name = None
    concurrency = 100
    timeout = 10
    loop = None
    # aiohttp client session
    ac_session = None
    max_tries = 3

    _bounded_semaphore = None
    _failed_urls = set()

    def __init__(self, loop=None, concurrency=None, timeout=None, **kwargs):
        if not getattr(self, 'name', None):
            self.name = self.__class__.__name__
        if concurrency is not None:
            self.concurrency = concurrency
        if timeout is not None:
            self.timeout = timeout
        if loop is None:
            self.loop = getattr(self, 'loop', None) or \
                        async_loop.new_event_loop()
            asyncio.set_event_loop(loop)
        else:
            self.loop = loop
        self.ac_session = aiohttp.ClientSession(loop=self.loop)
        self.__dict__.update(kwargs)

    async def on_start(self):
        raise NotImplementedError()

    async def _request(self, url, callback=None, sleep=None, **kwargs):
        async with self._bounded_semaphore:
            # try max_tries if fail
            method = kwargs.pop('method').lower()
            http_method_request = getattr(self.ac_session, method)

            for _ in range(self.max_tries):
                try:
                    with async_timeout.timeout(self.timeout):
                        response = await http_method_request(url, **kwargs)
                        response = EnhancedResponse(response)
                        await response.ready()
                    break
                except aiohttp.ClientError:
                    pass
                except asyncio.TimeoutError:
                    pass
            else:  # still fail
                self._failed_urls.add(url)
                return
            if sleep:
                print('sleep for {}s'.format(sleep))
                await asyncio.sleep(sleep)
            if callback:
                await callback(response)

    async def get(self, urls, params=None, callback=None, sleep=None,
                  allow_redirects=True, **kwargs):
        kwargs.update(dict(callback=callback, sleep=sleep,
                           params=params, allow_redirects=allow_redirects))
        await asyncio.gather(*[self._request(
            url, **kwargs, method=hdrs.METH_GET) for url in urls])

    async def post(self, urls, data=None, json=None, callback=None,
                   sleep=None, allow_redirects=True, **kwargs):
        kwargs.update(callback=callback, sleep=sleep, data=data,
                      json=json, allow_redirects=allow_redirects)
        await asyncio.gather(*[self._request(
            url, **kwargs, method=hdrs.METH_POST) for url in urls])

    async def patch(self, urls, data=None, json=None, callback=None,
                    sleep=None, allow_redirects=True, **kwargs):
        kwargs.update(callback=callback, sleep=sleep, data=data,
                      json=json, allow_redirects=allow_redirects)
        await asyncio.gather(*[self._request(
            url, **kwargs, method=hdrs.METH_PATCH) for url in urls])

    async def put(self, urls, data=None, json=None, callback=None,
                  sleep=None, allow_redirects=True, **kwargs):
        kwargs.update(callback=callback, sleep=sleep, data=data,
                      json=json, allow_redirects=allow_redirects)
        await asyncio.gather(*[self._request(
            url, **kwargs, method=hdrs.METH_PUT) for url in urls])

    async def head(self, urls, callback=None, sleep=None,
                   allow_redirects=True, **kwargs):
        kwargs.update(callback=callback, sleep=sleep,
                      allow_redirects=allow_redirects)
        await asyncio.gather(*[self._request(
            url, **kwargs, method=hdrs.METH_HEAD) for url in urls])

    async def delete(self, urls, callback=None, sleep=None,
                     allow_redirects=True, **kwargs):
        kwargs.update(callback=callback, sleep=sleep,
                      allow_redirects=allow_redirects)
        await asyncio.gather(*[self._request(
            url, **kwargs, method=hdrs.METH_DELETE) for url in urls])

    async def options(self, urls, callback=None, sleep=None,
                      allow_redirects=True, **kwargs):
        kwargs.update(callback=callback, sleep=sleep,
                      allow_redirects=allow_redirects)
        await asyncio.gather(*[self._request(
            url, **kwargs, method=hdrs.METH_OPTIONS) for url in urls])

    def _close(self):
        self.ac_session.close()
        self.loop.close()

    def run(self):
        start_at = datetime.now()
        print('Acrawl task:{} started with concurrency:{}'.format(
            self.name, self.concurrency))

        try:
            self._bounded_semaphore = asyncio.BoundedSemaphore(
                self.concurrency, loop=self.loop
            )

            self.loop.run_until_complete(self.on_start())
        except KeyboardInterrupt:
            for task in asyncio.Task.all_tasks():
                task.cancel()
        finally:
            end_at = datetime.now()
            print('Acrawl task:{} finished in {} seconds'.format(
                self.name, (end_at-start_at).total_seconds()))
            self._close()
