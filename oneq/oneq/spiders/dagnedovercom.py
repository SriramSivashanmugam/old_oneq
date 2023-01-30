# -*- coding: utf-8 -*-
from time import sleep
import scrapy
from scrapy.spiders import Spider, CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.http.request import Request
from scrapy.http import FormRequest
import logging
from scrapy.selector import Selector
import os.path
import sys
import re
from w3lib.html import remove_tags
import hashlib
from hashlib import md5
from ..items import ScraperItem
import datetime
import json
import requests
import random

# Class name will start _ and then lower case domain without extension and word Spider as follow
# '_'+DOMAIN_WITHOUT_EXT+'Spider'
class _dagnedovercomSpider(Spider):
    # spider name will start _ and then  lower case domain without extension as follow
    # '_'+DOMAIN_WITHOUT_EXT
    name = "_dagnedovercom"
    allowed_domains = ["dagnedover.com"]
    start_urls = ["https://www.dagnedover.com/sitemap.xml"]

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

    def __init__(self, *args, **kwargs):
        self.allowed_domains = (
            kwargs.get("allowed_domains", [])
            if kwargs.get("allowed_domains", [])
            else self.allowed_domains
        )
        # We need to add an aditional domain here where we will use in parse_options method
        self.allowed_domains.append("dagnedover.com")
        Spider.__init__(self, *args, **kwargs)

    def log(self, m):
        logging.error("custom_log:: %s" % m)
        print("custom_log:: %s" % m)

    def exception(self, msg=""):
        t, val, tb = sys.exc_info()
        self.log("custom_exception_log => %s : <%s> ! <%s> ! <%s>" % (msg, t, val, tb))
        return sys.exc_info()

    foundlinks = []
    proxy_list = []
    proxy_auth = {}

    def start_requests(self):
        # If given start_url is sitemap we will use PY requests module if this does not work we can try scrapy.Request object.
        for url in self.start_urls:
            if url.find(".xml") != -1:
                # This is an xml file so continue downloading it with requests module.
                # If we will start with given sitemap url we can open it with PY requests module.
                headers = {
                    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36",
                }

                try:
                    # Request with proxies is removed
                    # r = requests.get(url, headers=headers, proxies=proxies)
                    r = requests.get(url, headers=headers)
                    # Apply following pattern to extract all links from sitemap
                    pattern = "<loc>(.*?)</loc>"
                    m = re.findall(pattern, r.text, re.DOTALL)
                    i = 0
                    if len(m) > 0:
                        for l in m:
                            # Apply custom rule for each link found inside xml. If link is another xml file and contains products as follows
                            # send request to that xml too until we reach product html links.
                            if not l in self.foundlinks and l.find("products") != -1:
                                r = requests.get(l, headers=headers)
                                pattern = "<loc>(.*?)</loc>"
                                m = re.findall(pattern, r.text, re.DOTALL)
                                if len(m) > 0:
                                    for ll in m:
                                        # Be sure we are getting a product link which is not discovered before.
                                        if not ll in self.foundlinks:
                                            i += 1
                                            self.log("%d - %s" % (i, ll))
                                            self.foundlinks.append(ll.strip())
                    # Always use self.log function to print smth!
                    self.log("inside Xml FOUND LINK COUNT WITH PATTERN: %d" % (len(self.foundlinks)))
                except:
                    # Always use self.exception to catch messages!
                    self.exception("%s --> " % (url))
            else:
                # This is NOT an xml file we should yield request with scrapy.Request object with proper callback function.
                if url.find("/collections/") != -1:
                    # If given url is a search or category page we should yield it for parse method.
                    yield scrapy.Request(url, callback=self.parse)
                elif url.find("/product/") != -1:
                    # If given url is a single product page we should yield it for parse_product method.
                    yield scrapy.Request(url, callback=self.parse_product)
                else:
                    # If url is not any of above rules let's continue for next start_url .
                    continue

        # To make sure there are unique links inside foundlinks
        self.foundlinks = list(set(self.foundlinks))

        # If we are sure we found only product links we are yielding them to parse_product method.
        # If there are are some category or search links are inside foundlinks we must yield them to parse or parse_product methods respectively.
        for u in self.foundlinks:
            yield scrapy.Request(u, callback=self.parse_link_collection)

    def parse(self, response):
        # Extract product links from category or search pages
        # You must extract xpath of products on category or search pages.
        # You must keep following one line command and change ONLY xpath in it.
        product_links = list(filter(bool,[response.urljoin(e.strip()) for e in response.xpath('//div[@class="collection-row"]/div[@class="collection-products"]/a/@href').extract()],))

        for product_link in product_links:
            # Always be sure uniqueness before yielding new product link
            if not product_link in self.foundlinks:
                # Do not forget appending new product link into foundlinks list.
                self.foundlinks.append(product_link)
                # This is product link so callback must be parse_product.
                # If needed request.meta object can be used to pass extra information to parse_product method.
                # If we want to play with priorities product links must have biggest priority number. We should jump to product pages asap.
                yield scrapy.Request(product_link,callback=self.parse_product,meta={"category": response.url},priority=2,)

    def parse_link_collection(self, response):
        parse_link = next(iter(filter(bool,[e.strip() for e in re.findall('window\.location\.replace\("(.*?)"',response.text,re.DOTALL,)],)),"",)
        yield scrapy.Request(response.urljoin(parse_link), callback=self.parse_product)

    def parse_product(self, response):
        # First make sure this is a product page check title of product if there is no title return
        url = response.url

        name = next(iter(filter(bool,[e.strip() for e in response.xpath('//div[@id="product_title"]/h1//text()').extract()],)),"",)
        if not name:
            self.log("There is no Product Name for this product: %s" % url)
            return

        # Start preparing item
        
        item = ScraperItem()
        item["name"] = name
        item["url"] = url

        item["category"] = next(iter(filter(bool,[e.strip() for e in re.findall('"category":"(.*?)"', response.text, re.DOTALL)],)),"",)
        item["price"] = next(iter(filter(bool,[e.strip() for e in re.findall('Price:\s*"(.*?)"', response.text, re.DOTALL)],)),"",)
        item["colors"] = list(set(list(filter(bool,[e.strip() for e in re.findall("colortxt\s*\=\s*'(.*?)'", response.text, re.DOTALL)],))))
        item["sizes"] = list(set(list(filter(bool,[e.strip() for e in response.xpath('//div[@id="size-swatches"]/div/div/div/label//text()').extract()],))))
        item["reviews"] = list(set(list(filter(bool,[e.strip() for e in response.xpath('//div[@class="yotpo-main "]//text()').extract()],))))
        item["reviews_count"] = list(set(list(filter(bool,[e.replace(" Reviews ", "").strip() for e in response.xpath('//span[@class="reviews-amount"]//text()').extract()],))))
        item["rating"] = list(set(list(filter(bool,[e.replace(" star rating", "").strip() for e in response.xpath('//span[@class="yotpo-filter-stars rating-stars-container "]/span[@class="sr-only"]//text()').extract()],))))
        item["images"] = list(set(list(filter(bool,[e.strip() for e in response.xpath('//meta[@property="og:image"]/@content').extract()],))))

        # Finally yielding item
        yield item


# name,url,category,price,colors,sizes,reviews,reviews_count,rating,images
# Accordion Card Case,https://www.dagnedover.com/collections/the-accordion-card-case,Collection: the-accordion-card-case,$55.00,"Bone,Ash Blue,Graphite,Oxblood,Onyx",,"Melbourne, Australia,Everyday Essentials,0 of 5 rating,Location:,So Chic,I love this card case. It's sleek and minimal and holds everything I need without being too bulky. I keep about 6 cards in it and some cash. Quality is great.,Review by Nahal A. on 21 Aug 2021,review stating Perfect!,Sleek and Functional,Review by Quan H. on 25 Jun 2021,Review by Anonymous User,Best Wallet!,Jet-Setting, Weekend Wandering, Everyday Essentials,Monroe LA,review stating So Chic,Austin, Texas,review stating Fave wallet!,review stating Best Wallet!,On,I bought this little wallet so that I could carry just a couple cards with me at a time. I absolutely love it! It's well made, cute and truth be told I haven't carried around my actual wallet since purchasing this one.,Fits perfectly in your jean pocket too if you don't have enough things to pop into a bag,Chicago,review stating Sleek and Functional,Review by Ashley P. on  3 May 2021,Perfect!,I wish I would have known about DD before spending hundreds of dollars at a luxury brand for a canvas piece. This is soft leather, I’m able to get so many credit and loyalty cards in this cute little wallet.,Using For:,On Accordion Card Case in Onyx,Fave wallet!,Review by Amanda W. on 15 Jul 2021,So happy with this purchase. It holds multiple cards, and is so cute. It’s a must have!,San Francisco,Review by Alishia W. on  5 Nov 2021",161,4.7,//cdn.shopify.com/s/files/1/0260/1439/products/CC-Onyx-Front_medium.jpg?v=1627322789
