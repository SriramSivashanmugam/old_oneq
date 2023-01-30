# homepage: https://rothys.com/
# template: sample_sitemap.py
# sitemaps index: https://rothys.com/sitemap.xml
# sitemaps product: https://rothys.com/sitemap_products_1.xml?from=7905220038&to=6626475114590
# category page: https://rothys.com/collections/womens-shoes
# Extractor will extract products both from sitemap and category pages.
# Please copy sample template below and leave above comments as it is

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
from scrapy.selector import Selector
import datetime
import json
from urllib.parse import urljoin
import requests
import random


# Class name will start _ and then lower case domain without extension and word Spider as follow
# '_'+DOMAIN_WITHOUT_EXT+'Spider'


class RothysSpider(Spider):
    # spider name will start _ and then  lower case domain without extension as follow
    # '_'+DOMAIN_WITHOUT_EXT
    name = "_rothys"
    allowed_domains = ["rothys.com"]
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
        "https://rothys.com/sitemap.xml",
        "https://rothys.com/collections/all",
    ]

    def __init__(self, *args, **kwargs):
        self.allowed_domains = (
            kwargs.get("allowed_domains", [])
            if kwargs.get("allowed_domains", [])
            else self.allowed_domains
        )
        # We need to add an aditional domain here where we will use in parse_options method
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
                elif url.find("/products/") != -1:
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
                        '//a[@data-cy="product-card-link"]/@href'
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
        name = next(
            iter(
                filter(
                    bool,
                    [
                        e.strip()
                        for e in response.xpath(
                            '//p[@class="product-info__head__title h4--secondary align-c"]//text()'
                        ).extract()
                    ],
                )
            ),
            "",
        )
        if not name:
            self.log("There is no Product Name for this product: %s" % response.url)
            return

        # Start preparing item
        # item = ScraperItem()
        item = {}
        item["name"] = name
        item["url"] = response.url
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
                        e.replace("$", "").strip()
                        for e in response.xpath(
                            '//div[@class="product-cta__price w1 f jcc"]/ins/span[2]/text()'
                        ).extract()
                    ],
                )
            ),
            "",
        )
        item["sizes"] = list(
            set(
                list(
                    filter(
                        bool,
                        [
                            e.strip()
                            for e in response.xpath(
                                '//div[@class="product-sizes__single relative"]/span/text()'
                            ).extract()
                        ],
                    )
                )
            )
        )
        item["colors"] = list(
            set(
                list(
                    filter(
                        bool,
                        [
                            e.strip()
                            for e in response.xpath(
                                "//button[@data-color]/@data-color"
                            ).extract()
                        ],
                    )
                )
            )
        )
        item["reviews"] = list(
            set(
                list(
                    filter(
                        bool,
                        [
                            e.strip()
                            for e in response.xpath(
                                '//div[@class="review-content p1"]//text()'
                            ).extract()
                        ],
                    )
                )
            )
        )

        reviews_count = next(
            iter(
                filter(
                    bool,
                    [
                        e.replace("reviews", "")
                        .replace("(", "")
                        .replace(")", "")
                        .strip()
                        for e in response.xpath(
                            '//div[@class="count h6"]/p//text()'
                        ).extract()
                    ],
                )
            ),
            "",
        )  # total review count as integer
        if reviews_count != "":
            item["reviews_count"] = int(reviews_count)
        else:
            item["reviews_count"] = 0
        item["rating"] = next(
            iter(
                filter(
                    bool,
                    [
                        e.strip()
                        for e in response.xpath(
                            '//p[@class="average-score"]/text()'
                        ).extract()
                    ],
                )
            ),
            "",
        )
        item["images"] = list(
            set(
                list(
                    filter(
                        bool,
                        [
                            e.strip()
                            for e in response.xpath(
                                '//div[@class="img fit-cover is-loaded pos-center"]/img/@src'
                            ).extract()
                        ],
                    )
                )
            )
        )
        item["images"] = [urljoin(response.url, img_url) for img_url in item["images"]]
        # # Finally yielding item
        yield item


"""
{'name': 'The Slim Card Case', 'url': 'https://rothys.com/products/the-point-coral-dot', 'category': 'The Slim Card Case', 'price': '95', 'sizes': [], 'colors': ['woodland-camo', 'black', 'guava', 'forest', 'astro-grey'], 'reviews': ['The credit cards slide around in the wallet. I don’t think they will fall completely out but you will have to occasionally push them back in. The middle slot is a bit of a tight squeeze if you think you are going to put paper money in it, think again.', "I picked this up at the Rothy's store in NYC as a gift for my husband. He has carried wallets this style for as long as I can remember. Unlike the leather ones he has had over the years, this one is stretchy and makes it easier to get his cards in and out. He LOVES it! I'm going to try and get him addicted to the shoes next LOL", 'First experience on putting all my cards and cash on it was…”are thry gonna fall out?” Even my cards and cash didnt fall out. I meant is material doesnt structure the card case at all so it should not worth $95. $30 may be 😕', 'I love having just this tiny card case for my essentials. I don’t need to have all the bulk of other wallets when I have this case. It hold the few cards I need and conveniently fits in my shoulder bag. Love it - It’s just perfect.', 'A Perfect Place for Personal'], 'reviews_count': 5, 'rating': '4.2', 'images': ["./Credit Card Case in Astro Grey _ Rothy’s Men’s Accessories\xa0_ Rothy's_files/072_AstroGrey_pdp_B_43f77263-b9a0-409f-bd10-68826bfd27e9_1000x.jpg"]}
"""

