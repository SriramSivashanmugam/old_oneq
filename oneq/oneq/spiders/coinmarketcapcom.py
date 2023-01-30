# homepage: https://coinmarketcap.com/

# template: conc_demand.py

# link to scrape: https://coinmarketcap.com/exchanges/binance/

# Fields to be scraped: information in the table: currency / pair / price / +2%Depth / ...

# Every line will be a row

# -*- coding: utf-8 -*-
import scrapy
from scrapy.http import request
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
class _coinmarketcapSpider(Spider):
    # spider name will start _ and then  lower case domain without extension as follow
    # '_'+DOMAIN_WITHOUT_EXT
    name = "_coinmarketcap"
    allowed_domains = ["coinmarketcap.com"]
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
        "https://api.coinmarketcap.com/data-api/v3/exchange/market-pairs/latest?slug=binance&category=spot&start=1&limit=1000"
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

        json_data = json.loads(response.text)
        market_datas = json_data["data"]["marketPairs"]
        total_count = json_data["data"]["numMarketPairs"]
        for data in market_datas:
            # item = {}
            item = ScraperItem()
            item["url"] = response.url
            item["currency"] = data.get("baseCurrencyName", "")
            item["marketPair"] = data.get("marketPair", "")
            item["Price"] = data.get("price", "")
            item["depth+2"] = data.get("depthUsdPositiveTwo", "")
            item["depth-2"] = data.get("depthUsdNegativeTwo", "")
            item["volume"] = data.get("volumeUsd", "")
            item["liquidity"] = data.get("effectiveLiquidity", "")
            item["updated"] = data.get("lastUpdated", "")
            yield item

        for count in range(int(total_count / 1000)):
            next_page = ("https://api.coinmarketcap.com/data-api/v3/exchange/market-pairs/latest?slug=binance&category=spot&start="+ str(count + 1)+ "001&limit=1000")
            yield scrapy.Request(next_page, callback=self.parse)


# {'url': 'https://api.coinmarketcap.com/data-api/v3/exchange/market-pairs/latest?slug=binance&category=spot&start=1001&limit=1000', 'currency': 'Tether', 'marketPair': 'USDT/GYEN', 'Price': 0.0, 'depth+2': 67.17192481, 'depth-2': 6453.50269198, 'volume': 0.0, 'liquidity': 755.0094708938318, 'updated': '2021-11-11T16:43:24.000Z'}

