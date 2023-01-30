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
class _tmobilecomSpider(Spider):
    # spider name will start _ and then  lower case domain without extension as follow
    # '_'+DOMAIN_WITHOUT_EXT
    name = "_tmobilecom"
    allowed_domains = ["t-mobile.com"]
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
        "https://www.t-mobile.com/cell-phones/brand/google",
    ]

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
        product_links = list(
            filter(
                bool,
                [
                    response.urljoin(e.strip())
                    for e in response.xpath(
                        "//a[contains(@class,'fx-colum')]/@href"
                    ).extract()
                ],
            )
        )
        self.log("number of products :%s" % product_links)
        for product_link in product_links:
            # Always be sure uniqueness before yielding new product link
            if not product_link in self.foundlinks:
                # Do not forget appending new product link into foundlinks list.
                self.foundlinks.append(product_link)
                # This is product link so callback must be parse_product.
                # If needed request.meta object can be used to pass extra information to parse_product method.
                # If we want to play with priorities product links must have biggest priority number. We should jump to product pages asap.
                self.log("Found product link: %s" % product_link)
                yield scrapy.Request(product_link, callback=self.parse_product)

    def parse_product(self, response):
        # First make sure this is a product page check title of product if there is no title return
        name = next(
            iter(
                filter(
                    bool,
                    [
                        e.strip()
                        for e in response.xpath(
                            '//h1[contains(@class,"family-name heading-6")]//text()'
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
                        for e in response.xpath(
                            '//ul/li[1]//span[@itemprop="name"]/text()'
                        ).extract()
                    ],
                )
            ),
            "",
        )
        item["price"] = list(
            set(
                list(
                    filter(
                        bool,
                        [
                            e.strip()
                            for e in re.findall(
                                '"price":"(.*?)"', response.text, re.DOTALL
                            )
                        ],
                    )
                )
            )
        )
        item["availablity"] = list(
            set(
                list(
                    filter(
                        bool,
                        [
                            e.strip()
                            for e in response.xpath(
                                "//div[contains(@class,'product-inventory-status')]//text()"
                            ).extract()
                        ],
                    )
                )
            )
        )

        item["memory"] = list(
            set(
                list(
                    filter(
                        bool,
                        [
                            e.strip()
                            for e in response.xpath(
                                "//span[@class='mat-radio-label-content']//text()"
                            ).extract()
                            if "GB" in e
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
                                "//label[@class='mat-radio-label']/span/span[@class='sr-only']//text()"
                            ).extract()
                        ],
                    )
                )
            )
        )
        item["images"] = list(
            set(
                list(
                    filter(
                        bool,
                        [
                            e.strip()
                            for e in response.xpath(
                                "//img[contains(@class,'preview-item')]/@src"
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
                        e.lower().replace("(", "").replace(")", "").strip()
                        for e in response.xpath(
                            "//tmo-star-rating/div/div[2]/text()"
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
                            "//tmo-star-rating/div/div[1]/text()"
                        ).extract()
                    ],
                )
            ),
            "",
        )
        # Finally yielding item
        yield item

        # Output:
        # {
        #     "name": "Pixel 6",
        #     "url": "https://www.t-mobile.com/cell-phone/google-pixel-6?sku=810029932646",
        #     "category": "Phones",
        #     "price": ["599.99"],
        #     "availablity": [
        #         "estimated ship date: November 23 - December 7",
        #         "On backorder,",
        #     ],
        #     "memory": ["128GB"],
        #     "colors": ["Stormy Black", "Sorta Seafoam"],
        #     "images": [
        #         "https://cdn.tmobile.com/content/dam/t-mobile/en-p/cell-phones/Google/Google-Pixel-6/Sorta-Seafoam/Google-Pixel-6-Sorta-Seafoam-backimage.png",
        #         "https://cdn.tmobile.com/content/dam/t-mobile/en-p/cell-phones/Google/Google-Pixel-6/Sorta-Seafoam/Google-Pixel-6-Sorta-Seafoam-frontimage.png",
        #         "https://cdn.tmobile.com/content/dam/t-mobile/en-p/cell-phones/Google/Google-Pixel-6/Sorta-Seafoam/Google-Pixel-6-Sorta-Seafoam-leftimage.png",
        #         "https://cdn.tmobile.com/content/dam/t-mobile/en-p/cell-phones/Google/Google-Pixel-6/Sorta-Seafoam/Google-Pixel-6-Sorta-Seafoam-rightimage.png",
        #     ],
        #     "reviews_count": "19",
        #     "rating": "3.6",
        # }
