from aiocrawler import AioCrawler
from aiocrawler.request import random_navigator_headers


class LianjiaCrawler(AioCrawler):
    concurrency = 50
    urls = (
        "http://sh.lianjia.com/zufang/d{}".format(count)
        for count in range(1, 100)
    )
    timeout = 30
    headers = random_navigator_headers

    def on_start(self):
        self.get(self.urls, parser=self.parse, sleep=0.2)

    @staticmethod
    def parse(response):
        """
        json:
        'content_type', 'charset', 'method', 'request_info', 'url',
        'status', 'cookies', 'headers', 'raw_headers', 'json', 'type'
        html:
        'content_type', 'charset', 'method', 'request_info', 'url', 'status',
        'cookies', 'headers', 'raw_headers', 'text', 'e_doc', 'p_doc', 'type',
        xpath(), selector()
        """
        print(response.request_info)
        houses = response.xpath('//*[@id="house-lst"]/li')
        for index, house in enumerate(houses):
            title = house.xpath(
                '//li[{}]/div[2]/h2/a/text()'.format(index+1))[0]
            print("URL:{}, Title:{}".format(response.url, title))


if __name__ == "__main__":
    demo = LianjiaCrawler()
    demo.run()
