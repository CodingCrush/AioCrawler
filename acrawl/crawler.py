import asyncio
import aiohttp
from datetime import datetime
try:
    import uvloop as async_loop
except ImportError:
    async_loop = asyncio


class ACrawl(object):
    name = None
    concurrency = 100
    loop = None
    # aiohttp client session
    ac_session = None
    bounded_semaphore = None

    def __init__(self, loop=None, concurrency=None, **kwargs):
        if not getattr(self, 'name', None):
            self.name = self.__class__.__name__
        if concurrency is not None:
            self.concurrency = concurrency
        if loop is None:
            loop = getattr(self, 'loop', None) or async_loop.new_event_loop()
            asyncio.set_event_loop(loop)
        else:
            self.loop = loop
        self.ac_session = aiohttp.ClientSession(loop=loop)
        self.__dict__.update(kwargs)

    async def on_start(self):
        raise NotImplementedError

    async def _acrawl(self, url, **kwargs):
        response = await self.ac_session.get(url)
        if 'sleep' in kwargs:
            await asyncio.sleep(kwargs['sleep'])
        if 'callback' in kwargs:
            callback_func = kwargs['callback']
            await callback_func(response)
        else:
            return response

    async def acrawl(self, urls, **kwargs):
        if isinstance(urls, str):
            await self._acrawl(urls, **kwargs)
        elif hasattr(urls, "__iter__"):
            for url in urls:
                await self._acrawl(url, **kwargs)

    async def run(self):
        start_at = datetime.now()
        print('Acrawl task:{} started'.format(self.name))

        try:
            self.bounded_semaphore = asyncio.BoundedSemaphore(self.concurrency)  # noqa
            task = asyncio.wait(self.on_start())
            self.loop.run_until_complete(task)

            async with self.bounded_semaphore:
                await self.on_start()
        except KeyboardInterrupt:
            for task in asyncio.Task.all_tasks():
                task.cancel()
        finally:
            end_at = datetime.now()
            print('Acrawl Finished in {} seconds'.format(
                (end_at-start_at).total_seconds()))
            self.ac_session.close()
            self.loop.close()
