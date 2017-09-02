import asyncio
import async_timeout
import aiohttp
import aiofiles
import inspect
import os
from datetime import datetime
from urllib import parse as urlparse
from pathlib import Path
from aiocrawler.responses import wrap_response
from aiocrawler.logger import create_logger
from aiocrawler.constants import DOWNLOAD_CHUNK_SIZE, WORKING_DIR, \
    METHOD_DELETE, METHOD_GET, METHOD_HEAD, METHOD_OPTIONS, METHOD_PATCH, \
    METHOD_POST, METHOD_PUT, DEFAULT_TIMEOUT, DEFAULT_CONCURRENCY, \
    DEFAULT_MAX_TRIES, AIOHTTP_AUTO_HEADERS, NORMAL_STATUS_CODES

try:
    import uvloop as async_loop
except ImportError:
    async_loop = asyncio


class AioCrawler(object):
    name = None
    concurrency = DEFAULT_CONCURRENCY
    timeout = DEFAULT_TIMEOUT
    max_tries = DEFAULT_MAX_TRIES
    headers = None
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

    def _update_kwargs_headers(self, **kwargs):
        headers = kwargs.get("headers") or self.headers
        if callable(headers):
            # avoid aiohttp autogenerates headers
            kwargs["skip_auto_headers"] = AIOHTTP_AUTO_HEADERS
            kwargs["headers"] = headers()
        if isinstance(headers, dict):
            kwargs["headers"] = headers
        return kwargs

    async def _request(self, url, parser=None, sleep=None,
                       method=None, file=None, **kwargs):
        # If url is list, set, or tuple.Then Split the tasks
        if not isinstance(url, str):
            if hasattr(url, "__iter__"):
                for _url in url:
                    self._tasks_que.put_nowait(self._request(
                        _url, sleep=sleep, method=method, file=file,
                        parser=parser, **kwargs
                    ))
                return
            else:
                url = str(url)

        http_method_request = getattr(self.ac_session, method.lower())
        this_request_url = self.get_request_url(url, kwargs.get('params'))

        kwargs = self._update_kwargs_headers(**kwargs)

        # try max_tries if fail
        for try_count in range(1, self.max_tries+1):
            try:
                with async_timeout.timeout(self.timeout):
                    response = await http_method_request(url, **kwargs)
                    self._seen_urls.add(this_request_url)
                break
            except aiohttp.ClientError:
                self.logger.debug("[{}] {} [ClientError][Try:{}]".format(
                    method, this_request_url, try_count)
                )
            except asyncio.TimeoutError:
                self.logger.debug("[{}] {} [TimeoutError][Try:{}]".format(
                    method, this_request_url, try_count)
                )
        else:  # still fail
            self._failed_urls.add(this_request_url)
            return self.logger.error("[{}] {} [Failure][Try:{}]".format(
                method, this_request_url, self.max_tries)
            )

        self.logger.info("[{}] {} [{} {}]".format(
            method, this_request_url, response.status, response.reason)
        )

        if response.status not in NORMAL_STATUS_CODES:
            return

        if sleep is not None:
            await asyncio.sleep(sleep)

        if parser is None:
            return
        if parser is self._download:
            await parser(response, file)
            return self.logger.info("[DOWNLOAD]:{}".format(file))

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

    def download(self, url, save_dir=WORKING_DIR, headers=None, filename=None,
                 params=None, sleep=None, allow_redirects=True, **kwargs):
        # recursively mkdir, ignore error when directory exists
        if not os.path.exists(save_dir):
            path = Path(save_dir)
            path.mkdir(parents=True, exist_ok=True)
        file = os.path.join(save_dir, filename)

        self._tasks_que.put_nowait(self._request(
            url, sleep=sleep, params=params, method=METHOD_GET,
            headers=headers, file=file, parser=self._download,
            allow_redirects=allow_redirects, **kwargs
        ))

    def get(self, urls, params=None, parser=None, headers=None,
            sleep=None, allow_redirects=True, **kwargs):
        self._tasks_que.put_nowait(self._request(
            urls, parser=parser, sleep=sleep, method=METHOD_GET,
            params=params, headers=headers, allow_redirects=allow_redirects,
            **kwargs
        ))

    def post(self, urls, data=None, json=None, parser=None, headers=None,
             sleep=None, allow_redirects=True, **kwargs):
        self._tasks_que.put_nowait(self._request(
            urls, parser=parser, sleep=sleep, method=METHOD_POST,
            headers=headers, data=data, json=json,
            allow_redirects=allow_redirects, **kwargs
        ))

    def patch(self, urls, data=None, json=None, parser=None, headers=None,
              sleep=None, allow_redirects=True, **kwargs):
        self._tasks_que.put_nowait(self._request(
            urls, parser=parser, sleep=sleep, method=METHOD_PATCH,
            headers=headers, data=data, json=json,
            allow_redirects=allow_redirects, **kwargs
        ))

    def put(self, urls, data=None, json=None, parser=None,
            sleep=None, allow_redirects=True, **kwargs):
        self._tasks_que.put_nowait(self._request(
            urls, parser=parser, sleep=sleep, method=METHOD_PUT, data=data,
            json=json, allow_redirects=allow_redirects, **kwargs
        ))

    def head(self, urls, parser=None, sleep=None, headers=None,
             allow_redirects=True, **kwargs):
        self._tasks_que.put_nowait(self._request(
            urls, parser=parser, sleep=sleep, method=METHOD_HEAD,
            headers=headers, allow_redirects=allow_redirects, **kwargs
        ))

    def delete(self, urls, parser=None, sleep=None, headers=None,
               allow_redirects=True, **kwargs):
        self._tasks_que.put_nowait(self._request(
            urls, parser=parser, sleep=sleep, method=METHOD_DELETE,
            headers=headers, allow_redirects=allow_redirects, **kwargs
        ))

    def options(self, urls, parser=None, sleep=None, headers=None,
                allow_redirects=True, **kwargs):
        self._tasks_que.put_nowait(self._request(
            urls, parser=parser, sleep=sleep, method=METHOD_OPTIONS,
            headers=headers, allow_redirects=allow_redirects, **kwargs
        ))

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
        self.logger.info('{} Started, Concurrency:{}'.format(
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
                '{} Finished in {} seconds.'
                'Success:{}, Failure:{}'.format(
                    self.name, (end_at-start_at).total_seconds(),
                    len(self._seen_urls), len(self._failed_urls))
            )
            self.ac_session.close()
            self.loop.close()

    def __call__(self, *args, **kwargs):
        self.run()
