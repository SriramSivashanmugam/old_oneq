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
import requests
import pdb
import random

#from ..items import ScraperItem
import datetime
import json

# Class name will start _ and then lower case domain without extension and word Spider as follow
# '_'+DOMAIN_WITHOUT_EXT+'Spider'
class _verizonSpider(Spider):
    # spider name will start _ and then  lower case domain without extension as follow
    # '_'+DOMAIN_WITHOUT_EXT
    name = "_verizon"
    allowed_domains = ["verizon.com"]
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
    start_urls = ["https://www.verizon.com/smartphones"]

    user_agent_list = [
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4611.59 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4596.210 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4620.198 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4620.58 Safari/537.36",
        "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4619.89 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4605.169 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4602.107 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4589.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4603.200 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4595.195 Safari/537.36",
        "Mozilla/5.0 (X11; U; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/93.0.4587.119 Chrome/93.0.4587.119 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4637.168 Safari/537.36",
        "Mozilla/5.0 (X11; U; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4600.187 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4633.209 Safari/537.36",
    ]

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "If-None-Match": 'W/"71511-fiDw+hWeGWUcHNTM1hlTCWT1LH8"',
        "Host": "www.verizon.com",
        "User-Agent": random.choice(user_agent_list),
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

    foundlinks = []

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url, headers=self.headers, callback=self.parse)

    def parse(self, response):
        # Extract product links from category or search pages ! This method will have all page source after click actions.
        # You must extract xpath of products on category or search pages.
        # You must keep following one line command and change ONLY xpath in it.
        product_links = list(filter(bool,[(e.strip())for e in response.xpath('//div[@class="Tile__PromoBanner-sc-71g958-1 jBphua hidePromo"]/following-sibling::a/@href').extract()],))
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

        # Next page links are extracted below
        if response.xpath('//span[contains(text(),"Next")]/parent::a/@href'):
            next_page_urls = (response.xpath('//span[contains(text(),"Next")]/parent::a/@href').get("").strip())
            if not next_page_urls in self.foundlinks:
                self.foundlinks.append(next_page_urls)
                yield scrapy.Request(next_page_urls, callback=self.parse)

    def parse_product(self, response):
        # First make sure this is a product page check title of product if there is no title return
        device_name = next(iter(filter(bool,[e.strip()for e in response.xpath('//div[@class="TitleComponent__TitleWrapper-sc-8s9jvf-0 grDZTB"]/h3/div/text()').extract()],)),"",)

        if not device_name:
            self.log("There is no Product Name for this product: %s" % response.url)
            return

        # Start preparing item
        json_details = re.findall("window\.APP_STATE\s*\=\s*([\w\W]*?\})\;", response.text)[0]
        json_data = json.loads(json_details)
        # item = ScraperItem()
        item = {}
        item["device_name"] = device_name
        item["url"] = response.url
        item["category"] = next(iter(filter(bool,[e.strip()for e in re.findall('"productDetails"\:\{"category"\:"([\w\W]*?)"\,"categoryId"',response.text,re.DOTALL,)],)),"",)

        color_codes = response.xpath('//span/input[@class="StyledRadio-sc-143q3d-5 cNGztb"]/@value').getall()
        
        storage = json_data["pdp"]["productDetails"]["productSpecification"]["Performance"]["Storage"]

        try:
            if len(storage.split("|")) == 2:
                ram_size = storage.split("|")[0]            
                item["ram_variant"] = list(set(list(filter(bool,[ram_size],))))
                       
            elif len(storage.split("+")) == 2:
                ram_size = storage.split("+")[1].strip()
                item["ram_variant"] = list(set(list(filter(bool,[ram_size],))))
                
            elif len(storage.split("+")) == 3:
                ram_size = storage.split("+")[0].strip()
                item["ram_variant"] = list(set(list(filter(bool,[ram_size],))))

        except:
            item["memory_variant"] = ""
            item["ram_variant"] = ""

        prices = []
        availabilty = []
        color = []
        image = []
        for color_code in color_codes:
            price_dict = {}
            color_dict = {}
            try:
                color_var = (json_data.get("pdp", "").get("productDetails", "").get("productSkus", "").get("new", "").get(color_code, "").get("color", "").get("label", ""))
                color_dict["color"] = (json_data.get("pdp", "").get("productDetails", "").get("productSkus", "").get("new", "").get(color_code, "").get("color", "").get("label", ""))

            except:
                color_dict["color"] = ""
            try:
                color_dict["images"] = (json_data.get("pdp", "").get("productDetails", "").get("productSkus", "").get("new", "").get(color_code, "").get("images", "")[0])
                # image.append(images)

            except:
                color_dict["images"] = ""

            try:
                price_dict["installment_30_month_price_128gb"] = (json_data.get("pdp", "").get("productDetails", "").get("productSkus", "").get("new", "").get(color_code, "").get("dpp30", "").get("128", "").get("price", "").get("originalPrice", ""))
                if (json_data.get("pdp", "").get("productDetails", "").get("productSkus", "").get("new", "").get(color_code, "").get("dpp30", "").get("128", "").get("capacity", "")):
                    price_dict["memory_30months_128gb"] = "128 GB" 
                price_dict["avaiablity_30months_128gb"] = (json_data.get("pdp", "").get("productDetails", "").get("productSkus", "").get("new", "").get(color_code, "").get("dpp30", "").get("128", "").get("inStock", ""))
            except:
                price_dict["installment_30_month_price_128gb"] = ""
                price_dict["memory_30months_128gb"] = ""
                price_dict["avaiablity_30months_128gb"] = False
            try:
                price_dict["installment_24_month_price_128gb"] = (json_data.get("pdp", "").get("productDetails", "").get("productSkus", "").get("new", "").get(color_code, "").get("dpp24", "").get("128", "").get("price", "").get("originalPrice", ""))
                if(json_data.get("pdp", "").get("productDetails", "").get("productSkus", "").get("new", "").get(color_code, "").get("dpp24", "").get("128", "").get("capacity", "")):
                    price_dict["memory_24months_128gb"] = "128 GB"
                price_dict["avaiablity_24months_128gb"] = (json_data.get("pdp", "").get("productDetails", "").get("productSkus", "").get("new", "").get(color_code, "").get("dpp24", "").get("128", "").get("inStock", ""))
            except:
                price_dict["installment_24_month_price"] = ""
                price_dict["memory_24months_128gb"] = ""
                price_dict["avaiablity_24months_128gb"] = False
            try:
                price_dict["full_retail_price_128gb"] = (json_data.get("pdp", "").get("productDetails", "").get("productSkus", "").get("new", "").get(color_code, "").get("frp", "").get("128", "").get("price", "").get("originalPrice", ""))
                if(json_data.get("pdp", "").get("productDetails", "").get("productSkus", "").get("new", "").get(color_code, "").get("frp", "").get("128", "").get("capacity", "")):
                    price_dict["full_retail_memory_128gb"] = "128 GB"
                price_dict["full_retail_avaiablity_128gb"] = (json_data.get("pdp", "").get("productDetails", "").get("productSkus", "").get("new", "").get(color_code, "").get("frp", "").get("128", "").get("inStock", ""))
            except:
                price_dict["full_retail_price_128gb"] = ""
                price_dict["full_retail_memory_128gb"] = ""
                price_dict["full_retail_avaiablity_128gb"] = False
            try:
                price_dict["installment_30_month_price_256gb"] = (json_data.get("pdp", "").get("productDetails", "").get("productSkus", "").get("new", "").get(color_code, "").get("dpp30", "").get("256", "").get("price", "").get("originalPrice", ""))
                if(json_data.get("pdp", "").get("productDetails", "").get("productSkus", "").get("new", "").get(color_code, "").get("dpp30", "").get("256", "").get("capacity", "")):
                    price_dict["memory_30months_256gb"] = "256 GB"
                price_dict["avaiablity_30months_256gb"] = (json_data.get("pdp", "").get("productDetails", "").get("productSkus", "").get("new", "").get(color_code, "").get("dpp30", "").get("256", "").get("inStock", ""))
            except:
                price_dict["installment_30_month_price_256gb"] = ""
                price_dict["memory_30months_256gb"] = ""
                price_dict["avaiablity_30months_256gb"] = False
            try:
                price_dict["installment_24_month_price_256gb"] = (json_data.get("pdp", "").get("productDetails", "").get("productSkus", "").get("new", "").get(color_code, "").get("dpp24", "").get("256", "").get("price", "").get("originalPrice", ""))
                if(json_data.get("pdp", "").get("productDetails", "").get("productSkus", "").get("new", "").get(color_code, "").get("dpp24", "").get("256", "").get("capacity", "")):
                    price_dict["memory_24months_256gb"] = "256 GB"
                price_dict["avaiablity_24months_256gb"] = (json_data.get("pdp", "").get("productDetails", "").get("productSkus", "").get("new", "").get(color_code, "").get("dpp24", "").get("256", "").get("inStock", ""))
            except:
                price_dict["installment_24_month_price_256gb"] = ""
                price_dict["memory_24months_256gb"] = ""
                price_dict["avaiablity_24months_256gb"] = False
            try:
                price_dict["full_retail_price_256gb"] = (json_data.get("pdp", "").get("productDetails", "").get("productSkus", "").get("new", "").get(color_code, "").get("frp", "").get("256", "").get("price", "").get("originalPrice", ""))
                if(json_data.get("pdp", "").get("productDetails", "").get("productSkus", "").get("new", "").get(color_code, "").get("frp", "").get("256", "").get("capacity", "")):
                    price_dict["full_retail_memory_256gb"] = "256 GB"
                price_dict["full_retail_avaiablity_256gb"] = (json_data.get("pdp", "").get("productDetails", "").get("productSkus", "").get("new", "").get(color_code, "").get("frp", "").get("256", "").get("inStock", ""))
            except:
                price_dict["full_retail_price_256gb"] = ""
                price_dict["full_retail_memory_256gb"] = ""
                price_dict["full_retail_avaiablity_256gb"] = False
            try:
                price_dict["installment_30_month_price_512gb"] = (json_data.get("pdp", "").get("productDetails", "").get("productSkus", "").get("new", "").get(color_code, "").get("dpp30", "").get("512", "").get("price", "").get("originalPrice", ""))
                if(json_data.get("pdp", "").get("productDetails", "").get("productSkus", "").get("new", "").get(color_code, "").get("dpp30", "").get("512", "").get("capacity", "")):
                    price_dict["memory_30months_512gb"] = "512 GB" 
                price_dict["avaiablity_30months_512gb"] = (json_data.get("pdp", "").get("productDetails", "").get("productSkus", "").get("new", "").get(color_code, "").get("dpp30", "").get("512", "").get("inStock", ""))
            except:
                price_dict["installment_30_month_price_512gb"] = ""
                price_dict["memory_30months_512gb"] = ""
                price_dict["avaiablity_30months_512gb"] = False
            try:
                price_dict["installment_24_month_price_512gb"] = (json_data.get("pdp", "").get("productDetails", "").get("productSkus", "").get("new", "").get(color_code, "").get("dpp24", "").get("512", "").get("price", "").get("originalPrice", ""))
                if(json_data.get("pdp", "").get("productDetails", "").get("productSkus", "").get("new", "").get(color_code, "").get("dpp24", "").get("512", "").get("capacity", "")):
                    price_dict["memory_24months_512gb"] = "512 GB"
                price_dict["avaiablity_24months_512gb"] = (json_data.get("pdp", "").get("productDetails", "").get("productSkus", "").get("new", "").get(color_code, "").get("dpp24", "").get("512", "").get("inStock", ""))
            except:
                price_dict["installment_24_month_price_512gb"] = ""
                price_dict["memory_24months_512gb"] = ""
                price_dict["avaiablity_24months_512gb"] = False
            try:
                price_dict["full_retail_price_512gb"] = (json_data.get("pdp", "").get("productDetails", "").get("productSkus", "").get("new", "").get(color_code, "").get("frp", "").get("512", "").get("price", "").get("originalPrice", ""))
                if(json_data.get("pdp", "").get("productDetails", "").get("productSkus", "").get("new", "").get(color_code, "").get("frp", "").get("512", "").get("capacity", "")):
                    price_dict["full_retail_memory_512gb"] = "512 GB"
                price_dict["full_retail_avaiablity_512gb"] = (json_data.get("pdp", "").get("productDetails", "").get("productSkus", "").get("new", "").get(color_code, "").get("frp", "").get("512", "").get("inStock", ""))
            except:
                price_dict["full_retail_price_512gb"] = ""
                price_dict["full_retail_memory_512gb"] = ""
                price_dict["full_retail_avaiablity_512gb"] = False

            color_dict.update(price_dict)
            color.append(color_dict)
               
        item["color_variant"] = color
        product_id = json_data["pdp"]["productDetails"]["productId"]
        pass_key = json_data["pdp"]["reviewDetails"]["passKey"]

        review_api_url = f"https://api.bazaarvoice.com/data/reviews.json?apiversion=5.4&passkey={pass_key}&include=Products&stats=Reviews&Filter=ProductId:{product_id}&Sort=rating:desc&Limit=100&Offset=0"
        reviews_json = requests.get(review_api_url)
        review_json = json.loads(reviews_json.text)
        rating = review_json["Includes"]["Products"][product_id]["ReviewStatistics"]["AverageOverallRating"]
        total_review_count = review_json["TotalResults"]
        reviews = []
        if total_review_count <= 100:
            for count, i in enumerate(range(total_review_count)):
                review_dict = {}
                review = review_json["Results"][i]["ReviewText"]
                if review:
                    review = re.sub(r"r\n\r\n", "", review)
                    review = re.sub(r"\r\n", "", review)
                    review_dict["review_text"] = review
                else:
                    review_dict["review_text"] = ""
                review_dict["review_date"] = review_json["Results"][i]["SubmissionTime"]
                review_dict["reviewer_name"] = review_json["Results"][i]["UserNickname"]
                reviews.append(review_dict)
        else:
            for count, i in enumerate(range(0, 100)):
                review_dict = {}
                review = review_json["Results"][i]["ReviewText"]
                if review:
                    review = re.sub(r"r\n\r\n", "", review)
                    review = re.sub(r"\r\n", "", review)
                    review_dict["review_text"] = review
                else:
                    review_dict["review_text"] = ""
                review_dict["review_date"] = review_json["Results"][i]["SubmissionTime"]
                review_dict["review_name"] = review_json["Results"][i]["UserNickname"]
                reviews.append(review_dict)

        item["reviews"] = reviews
        item["reviews_count"] = next(iter(filter(bool,[total_review_count],)),"",)
        item["rating"] = next(iter(filter(bool,[rating],)),"",)
        item["carrier"] = ""  # Carrier field is not available in the Site
        pdb.set_trace()
        print(item)
        # Finally yielding item
        yield item

    #output {'device_name': 'Apple iPhone 12', 'url': 'https://www.verizon.com/smartphones/apple-iphone-12/', 'category': 'Device', 'color_variant': [{'color': 'Purple', 'images': 'https://ss7.vzw.com/is/image/VerizonWireless/apple-iphone-12-64gb-purple-53017-mjn13ll-a', 'installment_30_month_price_128gb': 24.99, 'memory_30months_128gb': '128 GB', 'avaiablity_30months_128gb': True, 'installment_24_month_price_128gb': 31.24, 'memory_24months_128gb': '128 GB', 'avaiablity_24months_128gb': True, 'full_retail_price_128gb': 749.99, 'full_retail_memory_128gb': '128 GB', 'full_retail_avaiablity_128gb': True, 'installment_30_month_price_256gb': 28.33, 'memory_30months_256gb': '256 GB', 'avaiablity_30months_256gb': True, 'installment_24_month_price_256gb': 35.41, 'memory_24months_256gb': '256 GB', 'avaiablity_24months_256gb': True, 'full_retail_price_256gb': 849.99, 'full_retail_memory_256gb': '256 GB', 'full_retail_avaiablity_256gb': True, 'installment_30_month_price_512gb': '', 'memory_30months_512gb': '', 'avaiablity_30months_512gb': False, 'installment_24_month_price_512gb': '', 'memory_24months_512gb': '', 'avaiablity_24months_512gb': False, 'full_retail_price_512gb': '', 'full_retail_memory_512gb': '', 'full_retail_avaiablity_512gb': False}, {'color': 'Blue', 'images': 'https://ss7.vzw.com/is/image/VerizonWireless/apple-iphone-12-blue-10132020', 'installment_30_month_price_128gb': 24.99, 'memory_30months_128gb': '128 GB', 'avaiablity_30months_128gb': True, 'installment_24_month_price_128gb': 31.24, 'memory_24months_128gb': '128 GB', 'avaiablity_24months_128gb': True, 'full_retail_price_128gb': 749.99, 'full_retail_memory_128gb': '128 GB', 'full_retail_avaiablity_128gb': True, 'installment_30_month_price_256gb': 28.33, 'memory_30months_256gb': '256 GB', 'avaiablity_30months_256gb': True, 'installment_24_month_price_256gb': 35.41, 'memory_24months_256gb': '256 GB', 'avaiablity_24months_256gb': True, 'full_retail_price_256gb': 849.99, 'full_retail_memory_256gb': '256 GB', 'full_retail_avaiablity_256gb': True, 'installment_30_month_price_512gb': '', 'memory_30months_512gb': '', 'avaiablity_30months_512gb': False, 'installment_24_month_price_512gb': '', 'memory_24months_512gb': '', 'avaiablity_24months_512gb': False, 'full_retail_price_512gb': '', 'full_retail_memory_512gb': '', 'full_retail_avaiablity_512gb': False}, {'color': 'Red', 'images': 'https://ss7.vzw.com/is/image/VerizonWireless/apple-iphone-12-red-10132020', 'installment_30_month_price_128gb': 24.99, 'memory_30months_128gb': '128 GB', 'avaiablity_30months_128gb': True, 'installment_24_month_price_128gb': 31.24, 'memory_24months_128gb': '128 GB', 'avaiablity_24months_128gb': True, 'full_retail_price_128gb': 749.99, 'full_retail_memory_128gb': '128 GB', 'full_retail_avaiablity_128gb': True, 'installment_30_month_price_256gb': 28.33, 'memory_30months_256gb': '256 GB', 'avaiablity_30months_256gb': True, 'installment_24_month_price_256gb': 35.41, 'memory_24months_256gb': '256 GB', 'avaiablity_24months_256gb': True, 'full_retail_price_256gb': 849.99, 'full_retail_memory_256gb': '256 GB', 'full_retail_avaiablity_256gb': True, 'installment_30_month_price_512gb': '', 'memory_30months_512gb': '', 'avaiablity_30months_512gb': False, 'installment_24_month_price_512gb': '', 'memory_24months_512gb': '', 'avaiablity_24months_512gb': False, 'full_retail_price_512gb': '', 'full_retail_memory_512gb': '', 'full_retail_avaiablity_512gb': False}, {'color': 'Black', 'images': 'https://ss7.vzw.com/is/image/VerizonWireless/apple-iphone-12-black-10132020', 'installment_30_month_price_128gb': 24.99, 'memory_30months_128gb': '128 GB', 'avaiablity_30months_128gb': True, 'installment_24_month_price_128gb': 31.24, 'memory_24months_128gb': '128 GB', 'avaiablity_24months_128gb': True, 'full_retail_price_128gb': 749.99, 'full_retail_memory_128gb': '128 GB', 'full_retail_avaiablity_128gb': True, 'installment_30_month_price_256gb': 28.33, 'memory_30months_256gb': '256 GB', 'avaiablity_30months_256gb': True, 'installment_24_month_price_256gb': 35.41, 'memory_24months_256gb': '256 GB', 'avaiablity_24months_256gb': True, 'full_retail_price_256gb': 849.99, 'full_retail_memory_256gb': '256 GB', 'full_retail_avaiablity_256gb': True, 'installment_30_month_price_512gb': '', 'memory_30months_512gb': '', 'avaiablity_30months_512gb': False, 'installment_24_month_price_512gb': '', 'memory_24months_512gb': '', 'avaiablity_24months_512gb': False, 'full_retail_price_512gb': '', 'full_retail_memory_512gb': '', 'full_retail_avaiablity_512gb': False}, {'color': 'Green', 'images': 'https://ss7.vzw.com/is/image/VerizonWireless/apple-iphone-12-green-10132020', 'installment_30_month_price_128gb': 24.99, 'memory_30months_128gb': '128 GB', 'avaiablity_30months_128gb': True, 'installment_24_month_price_128gb': 31.24, 'memory_24months_128gb': '128 GB', 'avaiablity_24months_128gb': True, 'full_retail_price_128gb': 749.99, 'full_retail_memory_128gb': '128 GB', 'full_retail_avaiablity_128gb': True, 'installment_30_month_price_256gb': 28.33, 'memory_30months_256gb': '256 GB', 'avaiablity_30months_256gb': True, 'installment_24_month_price_256gb': 35.41, 'memory_24months_256gb': '256 GB', 'avaiablity_24months_256gb': True, 'full_retail_price_256gb': 849.99, 'full_retail_memory_256gb': '256 GB', 'full_retail_avaiablity_256gb': True, 'installment_30_month_price_512gb': '', 'memory_30months_512gb': '', 'avaiablity_30months_512gb': False, 'installment_24_month_price_512gb': '', 'memory_24months_512gb': '', 'avaiablity_24months_512gb': False, 'full_retail_price_512gb': '', 'full_retail_memory_512gb': '', 'full_retail_avaiablity_512gb': False}, {'color': 'White', 'images': 'https://ss7.vzw.com/is/image/VerizonWireless/apple-iphone-12-white-10132020', 'installment_30_month_price_128gb': 24.99, 'memory_30months_128gb': '128 GB', 'avaiablity_30months_128gb': True, 'installment_24_month_price_128gb': 31.24, 'memory_24months_128gb': '128 GB', 'avaiablity_24months_128gb': True, 'full_retail_price_128gb': 749.99, 'full_retail_memory_128gb': '128 GB', 'full_retail_avaiablity_128gb': True, 'installment_30_month_price_256gb': 28.33, 'memory_30months_256gb': '256 GB', 'avaiablity_30months_256gb': True, 'installment_24_month_price_256gb': 35.41, 'memory_24months_256gb': '256 GB', 'avaiablity_24months_256gb': True, 'full_retail_price_256gb': 849.99, 'full_retail_memory_256gb': '256 GB', 'full_retail_avaiablity_256gb': True, 'installment_30_month_price_512gb': '', 'memory_30months_512gb': '', 'avaiablity_30months_512gb': False, 'installment_24_month_price_512gb': '', 'memory_24months_512gb': '', 'avaiablity_24months_512gb': False, 'full_retail_price_512gb': '', 'full_retail_memory_512gb': '', 'full_retail_avaiablity_512gb': False}], 'reviews': [{'review_text': '', 'review_date': '2021-11-04T00:43:22.000+00:00', 'review_name': 'Escorpión'}, {'review_text': 'I love this phone it has done me very well would 100% recommended this phone the most out of ALL phones.', 'review_date': '2021-10-30T13:54:12.000+00:00', 'review_name': 'Hazelbacil'}, {'review_text': 'I upgraded from the se 2020 because the battery was dying so fast and it was overheating so I decided to upgrade to the 12 and I’m glad I did! I’ve had it for a little over a month now and its been great! I recommend this phone.', 'review_date': '2021-10-15T17:14:55.000+00:00', 'review_name': 'kasen3321'}, {'review_text': 'This phone has everything that you need in a phone but just smaller lighter and cheaper!', 'review_date': '2021-10-15T01:52:01.000+00:00', 'review_name': 'Ry10035'}, {'review_text': 'If you don’t have the iPhone 12 then you need to get it now the battery life is amazing I haven’t charged it for 2 days and the battery is still alive I love using this phone it takes hours or days for the battery to die, if your constantly on your phone this is the one you need.', 'review_date': '2021-10-10T15:48:49.000+00:00', 'review_name': 'Bob27'}, {'review_text': 'I think this phone is amazing. This phone has the best camera that sometimes looks 3D. I think It works flawlessly. If you like apple phones then this is a great phone and you will not be sorry. Holds up to drops too.', 'review_date': '2021-10-10T14:47:04.000+00:00', 'review_name': 'ILovepink1977'}, {'review_text': '', 'review_date': '2021-08-31T00:42:55.000+00:00', 'review_name': 'MaxMag'}, {'review_text': 'I read the poor reviews and I have to say…I’ve never had ANY of the issues others says they’ve experienced.', 'review_date': '2021-08-27T22:08:33.000+00:00', 'review_name': 'Joey'}, {'review_text': 'Very solid. No complaints.', 'review_date': '2021-08-26T03:47:08.000+00:00', 'review_name': 'Tyty'}, {'review_text': 'Best iPhone design, fast internet and no dropped calls. Everyone should buy this phone', 'review_date': '2021-08-17T05:50:43.000+00:00', 'review_name': 'Dan70'}, {'review_text': 'This is a good iPhone and now you don’t have to push the button 24/7', 'review_date': '2021-08-09T18:33:47.000+00:00', 'review_name': 'Vic16'}, {'review_text': '', 'review_date': '2021-07-26T01:44:56.000+00:00', 'review_name': 'Winning1'}, {'review_text': 'The best iPhone I’ve had!! Upgraded from the XR. Perfect sound, vivid pictures and. Great size.', 'review_date': '2021-07-11T21:39:39.000+00:00', 'review_name': 'Reeda'}, {'review_text': 'Will not pair with Bluetooth. Only problem I have. Love the phone.', 'review_date': '2021-07-07T15:46:11.000+00:00', 'review_name': 'Jude16'}, {'review_text': "I thought of the I-phone as one of apple's better phones in a couple of years. The video that you could make let a lone the quality of the video that were able to watch where truly out of this world,", 'review_date': '2021-07-07T00:40:59.000+00:00', 'review_name': 'Maya loves apples'}, {'review_text': 'I recommend this phone to anyone And this is a very great product', 'review_date': '2021-07-02T10:26:16.000+00:00', 'review_name': 'AnnH'}, {'review_text': 'I’ve had my phone for a week now. Coming from the SEE this phone is outstanding. I highly recommend it.', 'review_date': '2021-06-24T04:15:32.000+00:00', 'review_name': 'Sdc75'}, {'review_text': '', 'review_date': '2021-06-22T12:01:30.000+00:00', 'review_name': 'has23'}, {'review_text': 'Phone works great. Can’t really say much about the 5G because there is not really a tower in my area yet. But the look and feel of the phone is great. I love the square design and the old school feel. The battery life is great as I use my phone for just about everything. The battery definitely keeps up.', 'review_date': '2021-06-21T12:30:05.000+00:00', 'review_name': 'Triptonc'}, {'review_text': '', 'review_date': '2021-06-15T20:14:12.000+00:00', 'review_name': 'i do not no'}, {'review_text': 'I upgraded from my IPhone 7 to IPhone 11. I got a Great deal on the IPhone 11. I took some pictures. It was beautiful photos, and the features are great too. I love the design of the iPhone 11.', 'review_date': '2021-06-14T21:20:08.000+00:00', 'review_name': 'Binky'}, {'review_text': '', 'review_date': '2021-06-14T13:38:42.000+00:00', 'review_name': '1744'}, {'review_text': 'he s been doing well so far.', 'review_date': '2021-06-12T06:03:05.000+00:00', 'review_name': 'elfuelte01'}, {'review_text': '', 'review_date': '2021-06-11T18:46:56.000+00:00', 'review_name': 'asDd'}, {'review_text': 'I’ve had this phone for about 3 months now and I love it! I upgraded from the Samsung note 10 plus. I wanted an Apple Watch and I don’t regret it at all. The camera is great and I am surprised at how great the pictures look. I would definitely recommend this phone!', 'review_date': '2021-06-05T11:16:22.000+00:00', 'review_name': 'Sammitoes'}, {'review_text': 'love this it has so many good things and can be helpful in a lot of ways!', 'review_date': '2021-06-03T23:05:04.000+00:00', 'review_name': 'joan157'}, {'review_text': 'I absolutely love my iPhone 12 Pro Max. It was the best decision I’ve made when it comes to phones.', 'review_date': '2021-06-02T22:38:40.000+00:00', 'review_name': 'Mommyoffour16181921'}, {'review_text': 'It is a very good product', 'review_date': '2021-06-02T13:03:00.000+00:00', 'review_name': 'Hehehe'}, {'review_text': 'I have had multiple iPhones and this one has been my favorite. No issues whatsoever and I like the squared edges. Super responsive and seamless to use.', 'review_date': '2021-05-31T16:28:54.000+00:00', 'review_name': 'MarineCruse'}, {'review_text': 'how  the cell phone  are alot  better  then other cell phone  company  im  going to  get  the purple  color of the new  cell phone  color  for  my  new  cell phone some time this i got  the cell phone  iphone of white  and it has been  a good  cell phone but  it kind  of cracked', 'review_date': '2021-05-21T22:52:49.000+00:00', 'review_name': 'diva'}, {'review_text': 'As soon as I heard Apple had designed a PURPLE iPhone, I had to pre-order it. I upgraded from my 11 Pro Max and the fact that it’s smaller and fits perfectly in my tiny hands was an added bonus! I’m very happy with this phone and highly recommend it to anyone that loves PURPLE and a small phone that easily fits in your back pocket.', 'review_date': '2021-05-04T03:31:47.000+00:00', 'review_name': 'MommyEve83'}, {'review_text': 'I had an iPhone 6s Plus, an iPhone 7, and an iPhone 12. So far, the iPhone 12 is the BEST one yet.', 'review_date': '2021-05-01T01:51:57.000+00:00', 'review_name': 'Tiger3'}, {'review_text': "I'm impressed. Fits nice in the hand. My last phone was android I used with an android smart watch. I know I'm not supposed to mention other products, but the apple watch (s3) is the best part of changing---it is SO much lighter to wear (ironically, the same reason I replaced my ipad pro with an android) and works so much smoother.  I had developed I pinched nerve in my watch and tablet holding arm, and needed to lighten the weight. The watch felt like I wasn't wearing a watch at first. Both phone and watch feel like a huge step up in quality, as one would expect.  It's nice that there is a voice-mail button on the phone screen. Having siri schedule appointments can be hilarious.  I've had Apple products off and on for around 15 years, and tile set up is not a lot different from my ipod that is over 10 years old (and still going strong, but no memory to update)....so, very familiar.", 'review_date': '2021-05-01T01:21:19.000+00:00', 'review_name': 'Kamyo'}, {'review_text': 'More than you’d like to admit than YOU NEED THIS PHONE! I’m clumsy & can forget where I set my phone, I drop it too often. I upgraded from the 7+ I will say -due to universal software updates, this isn’t too different besides the obvious features. One stand out difference though is the screen! This phones had a handful of falls that immediately made my heart sink because of the way it landed or how hard. I just knew when I picked it up it’d be horribly shattered....not even a small crack! I can guarantee my old phone would’ve never turned back on in comparison. So for this reason alone this phone is so worth it to me. I never have any problems with signal or dropped calls other people on here have mentioned; I don’t have any complaints', 'review_date': '2021-04-30T03:42:05.000+00:00', 'review_name': 'Emilys'}, {'review_text': '', 'review_date': '2021-03-27T21:39:18.000+00:00', 'review_name': 'MOAN123'}, {'review_text': 'Went from IPhone 7 Plus which hardware died after 4 years. Bought IPhone 12 some new features but basically it’s a IPhone . No problems with it. Just turn off 5G network in settings. Phone just seems to function better with it off. First time IPhone buyers might be sad with no charging gear. I always had IPhones have plenty of IPhone charging cubes and any IPhone owners will have extra lightening cables. They work with all new  IPhones. Smart thinking for savings for the Apple Co. Want the newest thing fast charger and cable then buy it! Just remember Apple USB-C cable does not fit any of the old style USB ports that are everywhere like cars, home products, etc will need to buy adapter to use those. People need to remember electronics change all the time to be more efficient.', 'review_date': '2021-03-26T19:59:47.000+00:00', 'review_name': 'Rich'}, {'review_text': 'Love the design and color', 'review_date': '2021-03-21T16:49:35.000+00:00', 'review_name': 'Gbg6'}, {'review_text': 'The phone is real piece of deal.', 'review_date': '2021-03-10T14:52:08.000+00:00', 'review_name': 'Saurav'}, {'review_text': 'I had a iPhone 7 and this is a great upgrade also 5G is amazing if next to the towers also a lot of people have no clue how 5G works so the 1 to 2 star complaints are crap. This phone is so much faster and a decent price', 'review_date': '2021-03-10T00:40:13.000+00:00', 'review_name': 'G person'}, {'review_text': 'I definitely recommend this phone for people who tend to drop there phone a lot because of the extremely thick glass and it is has extremely good quality and is definitely built to last.', 'review_date': '2021-03-09T00:59:54.000+00:00', 'review_name': 'Trent1423'}, {'review_text': 'Over all I love the iPhone 12! It is fast, it has AMAZING camera quality, and the design is so clean and slick.', 'review_date': '2021-03-03T03:13:48.000+00:00', 'review_name': 'Stampsman08'}, {'review_text': 'Great Speed no frame lag for playing games easy for one handed operation', 'review_date': '2021-02-27T12:22:50.000+00:00', 'review_name': 'Ghost'}, {'review_text': 'I have had my phone for 2 months now, and have not had one dropped call.  My wife has the 12, and has had the exact same reliability. No issues whatsoever. I wish people could just be happy with their own phone brand instead of constantly trashing Apple. It’s pathetic.', 'review_date': '2021-02-14T21:53:29.000+00:00', 'review_name': 'GLee'}, {'review_text': "I made the switch from Android a couple months ago and got the Iphone 12 and so far so good! I was worried about it being confusing but I quickly adjusted. I ordered the color black but it looks more blue than it does black. The battery life is amazing! Way better than any phone I've ever had. I like the size of it as it fits better in pockets and in my hand. Overall I'm super happy with it. If you are considering making the switch from Android to iPhone I suggest you do it. You wont be disappointed.", 'review_date': '2021-02-01T16:42:26.000+00:00', 'review_name': 'Katie'}, {'review_text': 'Everyone taking about dropped calls?! My iphone 12 works good, no call drop or nothing related, maybe they need to check their signal, cause mines works perfect!!!', 'review_date': '2021-01-26T02:01:15.000+00:00', 'review_name': 'Frankiepr80'}, {'review_text': 'Great Service Nice Store And Great professionals.', 'review_date': '2021-01-14T03:30:41.000+00:00', 'review_name': 'Jean69'}, {'review_text': "I'm enjoying this new phone. Here's a photo and video I took with it.", 'review_date': '2021-01-04T19:48:22.000+00:00', 'review_name': 'Steve'}, {'review_text': 'THE MOST BEST PHOE BY EVER I LIVE IT SO MUCH', 'review_date': '2020-12-01T02:15:52.000+00:00', 'review_name': 'Kandi13'}, {'review_text': "I have had the iPhone 5s, 6, 6s, SE, 7, and XR. The 12 is solidly the best iPhone that Apple has made and is a huge improvement over the XR and 11. Apple has finally brought back the adored square design like the 5s instead of the chunky feeling round edges of the XR and 11. The screen is miles ahead of the XR/11 as well. iOS14 brings a lot of welcome additions that gets iOS up to par with Android (the widget system is reminiscent of Windows Phone actually). My only real criticism is battery life has taken a hit compared to the XR and Touch ID would've been a welcome inclusion given the pandemic but this phone was likely planned and finalized well before covid-19 changed everything. Fully recommended if you are on a XS/XR or older. This phone is so good, I would recommend passing on the 12 Pro and either save the money or jump to the 12 Po Max.", 'review_date': '2020-11-25T05:44:52.000+00:00', 'review_name': 'jkitch03'}, {'review_text': 'Switched from the IPhone SE 2020, this phone is fantastic. My previous iphone started to freeze the screen 3x a week. I’m happy I switched to this phone. This phone is also way faster then the Iphone SE 2020', 'review_date': '2020-11-19T01:13:03.000+00:00', 'review_name': 'Bigchase'}, {'review_text': "This was a huge upgrade for me coming  from my iPhone 6 to now the iPhone 12. They really have made this such an easy device to set up and use. Would recommend this phone to any of my friends and we are in our 70's!", 'review_date': '2020-11-08T19:29:15.000+00:00', 'review_name': 'chrisy1234'}, {'review_text': 'I upgraded to the blue iPhone 12 from the iPhone X. I love the color and the camera is a big improvement. Battery lasts me all day. I love the screen size, larger than my old iPhone X, but still not too big. Screen is beautiful. Fast speeds and didn’t care that it did not come with headphones or usb charger because I have a charger from my old phone and use AirPods. I prefer wireless anyway. Great buy.', 'review_date': '2020-11-05T18:26:23.000+00:00', 'review_name': 'Ladiebug82'}, {'review_text': 'The camera better then my old iphone 11 pro', 'review_date': '2020-11-05T10:10:17.000+00:00', 'review_name': 'Jsanis'}, {'review_text': 'Very impressed by the camera features, thank you Apple!', 'review_date': '2020-11-04T05:24:38.000+00:00', 'review_name': 'andyroo'}, {'review_text': 'Love the camera and every feature of the phone.', 'review_date': '2020-11-01T20:33:36.000+00:00', 'review_name': 'Lori'}, {'review_text': 'Updated from an iPhone X and I love this phone! Screen quality is excellent, it’s fast, and I love the camera. The new design is also much easier to hold. I have it in green and it’s gorgeous. Apple you did it again!', 'review_date': '2020-11-01T14:19:53.000+00:00', 'review_name': 'Shannon7'}, {'review_text': 'This phone is great. It’s so pretty and do everything I need it to! It’s just amazing', 'review_date': '2020-10-26T20:19:53.000+00:00', 'review_name': 'aendsley13'}, {'review_text': "I upgrade from the IPhone XS. All images are very clear. It's a nice size not that much larger than the XS. The speed of the phone is great. My old charger still works with this phone so not having a charger and earphone was no big deal. I still have PLENTY of chargers and earphones from previous phone that i haven't even used yet.", 'review_date': '2020-10-26T12:26:52.000+00:00', 'review_name': 'moonpie'}, {'review_text': 'The camera is absolutely amazing. Some people are upset for not adding headphones. I like it. Its good and will reduce millions of pounds of waste.', 'review_date': '2020-10-23T22:39:47.000+00:00', 'review_name': 'Carys'}, {'review_text': 'Simply amazing , switch to ios from S10 plus never go back. Apple is were is at ,and 12  is amazing', 'review_date': '2020-10-23T20:31:48.000+00:00', 'review_name': 'Leo B'}, {'review_text': 'Very easy to use, and the camera is amazing!!! Thank you Apple!!!', 'review_date': '2020-10-21T17:45:51.000+00:00', 'review_name': 'Keaton'}, {'review_text': 'Fast powerful new camera rocks', 'review_date': '2020-10-16T07:51:33.000+00:00', 'review_name': 'JBone'}, {'review_text': '', 'review_date': '2021-10-29T03:13:46.000+00:00', 'review_name': 'Bob123456789'}, {'review_text': 'I updated to iPhone 12 from Samsung Galaxy S10. I had the Samsung for 2 years and I prefer the apple platform over the Samsung. I got the iPhone 12 because it was smaller, lighter and purple! Although I have experienced a few of the bugs that I experienced when I had iPhone before, I really like the iPhone 12. The camera takes excellent pictures, the battery lasts 2 days and I am on my phone a lot. I’ve experienced issues with scrolling freezes on certain sites and app and the battery gets hot when I charge it thus the 4 star review. Happy to be back with the apple platform overall. Can’t wait to update from iOS 14 to 15.1 in a week!', 'review_date': '2021-10-21T02:42:58.000+00:00', 'review_name': 'AppleAnn'}, {'review_text': 'It is a high quality product and I have owed it for a few weeks now and have not had one problem. My only complaint is that if you are not going to put a case on the phone then it feels very boxy. I would recommend putting a case on it.', 'review_date': '2021-09-13T14:42:07.000+00:00', 'review_name': 'Nonofyourbuisness'}, {'review_text': '', 'review_date': '2021-08-16T10:30:27.000+00:00', 'review_name': 'nandoz'}, {'review_text': '', 'review_date': '2021-08-03T18:56:59.000+00:00', 'review_name': 'unit'}, {'review_text': '', 'review_date': '2021-05-27T09:39:51.000+00:00', 'review_name': 'Bob Me'}, {'review_text': '', 'review_date': '2021-04-23T17:41:07.000+00:00', 'review_name': 'Deb22'}, {'review_text': 'I love my phone. I am impressed with the speed and features, just not the size. That’s about my only complaint. For a 12, it’s about the same size as a iPhone 6.', 'review_date': '2021-04-16T19:15:32.000+00:00', 'review_name': None}, {'review_text': 'This is the first apple ive owned i wont go back to go back to android. This cell is faster than any wifi ive been around', 'review_date': '2021-04-09T15:52:09.000+00:00', 'review_name': 'Hazmat13'}, {'review_text': 'I have had this phone for over 10 days, Very satisfied. Have not dropped a call. Great internet speed Wi-Fi or 5G.', 'review_date': '2021-03-24T16:02:22.000+00:00', 'review_name': 'IanH'}, {'review_text': 'Recently been having internet issues even when I have full bars, but hey other than that it’s been amazing, ngl dropped it in the hot tub for about 10 minutes, pulled it out, worker perfectly still', 'review_date': '2021-01-20T17:23:59.000+00:00', 'review_name': 'Ggwhite'}, {'review_text': "The phone is definitely bigger which I thought would be a problem but easily got used to it.It is 100% faster than the 6 which is makes using the phone a pleasure.. No lags at all.The service has been great with no dropped calls or issues as some people mentioned.Miss the fingerprint login which was cool but this has face ID. I also liked the rounded edges of the 6 as the edges of the 12 are flat which feels bulkier. The rounded edges were much better and comfortable. The camera is fantastic as always. Was hoping for better battery life but not too bad. Overall it's a great phone with a lot of changes and glad I made the switch.", 'review_date': '2021-01-08T15:55:35.000+00:00', 'review_name': 'Techtron'}, {'review_text': '', 'review_date': '2021-01-03T21:59:04.000+00:00', 'review_name': 'hixonium'}, {'review_text': '', 'review_date': '2020-11-25T13:57:22.000+00:00', 'review_name': 'ak47'}, {'review_text': 'm glad n happy to find this', 'review_date': '2020-10-31T20:14:28.000+00:00', 'review_name': 'simen toes'}, {'review_text': "Replaced iPhone 6s with 12 Pro.  Nice phone and significant improvement, but acted sooner because I was having problems with battery on 6s. Honestly, didn't need Pro, already realize that I won't use much of its capabilities, should have gone with 12 with 64G or waited for a much better deal..", 'review_date': '2020-10-30T18:30:00.000+00:00', 'review_name': 'Jimandnette'}, {'review_text': 'Bad reception on Wi-Fi and data. Get very hot at times. Screen just floats around on all pages. Screen freezes a lot.', 'review_date': '2021-11-14T16:28:49.000+00:00', 'review_name': 'rmspecialized'}, {'review_text': 'Coming from a Note 9,This phone seems lack luster.Lacking competitive features, that I personally miss. Battery life is good though other than that the phone seems average. The Iphone12 doesn’t have as good a service reception as others from Verizon. Wouldn’t recommend.', 'review_date': '2021-11-13T17:30:46.000+00:00', 'review_name': 'OsGPurple'}, {'review_text': 'I had a 12 pro max that I dropped and went static so needed to be replaced. The 12 was the only phone in stock, so I was forced into it. It, much like my x and 12 pro max has a volume issue where the volume randomly turns down to nothing, is super slow to load (like many others said) & is probably one of the worst phones I’ve had. I gave it 3 stars because on a positive note, I am never on my phone anymore because it is sooo bad and freeing myself from a possible phone addiction.', 'review_date': '2021-11-08T21:38:32.000+00:00', 'review_name': 'JHanson1980'}, {'review_text': 'Slow to no service in many areas. Bought these for the whole family and we all have the same issue.', 'review_date': '2021-11-06T13:19:02.000+00:00', 'review_name': 'Apple'}, {'review_text': 'If it doesn’t have 5G then no other networks work…LTE?  What’s that?  No service.  Only thing I like is more storage and good quality pictures.', 'review_date': '2021-11-04T01:01:31.000+00:00', 'review_name': 'Stressed T'}, {'review_text': "Battery life is only average, the OS still has bugs which I have already previously encountered on my iPhone business devices. Functionality is okay, the device OS is not very customizable and the lock screen, if not using face unlock, is buggy. The price is too high for this device for what you get. This is coming from a Samsung user who was looking for a phone with less capability that I wouldn't get glued to. Found it!", 'review_date': '2021-10-06T14:22:54.000+00:00', 'review_name': 'vzreviewer'}, {'review_text': '', 'review_date': '2021-09-09T09:29:20.000+00:00', 'review_name': 'Tes5'}, {'review_text': '', 'review_date': '2021-08-25T15:20:15.000+00:00', 'review_name': 'fran99'}, {'review_text': 'I wish I would have kept the XR instead of getting this phone I like that better just have not felt this phone.', 'review_date': '2021-08-19T03:09:37.000+00:00', 'review_name': 'Nica'}, {'review_text': 'After having android phones, I switched to the iPhone because I thought that it would integrate well with my Mac, iPad, etc. there are so many features that come standard in Google’s Pixel phone that just aren’t on this phone. No way to tease out which apps can send notifications to my Garmin watch. The keyboard is awkward with having punctuation on the alternate keyboard and not on the main. You have to turn off Bluetooth in the car to use the microphone. The messaging app doesn’t let you archive…only delete. Honestly looking into returning the phone. But it is a pretty green color and I have a glittery otter box case so I got that going for me', 'review_date': '2021-08-02T05:04:36.000+00:00', 'review_name': 'Talitha'}, {'review_text': "I've gone from an Android to an Iphone 12.Total change and I mean total change.I can say its a nice phone .but I well say this as soon as I got it my son had me go buy a screen protector. I didn't like the fact that you can't get certain apps on your phone because it's an iphone on your phone like I had with my Andriod...it's not the same at all! And I'm NOT going to buy it either! The features are really different and do take a while to get use to. If you going to try this phone make sure you order a OTEERbox to go with it.I was told to get an Otterbox when you buy the phone...now I know why.But then I'm still getting use to it. Will take more time. If you like Iphones then yes I'd say buy it by all means...however if your changing then think again.", 'review_date': '2021-07-17T18:22:01.000+00:00', 'review_name': 'Cindy'}, {'review_text': 'Other than the larger screen in the smaller case, there’s not much to the iPhone 12 to justify a switch, if your older iPhone is in good shape. I upgraded from an iPhone 6 that was having connectivity issues in rural areas when traveling. 5G has had its own issues (many more dropped calls) in urban areas and is not faster than LTE, so not a reason to buy it. And while i like the bigger screen, I miss Touch ID, which is easier and faster than Face ID.', 'review_date': '2021-06-09T02:07:53.000+00:00', 'review_name': 'GalenG'}, {'review_text': 'It’s just a regular iPhone with a new camera no upgrades and not worth the upgrade just a regular iPhone', 'review_date': '2021-03-23T21:45:50.000+00:00', 'review_name': 'Shaun'}, {'review_text': 'I recently upgraded my twin sons from older iPhones to the iPhone 12. They really love them and have had no problems with them. But I have a problem. For the price a charging block should come with it. Not just a cord. Especially as the plug has changed from usb to usb-c. iPhone’s prices are ridiculous especially since they claim you’re paying for the technology. There isn’t much improvement from one version to the next. I’m considering upgrading because the functions on my iPhone 7 Plus have deteriorated more with each new update. And my charge port is messed up. I’ve never had a problem with my charge port on previous iPhones before. But am still trying to decide if I want the hassle of continued dealings with Apple.', 'review_date': '2021-03-20T00:10:58.000+00:00', 'review_name': 'cindyleewood1'}, {'review_text': 'Nice camera. However, phone is uncomfortable to hold and use. Very heavy.Phone Itself does not feel like much of an upgrade in most respects', 'review_date': '2021-03-15T06:55:13.000+00:00', 'review_name': 'Reelviewer'}, {'review_text': 'I have had a handful of iPhones throughout the years. The iPhone 12 is functionally disappointing. It randomly drops service and glitches daily. I did not have this issue in the past with other iPhones. I wish I could go back to my iPhone 8 Plus. I would give up the amazing camera of the iPhone 12 for my iPhone 8plus.', 'review_date': '2021-03-02T18:39:44.000+00:00', 'review_name': 'Emily'}, {'review_text': 'I upgraded from my iphone 6s. I feel like not much has changed, maybe just the camera, but not overall impressed. Dropped calls/FT, it seems slow and not very responsive, my 6s and battery life seems the same as well, which is not good if you are going to compare the 6s to the 12. I wanted to upgrade, but I feel like I got a SLIGHT upgrade... disappointing!', 'review_date': '2021-02-18T15:25:31.000+00:00', 'review_name': 'Vala'}, {'review_text': 'I’ve had the iPhone 12 for 2 months and don’t see what all the hype is about. I’ve had more problems out of it than any other iphone including the 6 and 8. I really like it’s size and color. The home button is dearly missed.', 'review_date': '2021-02-18T13:50:13.000+00:00', 'review_name': 'iPhone User for 5 Years'}, {'review_text': 'I have never had service or dropped call issues until I got the iPhone 12. Every call drops.', 'review_date': '2021-01-01T19:28:57.000+00:00', 'review_name': 'Dixie'}, {'review_text': 'Phone is ok. Good Camera. When searching no identifying symbol or anything to denote that phone is searching.As usual decreased functionality. The swiping is no better than the home button.', 'review_date': '2020-12-25T17:42:44.000+00:00', 'review_name': 'ITDOC'}, {'review_text': "I just got the blue iPhone 12 last week, and I had the iPhone 11. There is not much of a difference in the two models and I personally think that I could have waited, because my 11 was paid off in cash at the Apple store. I like the vivid blue color, smaller size and camera, but the camera in the 11 was just as good. The 5G does not seem very fast in my area and I don't know what the hype was all about. I am also very upset that Apple did not include a charger in the box, because as much as you pay for the phones, it should include the accessories. I don't really understand why Apple doesn't focus on enhancements such as graphics, battery life and operating system; every phone just about has a camera and can do the same thing, therefore, they should focus on what makes the phone function. I am basically like meh with the changes and don't think that it is worth upgrading if you have any of the 11 models; save your money and wait for major improvements.", 'review_date': '2020-10-29T18:27:44.000+00:00', 'review_name': 'Emt72'}, {'review_text': 'Slow loading data. 5G barely works and other services are slower. In most buildings phone does not work. First IPhone I have bought and will be the last.', 'review_date': '2021-11-06T02:55:26.000+00:00', 'review_name': 'Deltagirl'}], 'reviews_count': 169, 'rating': 3.165680473372781, 'carrier': ''}