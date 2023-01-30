# -*- coding: utf-8 -*-
import scrapy
from scrapy.spiders import Spider, CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.http.request import Request
from scrapy.http import FormRequest
import logging
import os.path
import sys
import re
from w3lib.html import remove_tags
import hashlib
from hashlib import md5
from scrapy.selector import Selector

# from ..items import ScraperItem
import datetime
import json

# Class name will start _ and then lower case domain without extension and word Spider as follow
# '_'+DOMAIN_WITHOUT_EXT+'Spider'
class _attSpider(Spider):
    # spider name will start _ and then  lower case domain without extension as follow
    # '_'+DOMAIN_WITHOUT_EXT
    name = "attcomm"
    allowed_domains = ["att.com"]
    custom_settings = {
        "RETRY_ENABLED": True,
        "COOKIES_DEBUG": True,
        "COOKIES_ENABLED": True,
        "REDIRECT_ENABLED": True,
        "DOWNLOAD_DELAY": 1,
        "CONCURRENT_REQUESTS": 1,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "DOWNLOAD_TIMEOUT": 10,
        "LOG_LEVEL": "DEBUG",
    }
    start_urls = ["https://www.att.com/buy/phones/"]

    def __init__(self, *args, **kwargs):
        self.allowed_domains = (
            kwargs.get("allowed_domains", [])
            if kwargs.get("allowed_domains", [])
            else self.allowed_domains
        )
        Spider.__init__(self, *args, **kwargs)

    def log(self, m):
        logging.error("custom_log:: %s" % m)
        print("custom_log:: %s" % m)

    def exception(self, msg=""):
        t, val, tb = sys.exc_info()
        self.log("custom_exception_log => %s : <%s> ! <%s> ! <%s>" % (msg, t, val, tb))
        return sys.exc_info()

    foundlinks = []

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        # Extract product links from category or search pages ! This method will have all page source after click actions.
        # You must extract xpath of products on category or search pages.
        # You must keep following one line command and change ONLY xpath in it.
        product_links = list(filter(bool,[response.urljoin(e.strip()) for e in re.findall('"PDPPageURL"\:\["(.*?)"', response.text, re.DOTALL)],))

        for product_link in product_links:
            # Always be sure uniqueness before yielding new product link
            if not product_link in self.foundlinks:
                # Do not forget appending new product link into foundlinks list.
                self.foundlinks.append(product_link)
                # This is product link so callback must be parse_product.
                # If needed request.meta object can be used to pass extra information to parse_product method.
                # If we want to play with priorities product links must have biggest priority number. We should jump to product pages asap.
                self.log("Found product link: %s" % product_link)
        for u in self.foundlinks:
            yield scrapy.Request(u, callback=self.parse_product)

    def parse_product(self, response):
        # First make sure this is a product page check title of product if there is no title return
        url = response.url
        response1 = open('check.html','r',encoding='utf-8').read()
        response = Selector(text=response1)
        name = next(iter(filter(bool,[e.strip() for e in response.xpath('//h1[contains(@class,"heading")]//text()').extract()],)),"",)
        if not name:
            self.log("There is no Product Name for this product: %s" % url)
            return

        # Start preparing item
        item = ScraperItem()
        # item = {}
        item["name"] = name
        item["url"] = url
        item["Carrier"] = ""
        item["availability"] = ""
        item["retail_price"] = next(iter(filter(bool,[e.replace("$", "").strip() for e in response.xpath('//div[contains(text(),"Full retail price")]/parent::div/div/div/span[2]//text()').extract()],)),"",)
        item["installment_price"] = next(iter(filter(bool,[e.replace("$", "").strip() for e in response.xpath('//div[contains(text(),"Installment Plan")]/parent::div/div/div/span[2]//text()').extract()],)),"",)
        item["colors"] = list(set(list(filter(bool,[e.strip() for e in response.xpath('//fieldset[@id="Color"]/div/label/@for').extract()],))))
        item["memory"] = list(set(list(filter(bool,[e.strip() for e in response.xpath('//fieldset[@id="Capacity"]/div/div/label/div/div/div/div[1]//text()').extract()],))))
        item["reviews"] = list(set(list(filter(bool,[e.strip() for e in response.xpath('//div[@class="content-review"]//text()').extract()],))))
        item["reviews_count"] = next(iter(filter(bool,[e.strip() for e in re.findall('"reviewCount"\:"(.*?)"', response1, re.DOTALL)],)),"",)
        item["rating"] = next(iter(filter(bool,[e.strip() for e in re.findall('"ratingValue"\:"(.*?)"', response1, re.DOTALL)],)),"",)
        item["images"] = list(set(list(filter(bool,[(e.strip()) for e in response.xpath('//div[@id="accordion-content-gallery"]/div/div/img/@src').extract()],))))
        review_list = []
        for block in response.xpath('//ol[@class="bv-content-list bv-content-list-reviews"]/li'):
            review = {}
            review["review_name"] = block.xpath('.//*[@itemprop="author"]/span//text()').get()
            review["review_date"] = (block.xpath('.//div[@class="bv-content-datetime"]/span[2]//text()').get().replace(" \xa0", ""))
            review["review_text"] = block.xpath('.//div[@class="bv-content-summary-body-text"]/p//text()').get()
            review_list.append(review)

        item["reviews"] = review_list

        # Finally yielding item
        yield item


# {'name': 'Pixel 6 Pro', 'url': 'https://www.att.com/buy/phones/apple-iphone-13-pro-max-128gb-sierra-blue.html', 'Carrier': '', 'availability': '', 'retail_price': '939.99', 'installment_price': '26.12', 'colors': ['CloudyWhite', 'StormyBlack'], 'memory': ['128 GB'], 'reviews': [{'review_name': 'Crig316', 'review_date': 'a day ago', 'review_text': "Amazing phone. Probably the best phone I've ever owned. Awesome pictures"}, {'review_name': 'Anonymous', 'review_date': '9 days ago', 'review_text': "My Pixel 6 Pro is absolutely beautiful and amazing. The operating system is amazing, the camera's are top of the line. The hardware is awesome. Annnnnnnnd, the prices compared to other flagship smartphones can't be beat. No phone is perfect, but the Pixel 6 and Pixel 6 Pro are close!"}, {'review_name': 'JC Ace', 'review_date': '9 days ago', 'review_text': 'This phone exceeded my expectations. They put a lot of thoughts behind the day to day user needs.'}, {'review_name': 'Anayaz Sam', 'review_date': '8 days ago', 'review_text': 'Best Phone in the World right now'}], 'reviews_count': '64', 'rating': '4.6', 'images': ['./check_files/6074D-2.jpg', './check_files/6074D-5.jpg', './check_files/6074D-3.jpg', './check_files/6074D-4.jpg', './check_files/6074D-6.jpg', './check_files/6074D-7.jpg', './check_files/6074D-1.jpg']}

