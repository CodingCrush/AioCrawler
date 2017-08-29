from aiocrawl import AioCrawl


class DownloadCrawl(AioCrawl):
    concurrency = 1
    url = "http://dzs.qisuu.com/txt/%E9%80%86%E5%A4%A9%E9%AC%BC%E4%BF%AE.txt"
    timeout = 10
    debug = True

    async def on_start(self):
        await self.download(self.url, filename="test.txt")


if __name__ == "__main__":
    crawl = DownloadCrawl()
    crawl.run()
