from aiocrawler import AioCrawler
import os


class QisuuCrawler(AioCrawler):
    concurrency = 20
    timeout = 500
    debug = True

    def on_start(self):
        for count in range(1, 31000):
            self.download(
                "http://dzs.qisuu.com/txt/{}.txt".format(count),
                filename=str(count)+".txt", sleep=1)

    def parse_book(self, response):

        try:
            book_select = response.xpath("/html/body/div[4]/div[2]")[0]
        except IndexError:
            return print("parse error")

        name = book_select.xpath("div[1]/div/div[2]/div/h1/text()")[0]

        try:
            author = book_select.xpath("div[1]/div/div[2]/div/ul/li[7]/a/text()")[0]
        except IndexError:
            author = book_select.xpath("div[1]/div/div[2]/div/ul/li[7]/text()")[0]

        txt_url = book_select.xpath("div[3]/div[2]/ul/li[2]/a/@href")[0]

        save_dir = os.path.join(
            "download", "/".join(
                element.text for element in
                response.xpath("/html/body/div[3]/span/a")[1:-1])
        )

        self.download(txt_url, save_dir=save_dir, filename=" ".join((name, author)) + ".txt")


if __name__ == "__main__":
    crawler = QisuuCrawler()
    crawler.run()
