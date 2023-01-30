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
class _nacrewatchescomSpider(Spider):
    # spider name will start _ and then  lower case domain without extension as follow

    # '_'+DOMAIN_WITHOUT_EXT
    name = "_nacrewatchescom"
    allowed_domains = ["nacrewatches.com"]
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
        "https://nacrewatches.com/sitemap.xml",
        "https://nacrewatches.com/collections/watches",
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
                        '//article[@class="product"]/a[@class="product-container"]/@href'
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
                            '//h1[@class="product-title"]//text()'
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
        item["colors"] = ""  # colour will be populated with another request
        item["sizes"] = ""  # necklace_length will be populated with another request
        item["reviews"] = list(
            set(
                list(
                    filter(
                        bool,
                        [
                            e.strip()
                            for e in response.xpath(
                                '//div[@class="yotpo-review yotpo-regular-box  "]/div[@class="yotpo-main "]//text()'
                            ).extract()
                        ],
                    )
                )
            )
        )
        item["reviews_count"] = next(
            iter(
                filter(
                    bool,
                    [
                        e.strip()
                        for e in response.xpath(
                            '//div[@class="numbers"]/span[@class="total"]//text()'
                        ).extract()
                    ],
                )
            ),
            "",
        )
        item["rating"] = next(
            iter(
                filter(
                    bool,
                    [
                        e.strip()
                        for e in response.xpath(
                            '//div[@class="numbers"]/span[@class="average"]//text()'
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
                                '//meta[@property="og:image"]/@content'
                            ).extract()
                        ],
                    )
                )
            )
        )

        # Finally yielding item
        yield item


# {'name': 'Lune 8 in Matte Black and White', 'url': 'https://nacrewatches.com/products/lune-8-matte-black-and-white-matte-black-mesh', 'category': 'Mesh-Watch', 'price': '240.00', 'colors': '', 'sizes': '', 'reviews': ['review stating Beautiful!', 'Beautiful!', 'review stating Beautiful Watch, very unique! Quality', 'Review by Janda M. on 26 May 2021', 'Review by Tyler H. on  3 Nov 2021', 'High Quality Watch', 'review stating One of the nicest things I own!', 'review stating Beautiful Watch, great quality.', 'Review by Lyle C. on 23 Apr 2021', 'Beautiful Watch, very unique! Quality made Product! Love the style and how it fits comfortably on my wrist', 'review stating High Quality Watch', 'On Lune 8 - Matte Black and White - Matte Black Mesh', 'Beautiful, high quality watch. Luxury touch for a fraction of the price. I purchased this for my wife on our anniversary as she doesn’t have any watches in her accessory collection. The order was shipped quickly to my home in Europe and would definitely recommend this watch as a gift.', 'Beautiful Watch, very unique! Quality', 'One of the nicest things I own!', 'I was absolutely blown away by what was delivered to me! I mean, I knew exactly what I was buying but holding it in my hands…. BEAUTIFUL! 10/10 and it just brings my whole look together! I’m so happy to be apart of this brand now and I look forward to purchasing more products in the near future for the up and coming holidays!', 'Fast shipping too!', 'Review by Nicholas M. on  3 Nov 2021', 'Review by Phillip M. on 17 Sep 2021', 'Beautiful Watch, great quality.'], 'reviews_count': '80', 'rating': '5', 'images': ['http://cdn.shopify.com/s/files/1/2729/5296/products/nacre_lune_8_matte_black_white_matte_black_mesh_front_1969af65-9bf4-4bd9-8ff8-259183f7c991_1024x1024.png?v=1555988638', 'http://cdn.shopify.com/s/files/1/2729/5296/products/nacre_lune_8_matte_black_mesh_side_product_grey_4233905f-cdf7-4670-99a7-22e47bcd0b5a_1024x1024.png?v=1555988638', 'https://s3.us-east-2.amazonaws.com/nacrecdn.nacrewatches.com/nacrewatches-opengraph-builder.png', 'http://cdn.shopify.com/s/files/1/2729/5296/products/nacre_lune_8_matte_black_white_matte_black_mesh_front_1024x1024.png?v=1555988638']}
