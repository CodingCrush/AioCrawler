from aiocrawl import AioCrawl


class DemoCrawl(AioCrawl):
    concurrency = 2
    urls = ("http://sh.lianjia.com/zufang/d2",
            "http://api.bigsec.com/redq/v3/query/")
    timeout = 10

    async def on_start(self):
        await self.get(self.urls, callback=self.parse, sleep=1)

    async def parse(self, response):
        """ json
        'content_type', 'charset', 'method', 'request', 'url',
        'status', 'cookies', 'headers', 'raw_headers', 'json', 'type'
        """
        """ html
        'content_type', 'charset', 'method', 'request', 'url', 'status', 
        'cookies', 'headers', 'raw_headers', 'text', 'doc', 'pq_doc', 'type',
        xpath(), css()
        """
        if not response.status == 200:
            return
        if response.type == "html":
            houses = response.xpath('//*[@id="house-lst"]/li')

            count = 0
            for house_box in houses:
                count += 1
                title = house_box.xpath(
                    '//li[{}]'.format(count) + '/div[2]/h2/a/text()')[0]
                print(title)
        elif response.type == "json":
            print(response.json)

crawl = DemoCrawl()
crawl.run()
