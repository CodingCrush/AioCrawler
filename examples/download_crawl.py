from aiocrawl import AioCrawl
import os


class QisuuDownloadCrawl(AioCrawl):
    concurrency = 100
    urls = ("http://www.qisuu.com/Shtml{}.html".format(count) for count in range(1, 100))
    timeout = 100
    debug = True

    async def on_start(self):
        await self.get(self.urls, callback=self.parse_book)

    async def parse_book(self, response):
        try:
            book_select = response.xpath("/html/body/div[4]/div[2]")[0]
        except IndexError:
            return
        name = book_select.xpath("div[1]/div/div[2]/div/h1/text()")[0]
        try:
            author = book_select.xpath("div[1]/div/div[2]/div/ul/li[7]/a/text()")[0]
        except IndexError:
            author = book_select.xpath("div[1]/div/div[2]/div/ul/li[7]/text()")[0]

        txt_url = book_select.xpath("div[3]/div[2]/ul/li[2]/a/@href")[0]
        filename = " ".join((name, author)) + ".txt"
        save_dir = os.path.join(
            "test-download",
            "/".join(element.text for element in response.xpath("/html/body/div[3]/span/a")[1:-1])
        )

        self.logger.debug(os.path.join(save_dir, filename))
        await self.download(txt_url, save_dir=save_dir, filename=filename)


if __name__ == "__main__":
    crawl = QisuuDownloadCrawl()
    crawl.run()
