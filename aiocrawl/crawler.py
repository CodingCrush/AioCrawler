import asyncio
import async_timeout
import aiohttp
import aiofiles
import inspect
import os
from aiohttp import hdrs
from datetime import datetime
from pathlib import Path
from .responses import JsonResponse, HTMLResponse
from .logger import create_logger
from .constants import DOWNLOAD_CHUNK_SIZE, WORKING_DIR

try:
    import uvloop as async_loop
    asyncio.set_event_loop_policy(async_loop.EventLoopPolicy())
except ImportError:
    async_loop = asyncio


class AioCrawl(object):
    name = None
    concurrency = 20
    timeout = 10
    loop = None
    max_tries = 3
    debug = False

    _failed_urls = set()

    def __init__(self, loop=None, concurrency=None, timeout=None,
                 logger=None, **kwargs):
        if not getattr(self, 'name', None):
            self.name = self.__class__.__name__
        if concurrency is not None:
            self.concurrency = concurrency

        # Unlimited Queue for tasks buffer.
        self._todo_tasks = asyncio.LifoQueue()

        if timeout is not None:
            self.timeout = timeout

        if loop is None:
            self.loop = getattr(self, 'loop', None) or \
                        async_loop.new_event_loop()
            asyncio.set_event_loop(loop)
        else:
            self.loop = loop
        self.ac_session = aiohttp.ClientSession(loop=self.loop)

        if not getattr(self, 'logger', None):
            if logger is None:
                self.logger = create_logger(self)
            else:
                self.logger = logger

        self.__dict__.update(kwargs)

    async def on_start(self):
        raise NotImplementedError()

    async def _request(self, url, callback=None, sleep=None, **kwargs):
        method = kwargs.pop('method').lower()
        # used for download
        file = kwargs.pop("file", None)
        http_method_request = getattr(self.ac_session, method)
        # try max_tries if fail
        for _ in range(self.max_tries):
            try:
                with async_timeout.timeout(self.timeout):
                    response = await http_method_request(url, **kwargs)
                break
            except aiohttp.ClientError:
                pass
            except asyncio.TimeoutError:
                pass
        else:  # still fail
            self._failed_urls.add(url)
            return

        if sleep is not None:
            await asyncio.sleep(sleep)

        if callback is None:
            return
        if callback is self._download:
            return await callback(response, file)

        response = await self._wrap_response(response)
        if inspect.iscoroutinefunction(callback) or inspect.isawaitable(callback):
            return await callback(response)
        else:
            return callback(response)

    @staticmethod
    async def _wrap_response(response):
        assert response is not None
        if response.content_type == "application/json":
            response = JsonResponse(response)
        else:
            response = HTMLResponse(response)
        await response.ready()
        return response

    # real download method
    @staticmethod
    async def _download(response, file):
        async with aiofiles.open(file, 'wb') as fd:
            while True:
                chunk = await response.content.read(DOWNLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                await fd.write(chunk)
                await fd.flush()

    async def _produce_request_tasks(self, urls, method=None, **kwargs):
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            await self._todo_tasks.put(self._request(url, **kwargs, method=method))

    async def download(self, url, save_dir=WORKING_DIR, filename=None, params=None,
                       sleep=None, allow_redirects=True, **kwargs):
        # recursively mkdirs, ignore exists
        path = Path(save_dir)
        path.mkdir(parents=True, exist_ok=True)
        file = os.path.join(save_dir, filename)
        kwargs.update(sleep=sleep, params=params, allow_redirects=allow_redirects, file=file)

        await self._todo_tasks.put(
            self._request(url, **kwargs, method=hdrs.METH_GET, callback=self._download))

    async def get(self, urls, params=None, callback=None, sleep=None,
                  allow_redirects=True, **kwargs):
        kwargs.update(callback=callback, sleep=sleep,
                      params=params, allow_redirects=allow_redirects)
        await self._produce_request_tasks(urls, method=hdrs.METH_GET, **kwargs)

    async def post(self, urls, data=None, json=None, callback=None,
                   sleep=None, allow_redirects=True, **kwargs):
        kwargs.update(callback=callback, sleep=sleep, data=data,
                      json=json, allow_redirects=allow_redirects)
        await self._produce_request_tasks(urls, method=hdrs.METH_POST, **kwargs)

    async def patch(self, urls, data=None, json=None, callback=None,
                    sleep=None, allow_redirects=True, **kwargs):
        kwargs.update(callback=callback, sleep=sleep, data=data,
                      json=json, allow_redirects=allow_redirects)
        await self._produce_request_tasks(urls, method=hdrs.METH_PATCH, **kwargs)

    async def put(self, urls, data=None, json=None, callback=None,
                  sleep=None, allow_redirects=True, **kwargs):
        kwargs.update(callback=callback, sleep=sleep, data=data,
                      json=json, allow_redirects=allow_redirects)
        await self._produce_request_tasks(urls, method=hdrs.METH_PUT, **kwargs)

    async def head(self, urls, callback=None, sleep=None,
                   allow_redirects=True, **kwargs):
        kwargs.update(callback=callback, sleep=sleep,
                      allow_redirects=allow_redirects)
        await self._produce_request_tasks(urls, method=hdrs.METH_HEAD, **kwargs)

    async def delete(self, urls, callback=None, sleep=None,
                     allow_redirects=True, **kwargs):
        kwargs.update(callback=callback, sleep=sleep,
                      allow_redirects=allow_redirects)
        await self._produce_request_tasks(urls, method=hdrs.METH_DELETE, **kwargs)

    async def options(self, urls, callback=None, sleep=None,
                      allow_redirects=True, **kwargs):
        kwargs.update(callback=callback, sleep=sleep,
                      allow_redirects=allow_redirects)
        await self._produce_request_tasks(urls, method=hdrs.METH_OPTIONS, **kwargs)

    async def workers(self):
        # produce as much tasks as possible.
        while True:
            try:
                await self._todo_tasks.get_nowait()
                self._todo_tasks.task_done()
            except asyncio.CancelledError:
                pass
            except asyncio.QueueEmpty:
                asyncio.sleep(0.5)
                if not self._todo_tasks.qsize():
                    break

    async def work(self):
        await self.on_start()
        workers = [
            asyncio.Task(self.workers(), loop=self.loop)
            for _ in range(self.concurrency)
        ]

        await self._todo_tasks.join()
        for w in workers:
            w.cancel()

    def run(self):
        start_at = datetime.now()
        print('Aiocrawl task:{} started with concurrency:{}'.format(
            self.name, self.concurrency))
        try:
            self.loop.run_until_complete(self.work())
        except KeyboardInterrupt:
            for task in asyncio.Task.all_tasks():
                task.cancel()
        finally:
            end_at = datetime.now()
            print('Aiocrawl task:{} finished in {} seconds'.format(
                self.name, (end_at-start_at).total_seconds()))
            self.ac_session.close()
            self.loop.close()