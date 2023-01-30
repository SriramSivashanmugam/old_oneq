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
import requests
import random


# Class name will start _ and then lower case domain without extension and word Spider as follow

# '_'+DOMAIN_WITHOUT_EXT+'Spider'
class _rainscomSpider(Spider):
    # spider name will start _ and then  lower case domain without extension as follow

    # '_'+DOMAIN_WITHOUT_EXT
    name = "_rainscom"
    allowed_domains = ["rains.com"]
    # You can assign custom settings if needed.
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
    start_urls = [
        "https://www.us.rains.com/sitemap.xml",
        "https://www.rains.com/collections/women",
    ]

    def __init__(self, *args, **kwargs):
        self.allowed_domains = (
            kwargs.get("allowed_domains", [])
            if kwargs.get("allowed_domains", [])
            else self.allowed_domains
        )
        # We need to add an aditional domain here where we will use in parse_options method
        self.allowed_domains.append("nacrewatches.com")
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

                # We must assign random selected proxy to requests.get method. self.proxy_list is holding all proxies as a list.

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
                    self.log(
                        "inside Xml FOUND LINK COUNT WITH PATTERN: %d"
                        % (len(self.foundlinks))
                    )
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
            yield scrapy.Request(u, callback=self.parse_product)

    def parse(self, response):
        # Extract product links from category or search pages
        # You must extract xpath of products on category or search pages.
        # You must keep following one line command and change ONLY xpath in it.
        product_links = list(
            filter(
                bool,
                [
                    response.urljoin(e.strip())
                    for e in response.xpath(
                        '//div[@class="product-item product-item--alt"]/a/@href'
                    ).extract()
                ],
            )
        )

        for product_link in product_links:
            # Always be sure uniqueness before yielding new product link
            if not product_link in self.foundlinks:
                # Do not forget appending new product link into foundlinks list.
                self.foundlinks.append(product_link)
                # This is product link so callback must be parse_product.
                # If needed request.meta object can be used to pass extra information to parse_product method.
                # If we want to play with priorities product links must have biggest priority number. We should jump to product pages asap.
                yield scrapy.Request(
                    product_link,
                    callback=self.parse_product,
                    meta={"category": response.url},
                    priority=2,
                )

    def parse_product(self, response):
        # First make sure this is a product page check title of product if there is no title return
        url = response.url

        name = next(
            iter(
                filter(
                    bool,
                    [
                        e.strip()
                        for e in response.xpath(
                            '//h1[@class="product__title"]//text()'
                        ).extract()
                    ],
                )
            ),
            "",
        )
        if not name:
            self.log("There is no Product Name for this product: %s" % url)
            return

        # Start preparing item
        # item = ScraperItem()
        item = {}
        item["name"] = name
        item["url"] = url
        item["category"] = next(
            iter(
                filter(
                    bool,
                    [
                        e.strip()
                        for e in re.findall(
                            '"category":"(.*?)"', response.text, re.DOTALL
                        )
                    ],
                )
            ),
            "",
        )
        item["price"] = next(
            iter(
                filter(
                    bool,
                    [
                        e.strip()
                        for e in re.findall('"price":"(.*?)"', response.text, re.DOTALL)
                    ],
                )
            ),
            "",
        )
        item["colors"] = list(
            set(
                list(
                    filter(
                        bool,
                        [
                            e.strip()
                            for e in response.xpath(
                                '//div[@class="product__swatches"]/fieldset/div/div/label/span[@class="sr-only"]//text()'
                            ).extract()
                        ],
                    )
                )
            )
        )
        item["sizes"] = list(
            set(
                list(
                    filter(
                        bool,
                        [
                            e.strip()
                            for e in response.xpath(
                                '//legend[contains(text(),"Size")]/parent::fieldset/div/div/label/span//text()'
                            ).extract()
                        ],
                    )
                )
            )
        )
        item["reviews"] = ""  # No reviewer review the product
        item["reviews_count"] = ""  # review count is not available
        item["rating"] = ""  # rating is not available
        item["images"] = list(
            set(
                list(
                    filter(
                        bool,
                        [
                            e.strip()
                            for e in response.xpath(
                                '//div[@class="product__images"]/div/div/div/div/@data-zoom'
                            ).extract()
                        ],
                    )
                )
            )
        )

        # Finally yielding item
        yield item


# {'name': 'Mittens Quilted', 'url': 'https://www.us.rains.com/products/mittens-quilted', 'category': 'Gloves and Mittens', 'price': '42.00', 'colors': ['Velvet Black', 'Slate', 'Velvet Taupe'], 'sizes': ['S', 'L', 'M'], 'reviews': '', 'reviews_count': '', 'rating': '', 'images': ['//cdn.shopify.com/s/files/1/0250/8090/products/Mittens_20Quilted-Gloves_20and_20Mittens-1671-05_20Slate-5.jpg?v=1623232448', '//cdn.shopify.com/s/files/1/0250/8090/products/Mittens_20Quilted-Gloves_20and_20Mittens-1671-05_20Slate-1.jpg?v=1623232437', '//cdn.shopify.com/s/files/1/0250/8090/products/Mittens_20Quilted-Gloves_20and_20Mittens-1671-05_20Slate-4.jpg?v=1623232445', '//cdn.shopify.com/s/files/1/0250/8090/products/Mittens_20Quilted-Gloves_20and_20Mittens-1671-05_20Slate-6.jpg?v=1623232451', '//cdn.shopify.com/s/files/1/0250/8090/products/Mittens_20Quilted-Gloves_20and_20Mittens-1671-05_20Slate-2.jpg?v=1623232440']}
