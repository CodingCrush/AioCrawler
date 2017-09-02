from aiocrawler import AioCrawler
from aiocrawler.request import random_navigator_headers


class LianjiaCrawler(AioCrawler):
    concurrency = 50
    urls = (
        "http://sh.lianjia.com/zufang/d{}".format(count)
        for count in range(1, 100)
    )
    timeout = 30
    debug = True
    headers = random_navigator_headers

    def on_start(self):
        self.get(self.urls, parser=self.parse, sleep=0.2)

    def parse(self, response):
        """
        json:
        'content_type', 'charset', 'method', 'request_info', 'url',
        'status', 'cookies', 'headers', 'raw_headers', 'json', 'type'
        html:
        'content_type', 'charset', 'method', 'request_info', 'url', 'status',
        'cookies', 'headers', 'raw_headers', 'text', 'e_doc', 'p_doc', 'type',
        xpath(), selector()
        """
        if not response.status == 200:
            return

        houses = response.xpath('//*[@id="house-lst"]/li')
        count = 0
        for house_box in houses:
            count += 1
            title = house_box.xpath(
                '//li[{}]'.format(count) + '/div[2]/h2/a/text()')[0]
            self.logger.info(title)


if __name__ == "__main__":
    demo = LianjiaCrawler()
    demo.run()
