from aiocrawl import AioCrawl
import os


class QisuuDownloadCrawl(AioCrawl):
    concurrency = 50
    urls = ("http://www.qisuu.com/Shtml{}.html".format(count) for count in range(1, 30000))
    timeout = 500
    debug = True

    def on_start(self):
        self.get(self.urls, parser=self.parse_book)

    def parse_book(self, response):
        if not response.status == 200:
            print("{}:{}".format(response.url, response.status))
            return

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
            "download", "/".join(element.text for element in response.xpath("/html/body/div[3]/span/a")[1:-1])
        )

        self.logger.debug(os.path.join(save_dir, filename))

        self.download(txt_url, save_dir=save_dir, filename=filename)


if __name__ == "__main__":
    crawl = QisuuDownloadCrawl()
    crawl.run()
