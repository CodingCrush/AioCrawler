import aioredis
import asyncio
import time
import umsgpack
from aiocrawler.exceptions import QueueEmpty, QueueFull
from aiocrawler.crawler import async_loop
from aiocrawler.constants import QUEUE_BLOCK_SLEEP_INTERVAL, \
    AIOREDIS_POOL_MIN_SIZE, AIOREDIS_POOL_MAX_SIZE


class AioRedisQueue(object):

    def __init__(self, name, host="localhost", port=6379, db=0, max_size=0,
                 password=None, loop=None, timeout=None, ssl=None,
                 encoding=None):
        self._name = name
        self._host = host
        self._port = port
        self._db = db
        self._password = password
        self._timeout = timeout
        self._ssl = ssl
        self._encoding = encoding
        if loop is None:
            self._loop = async_loop.new_event_loop()
        else:
            self._loop = loop
        self._max_size = max_size
        self._pool = None

    async def connect(self):
        with await asyncio.Lock():
            self._pool = await aioredis.create_pool(
                (self._host, self._port), db=self._db, password=self._password,
                ssl=self._ssl, encoding=self._encoding, loop=self._loop,
                minsize=AIOREDIS_POOL_MIN_SIZE, maxsize=AIOREDIS_POOL_MAX_SIZE
            )

    async def close(self):
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()

    async def qsize(self):
        if not self._pool:
            await self.connect()
        return await self._pool.execute("LLEN", self._name)

    async def empty(self):
        return await self.qsize() == 0

    async def full(self):
        if not self._max_size:
            return False
        return await self.qsize() >= self._max_size

    # no wait for full, but still async
    async def put_nowait(self, item):
        if not self._pool:
            await self.connect()
        if await self.full():
            raise QueueFull
        await self._pool.execute("RPUSH", self._name, umsgpack.packb(item))
        return True

    async def put(self, item, block=True, timeout=None):
        if not block:
            return await self.put_nowait(item)
        timeout = timeout or self._timeout
        start_time = time.time()

        while True:
            try:
                return await self.put_nowait(item)
            except QueueFull:
                if not timeout:
                    await asyncio.sleep(QUEUE_BLOCK_SLEEP_INTERVAL)
                    continue
                lasted = time.time() - start_time
                if lasted < timeout:
                    await asyncio.sleep(min(timeout, timeout-lasted))
                else:  # timeout
                    raise

    async def _get(self):
        if not self._pool:
            await self.connect()
        return await self._pool.execute("LPOP", self._name)

    async def get_nowait(self):
        if not self._pool:
            await self.connect()
        serialized_item = await self._get()
        if serialized_item is None:
            raise QueueEmpty
        return umsgpack.unpackb(serialized_item)

    async def get(self, block=True, timeout=None):
        if not block:
            return await self.get_nowait()
        timeout = timeout or self._timeout
        start_time = time.time()

        while True:
            try:
                return await self.get_nowait()
            except QueueEmpty:
                if not timeout:
                    await asyncio.sleep(QUEUE_BLOCK_SLEEP_INTERVAL)
                    continue
                lasted = time.time() - start_time
                if lasted < timeout:
                    await asyncio.sleep(min(timeout, timeout-lasted))
                else:  # timeout
                    raise


class AioRedisLifoQueue(AioRedisQueue):

    async def _get(self):
        return self._pool.execute("RPOP", self._name)
