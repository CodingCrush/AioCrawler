import asyncio
import async_timeout
import aiohttp
import aiofiles
import inspect
import os
from datetime import datetime
from pathlib import Path
from .responses import JsonResponse, HTMLResponse
from .logger import create_logger
from .constants import DOWNLOAD_CHUNK_SIZE, WORKING_DIR, METHOD_DELETE, METHOD_GET, METHOD_HEAD, \
    METHOD_OPTIONS, METHOD_PATCH, METHOD_POST, METHOD_PUT

try:
    import uvloop as async_loop
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
    _seen_urls = set()

    def __init__(self, loop=None, concurrency=None, timeout=None, logger=None, **kwargs):
        if not getattr(self, 'name', None):
            self.name = self.__class__.__name__
        if concurrency is not None:
            self.concurrency = concurrency

        if timeout is not None:
            self.timeout = timeout

        if loop is None:
            self.loop = getattr(self, 'loop', None) or async_loop.new_event_loop()
            asyncio.set_event_loop(loop)
        else:
            self.loop = loop
        self.ac_session = aiohttp.ClientSession(loop=self.loop)

        # Tasks Queue for Future objects.
        self._tasks_que = asyncio.LifoQueue(loop=self.loop)

        if not getattr(self, 'logger', None):
            if logger is None:
                self.logger = create_logger(self)
            else:
                self.logger = logger

        self.__dict__.update(kwargs)

    def on_start(self):
        raise NotImplementedError()

    async def _request(self, url, callback=None, sleep=None, **kwargs):
        method = kwargs.pop('method')
        # used for download
        file = kwargs.pop("file", None)
        http_method_request = getattr(self.ac_session, method.lower())
        # try max_tries if fail
        for _ in range(self.max_tries):
            try:
                with async_timeout.timeout(self.timeout):
                    response = await http_method_request(url, **kwargs)
                    self._seen_urls.add(url)
                break
            except aiohttp.ClientError:
                self.logger.debug("{} {} ClientError".format(method, url))
            except asyncio.TimeoutError:
                self.logger.debug("{} {} TimeoutError".format(method, url))
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

    def download(self, url, save_dir=WORKING_DIR, filename=None, params=None,
                 sleep=None, allow_redirects=True, **kwargs):
        # recursively mkdirs, ignore exists
        path = Path(save_dir)
        path.mkdir(parents=True, exist_ok=True)
        file = os.path.join(save_dir, filename)
        kwargs.update(sleep=sleep, params=params, allow_redirects=allow_redirects, file=file)

        self._tasks_que.put_nowait(
            self._request(url, **kwargs, method=METHOD_GET, callback=self._download))

    def get(self, urls, params=None, callback=None, sleep=None, allow_redirects=True, **kwargs):
        kwargs.update(callback=callback, sleep=sleep, params=params, allow_redirects=allow_redirects)
        self._produce_request_tasks(urls, method=METHOD_GET, **kwargs)

    def post(self, urls, data=None, json=None, callback=None, sleep=None, allow_redirects=True, **kwargs):
        kwargs.update(callback=callback, sleep=sleep, data=data, json=json, allow_redirects=allow_redirects)
        self._produce_request_tasks(urls, method=METHOD_POST, **kwargs)

    def patch(self, urls, data=None, json=None, callback=None, sleep=None, allow_redirects=True, **kwargs):
        kwargs.update(callback=callback, sleep=sleep, data=data, json=json, allow_redirects=allow_redirects)
        self._produce_request_tasks(urls, method=METHOD_PATCH, **kwargs)

    def put(self, urls, data=None, json=None, callback=None, sleep=None, allow_redirects=True, **kwargs):
        kwargs.update(callback=callback, sleep=sleep, data=data, json=json, allow_redirects=allow_redirects)
        self._produce_request_tasks(urls, method=METHOD_PUT, **kwargs)

    def head(self, urls, callback=None, sleep=None, allow_redirects=True, **kwargs):
        kwargs.update(callback=callback, sleep=sleep, allow_redirects=allow_redirects)
        self._produce_request_tasks(urls, method=METHOD_HEAD, **kwargs)

    def delete(self, urls, callback=None, sleep=None, allow_redirects=True, **kwargs):
        kwargs.update(callback=callback, sleep=sleep, allow_redirects=allow_redirects)
        self._produce_request_tasks(urls, method=METHOD_DELETE, **kwargs)

    def options(self, urls, callback=None, sleep=None, allow_redirects=True, **kwargs):
        kwargs.update(callback=callback, sleep=sleep, allow_redirects=allow_redirects)
        self._produce_request_tasks(urls, method=METHOD_OPTIONS, **kwargs)

    def _produce_request_tasks(self, urls, method=None, **kwargs):
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            self._tasks_que.put_nowait(self._request(url, **kwargs, method=method))

    async def workers(self):
        # produce as much tasks as possible.
        while True:
            try:
                await self._tasks_que.get_nowait()
                self._tasks_que.task_done()
            except asyncio.CancelledError:
                pass
            except asyncio.QueueEmpty:
                asyncio.sleep(0.5)
                if not self._tasks_que.qsize():
                    break

    async def work(self):
        self.on_start()
        
        workers = [
            asyncio.Task(self.workers(), loop=self.loop)
            for _ in range(self.concurrency)
        ]

        await self._tasks_que.join()
        for w in workers:
            w.cancel()

    def run(self):
        start_at = datetime.now()
        self.logger.info('Aiocrawl task:{} started with concurrency:{}'.format(
            self.name, self.concurrency))
        try:
            self.loop.run_until_complete(self.work())
        except KeyboardInterrupt:
            for task in asyncio.Task.all_tasks():
                task.cancel()
        finally:
            end_at = datetime.now()
            self.logger.info('Aiocrawl task:{} finished in {} seconds. Success:{}, Failure:{}'.format(
                self.name, (end_at-start_at).total_seconds(), len(self._seen_urls), len(self._failed_urls)))
            self.ac_session.close()
            self.loop.close()

    def __call__(self, *args, **kwargs):
        self.run()
