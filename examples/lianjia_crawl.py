from aiocrawl import AioCrawl
from lxml import etree


class LianjiaCrawl(AioCrawl):
    concurrency = 2
    urls = ("http://sh.lianjia.com/zufang/d{}".format(index)
            for index in range(1, 100))
    timeout = 10

    async def on_start(self):
        await self.get(self.urls, callback=self.fetch_houses, sleep=0.5)

    async def fetch_houses(self, response):
        if response.status == 200:
            text = await response.text()
            doc = etree.HTML(text)
            houses_select = '//*[@id="house-lst"]/li'
            houses = doc.xpath(houses_select)

            count = 0
            for house_box in houses:
                count += 1
                title = house_box.xpath(
                    '//li[{}]'.format(count) + '/div[2]/h2/a/text()')[0]
                print(title)


crawl = LianjiaCrawl()
crawl.run()
