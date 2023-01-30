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
from urllib.parse import urljoin

# from ..items import ScraperItem
import datetime
import json
import requests
import random

# Class name will start _ and then lower case domain without extension and word Spider as follow
# '_'+DOMAIN_WITHOUT_EXT+'Spider'
class AHonestComSpider(scrapy.Spider):
    # spider name will start _ and then  lower case domain without extension as follow
    # '_'+DOMAIN_WITHOUT_EXT
    name = "_honestcom"
    allowed_domains = ["honest.com"]
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
        "https://www.honest.com/sitemap_0.xml",
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

                # We must assign random selected proxy to requests.get method. self.proxy_list is holding all proxies as a list.
                # proxy = random.choice(self.proxy_list)
                # proxies = {
                # "http": proxy,
                # "https": proxy,
                # }

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
                                # r = requests.get(l, headers=headers, proxies=proxies)
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
            if "/products/" in u:
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
                        '//a[contains(@class,"grid-view-item__link")]/@href'
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

        # Extract pagination links and yield them back to parse callback
        # Thus we hold all links in foundlinks array we can yield all pagination links not only next page as follows:
        # Pagination links also can be prepared with help of url parameters like offset page number and total product count.
        # If you need to calculate and manage pagination links be sure u are appending paginated links into self.foundlinks
        pages = list(
            filter(
                bool,
                [
                    response.urljoin(e.strip())
                    for e in response.xpath(
                        '//ul[contains(@class,"pagination")]//a[contains(@href,"page")]/@href'
                    ).extract()
                ],
            )
        )
        for page in pages:
            if not page in self.foundlinks:
                self.foundlinks.append(page)
                yield scrapy.Request(
                    page,
                    callback=self.parse,
                    meta={"category": response.url},
                    priority=1,
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
                            '//div[@class="product-title"]/h1/text()'
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
                            '"productType"]\s*=\s*"(.*?)"', response.text, re.DOTALL
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
                            '//div[@class="product-title"]/p/text()'
                        ).extract()
                    ],
                )
            ),
            "",
        )
        if item["price"] == "":
            item["price"] = next(
                iter(
                    filter(
                        bool,
                        [
                            e.replace("$", "").strip()
                            for e in response.xpath(
                                '//div[@class="product-title"]/p/s/text()'
                            ).extract()
                        ],
                    )
                ),
                "",
            )
            item["sales_price"] = next(
                iter(
                    filter(
                        bool,
                        [
                            e.replace("$", "").strip()
                            for e in response.xpath(
                                '//div[@class="product-title"]/p/span/text()'
                            ).extract()
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
                            for e in re.findall(
                                '<button\s*type="button"\s*aria-label="product-color-button"\s*data-color="([^"]*?)"(?:\>|\s*class="selected">)',
                                response.text,
                                re.DOTALL,
                            )
                        ],
                    )
                )
            )
        )  # colour will be populated with another request
        if item["colors"] == []:
            item["colors"] = list(
                set(
                    list(
                        filter(
                            bool,
                            [
                                e.strip()
                                for e in response.xpath(
                                    '//div[@class="option-block color"]/p/span/text()'
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
                            for e in re.findall(
                                '<button\s*type="button"\s*aria-label="Product Size Button"[^>]*?>\s*<span>([^>]*?)<\/span>',
                                response.text,
                                re.DOTALL,
                            )
                        ],
                    )
                )
            )
        )  # necklace_length will be populated with another request
        item["reviews"] = list(
            set(
                list(
                    filter(
                        bool,
                        [
                            e.strip()
                            for e in response.xpath(
                                '//div[@class="yotpo-review-wrapper"]/div[@class="content-review"]/text()'
                            ).extract()
                        ],
                    )
                )
            )
        )  # text as a list
        reviews_count = next(
            iter(
                filter(
                    bool,
                    [
                        e.strip()
                        .replace("Reviews", "")
                        .replace("Review", "")
                        .replace("Write a review", "")
                        for e in response.xpath(
                            '//div[@class="yotpo-bottomline pull-left  star-clickable"]/a/text()'
                        ).extract()
                    ],
                )
            ),
            "",
        )
        if reviews_count != "":
            item["reviews_count"] = int(reviews_count)  # total review count as integer
        item["rating"] = next(
            iter(
                filter(
                    bool,
                    [
                        e.replace("star rating", "").strip()
                        for e in response.xpath(
                            '//span[@class="yotpo-stars"]/span[@class="sr-only"]/text()'
                        ).extract()
                    ],
                )
            ),
            "",
        )  # star or review rating of product as string
        item["images"] = list(
            set(
                list(
                    filter(
                        bool,
                        [
                            e.strip()
                            for e in response.xpath(
                                '//nav[@class="product-thumbnails"]/figure/span/img/@src'
                            ).extract()
                        ],
                    )
                )
            )
        )
        item["images"] = [urljoin(response.url, img_url) for img_url in item["images"]]
        # Finally yielding item
        yield item
