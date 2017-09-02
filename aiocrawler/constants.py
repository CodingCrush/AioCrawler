import os


# aio download buffer chunk size: 500kb
DOWNLOAD_CHUNK_SIZE = 512000

DEFAULT_TIMEOUT = 20
DEFAULT_CONCURRENCY = 20
DEFAULT_MAX_TRIES = 3

WORKING_DIR = os.getcwd()


METHOD_HEAD = 'HEAD'
METHOD_GET = 'GET'
METHOD_DELETE = 'DELETE'
METHOD_OPTIONS = 'OPTIONS'
METHOD_PATCH = 'PATCH'
METHOD_POST = 'POST'
METHOD_PUT = 'PUT'

# aiohttp autogenerates headers like User-Agent or Content-Type
# if these headers are not explicitly passed.
AIOHTTP_AUTO_HEADERS = ("User-Agent", "Content-Type")

# if response.status not in the set, drop the response.
NORMAL_STATUS_CODES = (200, 201)
