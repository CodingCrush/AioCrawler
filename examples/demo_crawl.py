from aiocrawl import AioCrawl


class DemoCrawl(AioCrawl):
    concurrency = 50
    urls = ("http://sh.lianjia.com/zufang/d{}".format(count) for count in range(1, 100))
    timeout = 30
    debug = True

    def on_start(self):
        self.get(self.urls, parser=self.parse, sleep=0.2)

    def parse(self, response):
        """
        json:
        'content_type', 'charset', 'method', 'request', 'url',
        'status', 'cookies', 'headers', 'raw_headers', 'json', 'type'
        html:
        'content_type', 'charset', 'method', 'request', 'url', 'status', 
        'cookies', 'headers', 'raw_headers', 'text', 'e_doc', 'p_doc', 'type',
        xpath(), selector()
        """
        if not response.status == 200:
            return

        self.logger.info(response.selector('#house-lst > li:nth-child(1) > div.info-panel > h2 > a'))

        houses = response.xpath('//*[@id="house-lst"]/li')
        count = 0
        for house_box in houses:
            count += 1
            title = house_box.xpath(
                '//li[{}]'.format(count) + '/div[2]/h2/a/text()')[0]
            self.logger.info(title)


if __name__ == "__main__":
    demo = DemoCrawl()
    demo()  # same as demo.run()
