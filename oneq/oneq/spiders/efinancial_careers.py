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
import pdb

# from ..items import ScraperItem
import datetime
import json

# Class name will start _ and then lower case domain without extension and word Spider as follow
# '_'+DOMAIN_WITHOUT_EXT+'Spider'


class EfinancialcareersSpider(Spider):
    # spider name will start _ and then  lower case domain without extension as follow
    # '_'+DOMAIN_WITHOUT_EXT
    name = "_efinancialcareers"
    allowed_domains = ["efinancialcareers.com"]
    custom_settings = {
        "RETRY_ENABLED": True,
        "COOKIES_DEBUG": True,
        "COOKIES_ENABLED": False,
        "REDIRECT_ENABLED": True,
        "DOWNLOAD_DELAY": 1,
        "CONCURRENT_REQUESTS": 1,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "DOWNLOAD_TIMEOUT": 10,
        "LOG_LEVEL": "DEBUG",
    }
    start_urls = [
        "https://job-search-api.efinancialcareers.com/v1/efc/jobs/search?q=financial%20analyst&locationPrecision=City&latitude=40.4862157&longitude=-74.4518188&countryCode2=US&radius=50&radiusUnit=mi&page=1&pageSize=100&facets=employmentType%7Csectors%7CpositionType%7CexperienceLevel%7CsalaryBand%7CpostedDate%7CjobSource%7ClocationPath&currencyCode=USD&fields=id%7CjobId%7Csummary%7Ctitle%7CpostedDate%7CjobLocation.displayName%7CdetailsPageUrl%7Csalary%7CclientBrandId%7CcompanyPageUrl%7CcompanyLogoUrl%7CpositionId%7CcompanyName%7CemploymentType%7CisHighlighted%7Cscore%7CeasyApply%7CemployerType%7CworkFromHomeAvailability%7CisRemote&culture=en&recommendations=true&interactionId=0&fj=false&includeRemote=true"
    ]
    headers = {
        "authority": "job-search-api.efinancialcareers.com",
        "sec-ch-ua": '"Google Chrome";v="95", "Chromium";v="95", ";Not A Brand";v="99"',
        "accept": "application/json, text/plain, */*",
        "sec-ch-ua-mobile": "?0",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36",
        "x-api-key": "zvDFWwKGZ07cpXWV37lpO5MTEzXbHgyL4rKXb39C",
        "sec-ch-ua-platform": '"Linux"',
        "origin": "https://www.efinancialcareers.com",
        "sec-fetch-site": "same-site",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
        "referer": "https://www.efinancialcareers.com/",
        "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    }

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

    def start_requests(self):
        url = "https://job-search-api.efinancialcareers.com/v1/efc/jobs/search?q=financial%20analyst&locationPrecision=City&latitude=40.4862157&longitude=-74.4518188&countryCode2=US&radius=50&radiusUnit=mi&page=1&pageSize=100&facets=employmentType%7Csectors%7CpositionType%7CexperienceLevel%7CsalaryBand%7CpostedDate%7CjobSource%7ClocationPath&currencyCode=USD&fields=id%7CjobId%7Csummary%7Ctitle%7CpostedDate%7CjobLocation.displayName%7CdetailsPageUrl%7Csalary%7CclientBrandId%7CcompanyPageUrl%7CcompanyLogoUrl%7CpositionId%7CcompanyName%7CemploymentType%7CisHighlighted%7Cscore%7CeasyApply%7CemployerType%7CworkFromHomeAvailability%7CisRemote&culture=en&recommendations=true&interactionId=0&fj=false&includeRemote=true"
        yield scrapy.Request(url=url, headers=self.headers, callback=self.parse)

    def parse(self, response):

        json_data = json.loads(response.text)
        for i in json_data["data"]:
            item = {}
            # item = ScraperItem()
            item["title"] = i.get("title", "")
            item["job_location"] = i["jobLocation"]["displayName"]
            detail_url = i.get("detailsPageUrl", "")
            item["detail_url"] = "https://www.efinancialcareers.com" + detail_url
            item["company_name"] = i.get("companyName", "")
            item["employment_type"] = i.get("employmentType", "")
            item["company_name"] = i.get("companyName", "")
            item["summary"] = i.get("summary", "")
            item["logo"] = i.get("companyLogoUrl", "")
            item["salary"] = i.get("salary", "")
            yield item
        if "json_data['_links']['next']['href']":
            next_page = json_data["_links"]["next"]["href"]
            next_pag = response.urljoin(next_page)
            yield scrapy.Request(
                url=next_pag, callback=self.parse, headers=self.headers
            )
