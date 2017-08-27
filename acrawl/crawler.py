import asyncio
import aiohttp
from datetime import datetime

try:
    import uvloop as async_loop
    asyncio.set_event_loop_policy(async_loop.EventLoopPolicy())
except ImportError:
    async_loop = asyncio


class ACrawl(object):
    name = None
    concurrency = 100
    loop = None
    # aiohttp client session
    ac_session = None
    max_tries = 3
    _bounded_semaphore = None

    def __init__(self, loop=None, concurrency=None, **kwargs):
        if not getattr(self, 'name', None):
            self.name = self.__class__.__name__
        if concurrency is not None:
            self.concurrency = concurrency
        if loop is None:
            self.loop = getattr(self, 'loop', None) or \
                        async_loop.new_event_loop()
            asyncio.set_event_loop(loop)
        else:
            self.loop = loop
        self.ac_session = aiohttp.ClientSession(loop=self.loop)
        self.__dict__.update(kwargs)

    async def on_start(self):
        # noqa
        raise NotImplementedError()

    async def _fetch_response(self, url, **kwargs):
        method = (kwargs.get('method') or "").lower()
        if method == "get" or not method:
            return await self.ac_session.get(url, params=kwargs.get("params", {}))  # noqa

        elif method in ("post", "patch", "put"):
            if "data" in kwargs:
                command = "self.ac_session.{}(url, data=kwargs['data'])".format(method)  # noqa
            elif "json" in kwargs:
                command = "self.ac_session.{}(url, json=kwargs['data'])".format(method)  # noqa
            else:
                command = "self.ac_session.{}(url)".format(method)
            return await eval(command)
        elif method in ("delete", "head", "options"):
            return await eval("self.ac_session.{}(url)".format(method))
        else:
            print("method:{} is not supported".format(method))

    async def _acrawl(self, url, **kwargs):
        async with self._bounded_semaphore:
            # try max_tries if fail
            for _ in range(self.max_tries):
                try:
                    response = await self._fetch_response(url, **kwargs)
                    break
                except aiohttp.ClientError:
                    pass
            else:  # still fail
                return
            if 'sleep' in kwargs:
                print('sleep for {}s'.format(kwargs['sleep']))
                await asyncio.sleep(kwargs['sleep'])
            if 'callback' in kwargs:
                callback_func = kwargs['callback']
                await callback_func(response)

    async def acrawl(self, urls, callback=None, sleep=None, data=None,
                     method=None, json=None, params=None):
        kwargs = dict(
            callback=callback,
            sleep=sleep,
            data=data,
            method=method,
            json=json,
            params=params
        )
        await asyncio.gather(*[self._acrawl(url, **kwargs) for url in urls])

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
