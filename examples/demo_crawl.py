from aiocrawl import AioCrawl


class DemoCrawl(AioCrawl):
    concurrency = 2
    urls = ("http://sh.lianjia.com/zufang/d2",
            "http://api.bigsec.com/redq/v3/query/")
    timeout = 10
    debug = True

    async def on_start(self):
        await self.get(self.urls, callback=self.parse, sleep=1)

    async def parse(self, response):
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
        if response.type == "html":
            self.logger.info(response.selector('#house-lst > li:nth-child(1) > div.info-panel > h2 > a'))

            houses = response.xpath('//*[@id="house-lst"]/li')
            count = 0
            for house_box in houses:
                count += 1
                title = house_box.xpath(
                    '//li[{}]'.format(count) + '/div[2]/h2/a/text()')[0]
                self.logger.info(title)

        elif response.type == "json":
            self.logger.info(response.json)


if __name__ == "__main__":
    crawl = DemoCrawl()
    crawl.run()
