import asyncio
import async_timeout
import aiohttp
import aiofiles
import inspect
import os
from datetime import datetime
from urllib import parse as urlparse
from pathlib import Path
from .responses import wrap_response
from .logger import create_logger
from .constants import DOWNLOAD_CHUNK_SIZE, WORKING_DIR, METHOD_DELETE, \
    METHOD_GET, METHOD_HEAD, METHOD_OPTIONS, METHOD_PATCH, METHOD_POST, \
    METHOD_PUT, DEFAULT_TIMEOUT, DEFAULT_CONCURRENCY, DEFAULT_MAX_TRIES

try:
    import uvloop as async_loop
except ImportError:
    async_loop = asyncio


class AioCrawl(object):
    name = None
    concurrency = DEFAULT_CONCURRENCY
    timeout = DEFAULT_TIMEOUT
    max_tries = DEFAULT_MAX_TRIES
    loop = None
    logger = None
    debug = False

    _failed_urls = set()
    _seen_urls = set()

    def __init__(self, **kwargs):
        self.name = getattr(self, 'name') or self.__class__.__name__

        self.loop = getattr(self, 'loop') or async_loop.new_event_loop()
        asyncio.set_event_loop(self.loop)

        self.ac_session = aiohttp.ClientSession(loop=self.loop)

        # Lifo Queue for Stashing all tasks to be done.
        self._tasks_que = asyncio.LifoQueue(loop=self.loop)

        self.logger = getattr(self, 'logger') or create_logger(self)

        self.__dict__.update(kwargs)

    def on_start(self):
        raise NotImplementedError()

    @staticmethod
    def get_request_url(url, params):
        if params is None:
            params = {}
        url_parts = list(urlparse.urlparse(url))
        query = dict(urlparse.parse_qsl(url_parts[4]))
        query.update(params)
        url_parts[4] = urlparse.urlencode(query)
        return urlparse.urlunparse(url_parts)

    async def _request(self, url, parser=None, sleep=None, method=None,
                       file=None, **kwargs):
        http_method_request = getattr(self.ac_session, method.lower())
        this_request_url = self.get_request_url(url, kwargs.get('params'))

        # try max_tries if fail
        for _ in range(self.max_tries):
            try:
                with async_timeout.timeout(self.timeout):
                    response = await http_method_request(url, **kwargs)
                    self._seen_urls.add(this_request_url)
                break
            except aiohttp.ClientError:
                self.logger.error("{} {} ClientError".format(
                    method, this_request_url)
                )
            except asyncio.TimeoutError:
                self.logger.error("{} {} TimeoutError".format(
                    method, this_request_url)
                )
        else:  # still fail
            self._failed_urls.add(this_request_url)
            return

        if sleep is not None:
            await asyncio.sleep(sleep)

        if parser is None:
            return
        if parser is self._download:
            return await parser(response, file)

        response = await wrap_response(response)

        if inspect.iscoroutinefunction(parser) or \
                inspect.isawaitable(parser):
            return await parser(response)
        else:
            return parser(response)

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
        kwargs.update(sleep=sleep, params=params,
                      allow_redirects=allow_redirects, file=file)

        self._tasks_que.put_nowait(
            self._request(url, **kwargs, method=METHOD_GET,
                          parser=self._download))

    def get(self, urls, params=None, parser=None,
            sleep=None, allow_redirects=True, **kwargs):
        kwargs.update(parser=parser, sleep=sleep,
                      params=params, allow_redirects=allow_redirects)
        self._produce_request_tasks(urls, method=METHOD_GET, **kwargs)

    def post(self, urls, data=None, json=None, parser=None,
             sleep=None, allow_redirects=True, **kwargs):
        kwargs.update(parser=parser, sleep=sleep, data=data,
                      json=json, allow_redirects=allow_redirects)
        self._produce_request_tasks(urls, method=METHOD_POST, **kwargs)

    def patch(self, urls, data=None, json=None, parser=None,
              sleep=None, allow_redirects=True, **kwargs):
        kwargs.update(parser=parser, sleep=sleep, data=data,
                      json=json, allow_redirects=allow_redirects)
        self._produce_request_tasks(urls, method=METHOD_PATCH, **kwargs)

    def put(self, urls, data=None, json=None, parser=None,
            sleep=None, allow_redirects=True, **kwargs):
        kwargs.update(parser=parser, sleep=sleep, data=data,
                      json=json, allow_redirects=allow_redirects)
        self._produce_request_tasks(urls, method=METHOD_PUT, **kwargs)

    def head(self, urls, parser=None, sleep=None,
             allow_redirects=True, **kwargs):
        kwargs.update(parser=parser, sleep=sleep,
                      allow_redirects=allow_redirects)
        self._produce_request_tasks(urls, method=METHOD_HEAD, **kwargs)

    def delete(self, urls, parser=None, sleep=None,
               allow_redirects=True, **kwargs):
        kwargs.update(parser=parser, sleep=sleep,
                      allow_redirects=allow_redirects)
        self._produce_request_tasks(urls, method=METHOD_DELETE, **kwargs)

    def options(self, urls, parser=None, sleep=None,
                allow_redirects=True, **kwargs):
        kwargs.update(parser=parser, sleep=sleep,
                      allow_redirects=allow_redirects)
        self._produce_request_tasks(urls, method=METHOD_OPTIONS, **kwargs)

    def _produce_request_tasks(self, urls, method=None, **kwargs):
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            self._tasks_que.put_nowait(
                self._request(url, **kwargs, method=method)
            )

    async def workers(self):
        while True:
            task = await self._tasks_que.get()
            await task
            self._tasks_que.task_done()

    async def work(self):
        self.on_start()

        workers = [
            asyncio.Task(self.workers(), loop=self.loop)
            for _ in range(self.concurrency)
        ]

        await self._tasks_que.join()
        for worker in workers:
            worker.cancel()

    def run(self):
        start_at = datetime.now()
        self.logger.info('AioCrawl task:{} started, Concurrency:{}'.format(
            self.name, self.concurrency))
        try:
            self.loop.run_until_complete(self.work())
        except KeyboardInterrupt:
            for task in asyncio.Task.all_tasks():
                task.cancel()
        except asyncio.CancelledError:
            pass  # All tasks has been cancelled
        finally:
            end_at = datetime.now()
            self.logger.info(
                'AioCrawl task:{} finished in {} seconds.'
                'Success:{}, Failure:{}'.format(
                    self.name, (end_at-start_at).total_seconds(),
                    len(self._seen_urls), len(self._failed_urls))
            )
            self.ac_session.close()
            self.loop.close()

    def __call__(self, *args, **kwargs):
        self.run()
