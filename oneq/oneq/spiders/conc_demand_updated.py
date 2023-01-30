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
# from ..items import ScraperItem
import datetime
import json

# Class name will start _ and then lower case domain without extension and word Spider as follow
# '_'+DOMAIN_WITHOUT_EXT+'Spider'
class _allegroSpider(Spider):
    # spider name will start _ and then  lower case domain without extension as follow
    # '_'+DOMAIN_WITHOUT_EXT
    name = 'allegro_pl'
    allowed_domains = ['allegro.pl']
    custom_settings={
        'RETRY_ENABLED': True,
        'COOKIES_DEBUG': True,
        'COOKIES_ENABLED': True,
        'REDIRECT_ENABLED': True,
        'DOWNLOAD_DELAY': 1,
        'CONCURRENT_REQUESTS': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'DOWNLOAD_TIMEOUT':10,
        'LOG_LEVEL': 'DEBUG',
    }
    start_urls = [
        #'https://allegro.pl/kategoria/pieluszki-i-chusteczki-chusteczki-nawilzane-99393?offerTypeAuction=2'
    ]


    def __init__(self, *args, **kwargs):
        self.allowed_domains = kwargs.get('allowed_domains',[]) if kwargs.get('allowed_domains',[]) else self.allowed_domains
        Spider.__init__(self, *args, **kwargs)

    def log(self, m):
        logging.error('custom_log:: %s' % m)
        print('custom_log:: %s' % m)

    def exception(self, msg=''):
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
        product_links = list(filter(bool,[response.urljoin(e.strip()) for e in response.xpath('').extract()]))
        self.log("number of products :%s"%product_links)
        for product_link in product_links:
            # Always be sure uniqueness before yielding new product link
            if not product_link in self.foundlinks:
                # Do not forget appending new product link into foundlinks list.
                self.foundlinks.append(product_link)
                # This is product link so callback must be parse_product.
                # If needed request.meta object can be used to pass extra information to parse_product method.
                # If we want to play with priorities product links must have biggest priority number. We should jump to product pages asap.
                self.log('Found product link: %s' % product_link)
                yield scrapy.Request(product_link, callback=self.parse_product)

        next_pages = list(filter(bool,[response.urljoin(e.strip()) for e in response.xpath('').extract()]))
        total_number_of_products = list(filter(bool,[response.urljoin(e.strip()) for e in response.xpath('').extract()])) #get total number of products listed in category.
        self.log("total_number_of_products :%s"%total_number_of_products) #printout for debugging later
        for page in next_pages:
            if not page in self.foundlinks:
                self.foundlinks.append(page)
                self.log('Found product link: %s' % page)
                yield scrapy.Request(page, callback=self.parse)



    def parse_product(self, response):
        # First make sure this is a product page check title of product if there is no title return
        name = next(iter(filter(bool,[e.strip() for e in response.xpath('//h1[contains(@class,"product-name mt1")]//text()').extract()])),"")
        if not name:
            self.log('There is no Product Name for this product: %s' % response.url)
            return

        # Start preparing item
        item = ScraperItem()
        item["name"] = name
        item["url"] = response.url
        item["category"] = next(iter(filter(bool,[e.strip() for e in response.xpath('//div[@class="desktop-content"]//p[@class="affirm-as-low-as"]/@data-category').extract()])),"")
        item["price"] = next(iter(filter(bool,[e.strip() for e in response.xpath('//div[@class="desktop-content"]//span[@itemprop="price"]//text()').extract()])),"")
        item["colors"] = list(set(list(filter(bool,[e.strip() for e in response.xpath('//ul[@class="options swatches color"]/li/@data-selection-name').extract()]))))
        item["sizes"] = list(set(list(filter(bool,[e.strip() for e in response.xpath('//li[contains(@class,"size-swatch")]/span//text()').extract()]))))
        item["reviews"] = list(set(list(filter(bool,[e.strip() for e in response.xpath('//div[@class="content-review"]//text()').extract()]))))
        item["reviews_count"] = next(iter(filter(bool,[e.lower().replace('reviews','').replace('review','').strip() for e in response.xpath('//span[contains(@class,"reviews-qa-label ")]//text()').extract()])),"")
        item["rating"] = next(iter(filter(bool,[e.strip() for e in response.xpath('//span[contains(@class,"avg-score")]//text()').extract()])),"")
        item["images"] = list(set(list(filter(bool,[e.replace('sw=250&sh=250','sw=2000&sh=2000').strip() for e in response.xpath('//img[contains(@class,"productthumbnail")]/@src').extract()]))))
        print(item)
        # Finally yielding item
        yield item
