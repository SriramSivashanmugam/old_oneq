# homepage: https://www.att.com/
# template: conc_demand.py
# category page: https://www.att.com/buy/phones/
# product link: https://www.att.com/buy/phones/google-pixel-6-pro-128gb-cloudy-white.html
# Fields to be scraped: Carrier, Device Name, Color Variant, Memory Variant, price per variant, availability per variant from Device

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

# Class name will start _ and then lower case domain without extension and word Spider as follow
# '_'+DOMAIN_WITHOUT_EXT+'Spider'
class _attSpider(Spider):
    # spider name will start _ and then  lower case domain without extension as follow
    # '_'+DOMAIN_WITHOUT_EXT
    name = "attcom"
    allowed_domains = ["att.com"]
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
    start_urls = ["https://www.att.com/buy/phones/"]

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
        product_links = list(filter(bool,[response.urljoin(e.strip()) for e in re.findall('"PDPPageURL"\:\["(.*?)"', response.text, re.DOTALL)],))

        for product_link in product_links:
            # Always be sure uniqueness before yielding new product link
            if not product_link in self.foundlinks:
                # Do not forget appending new product link into foundlinks list.
                self.foundlinks.append(product_link)
                # This is product link so callback must be parse_product.
                # If needed request.meta object can be used to pass extra information to parse_product method.
                # If we want to play with priorities product links must have biggest priority number. We should jump to product pages asap.
                self.log("Found product link: %s" % product_link)
        for u in self.foundlinks:
            yield scrapy.Request(u, callback=self.parse_product)

    def parse_product(self, response):
        # First make sure this is a product page check title of product if there is no title return
        url = response.url
        name = next(iter(filter(bool,[e.strip() for e in response.xpath('//h1[contains(@class,"heading")]//text()').extract()],)),"",)
        if not name:
            self.log("There is no Product Name for this product: %s" % url)
            return

        # Start preparing item
        # item = ScraperItem()
        item = {}
        # carrier, device_name, colors => with a variant dict if applicable including price and availability as a key,
        # memory => with a variant dict if applicable including price and availability as a key
                
        item["name"] = name
        item["device_name"] = name
        item["url"] = url
        item['colors_variant'] = []
         
        item["carrier"] = "" #values not available for the field Carrier
        image_list = []
        if  re.search(r'\"color\"\:\"(.*?)\"\,\"mediaTypes\"\:\{\"images\"\:\{\"masterImageUrl\"\:\"(.*?)\"\}',response.text):
            image_list = re.findall(r'\"color\"\:\"(.*?)\"\,\"mediaTypes\"\:\{\"images\"\:\{\"masterImageUrl\"\:\"(.*?)\"\}',response.text)

        for color in response.xpath('//fieldset[@id="Color"]/div/label'):
            data = {}
            data['colors'] = next(iter(filter(bool,[e.strip() for e in color.xpath('input/@id').extract()],)),"",)
            data['price'] = next(iter(filter(bool,[e.replace("$", "").strip() for e in response.xpath('//*[@id="pageContainer"]/div[1]/div[2]/div[10]/div/div/span[1]/text()').extract()],)),"",)
            data['availability'] =False #values not available for the field availability
            
            for color_image in image_list:
                variant_color,variant_image = color_image
                variant_color = re.sub(r'\s+','',variant_color)
                
                if variant_color in data['colors']:
                    data['color_image'] = 'https://www.att.com'+str(variant_image)
                    break

            item['colors_variant'].append(data)
        item["retail_price"] = next(iter(filter(bool,[e.replace("$", "").strip() for e in response.xpath('//div[contains(text(),"Full retail price")]/parent::div/div/div/span[2]//text()').extract()],)),"",)
        item["installment_price"] = next(iter(filter(bool,[e.replace("$", "").strip() for e in response.xpath('//div[contains(text(),"Installment Plan")]/parent::div/div/div/span[2]//text()').extract()],)),"",)
        memory_details = []
        for each in response.xpath('//fieldset[@id="Capacity"]/div/div/label/div/div/div'):
            memory_variant={}
            memory_variant['memory'] = next(iter(filter(bool,[e.replace('GB','').strip() for e in each.xpath('div/text()').extract()],)),"",)
            memory_variant['price'] =  next(iter(filter(bool,[e.replace('$','').strip() for e in each.xpath('div/div/span[2]/text()').extract()],)),"",)
            memory_variant['availability'] = False #values not available for the field availability
            memory_details.append(memory_variant)
        item["memory_variant"] = memory_details 
        item["reviews"] = list(set(list(filter(bool,[e.strip() for e in response.xpath('//div[@class="content-review"]//text()').extract()],))))
        item["reviews_count"] = next(iter(filter(bool,[e.strip() for e in re.findall('"reviewCount"\:"(.*?)"', response.text, re.DOTALL)],)),"",)
        item["rating"] = next(iter(filter(bool,[e.strip() for e in re.findall('"ratingValue"\:"(.*?)"', response.text, re.DOTALL)],)),"",)
        item["images"] = list(set(list(filter(bool,[('https://www.att.com'+str(e.strip())) for e in response.xpath('//div[@id="accordion-content-gallery"]/div/div/img/@src').extract()],))))
        review_list = []
        for block in response.xpath('//ol[@class="bv-content-list bv-content-list-reviews"]/li'):
            review = {}
            review["review_name"] = next(iter(filter(bool,[e.strip() for e in block.xpath('.//*[@itemprop="author"]/span//text()').extract()],)),"",)
            review["review_date"] = next(iter(filter(bool,[e.replace(" \xa0", "").strip() for e in block.xpath('.//div[@class="bv-content-datetime"]/span[2]//text()').extract()],)),"",)
            review["review_text"] = next(iter(filter(bool,[e.strip() for e in block.xpath('.//div[@class="bv-content-summary-body-text"]/p//text()').extract()],)),"",)
            review_list.append(review)

        item["reviews"] = review_list
        # Finally yielding item
        yield item


# {'name': 'iPhone 13 Pro Max', 'device_name': 'iPhone 13 Pro Max', 'url': 'https://www.att.com/buy/phones/apple-iphone-13-pro-max-128gb-sierra-blue.html', 'colors_variant': [{'colors': 'SierraBlue', 'price': '30.56', 'availability': False, 'color_image': 'https://www.att.com/idpassets/global/devices/phones/apple/apple-iphone-13-pro-max/defaultimage/sierra-blue-hero-zoom.png'}, {'colors': 'Silver', 'price': '30.56', 'availability': False, 'color_image': 'https://www.att.com/idpassets/global/devices/phones/apple/apple-iphone-13-pro-max/defaultimage/silver-hero-zoom.png'}, {'colors': 'Gold', 'price': '30.56', 'availability': False, 'color_image': 'https://www.att.com/idpassets/global/devices/phones/apple/apple-iphone-13-pro-max/defaultimage/gold-hero-zoom.png'}, {'colors': 'Graphite', 'price': '30.56', 'availability': False, 'color_image': 'https://www.att.com/idpassets/global/devices/phones/apple/apple-iphone-13-pro-max/defaultimage/graphite-hero-zoom.png'}], 'carrier': '', 'retail_price': '1,099.99', 'installment_price': '30.56', 'memory_variant': [{'memory': '128', 'price': '30.56', 'availability': False}, {'memory': '256', 'price': '33.34', 'availability': False}, {'memory': '512', 'price': '38.89', 'availability': False}, {'memory': '1024', 'price': '44.45', 'availability': False}], 'reviews': [{'review_name': 'TB101brown', 'review_date': '2 months ago', 'review_text': 'Need to know that the camera sticks out from the back of phone and is weighted. I tend to always grab my phone upside down because of this. I would suggest this to be a design flaw and recommend this piece sitting flush with the back. The screen is super sensitive to touch, I find myself making mistakes when texting, it picks up any inadvertent touches. iOS 15 is awesome, but you don’t need this phone to enjoy it!! Mag - saf - my accessories have not arrived yet… accept my clear case, I can’t wait to attach the mag safe wallet and they have a pop socket one also. The phone still doesn’t turn up as loud as I would like it to. The 13 pro max is a great size for me, although a little heavy. It is a tad bigger than my iPhone 11 Pro Max. I want to give credit to the manufacturers that are making TRUE edge to edge screen protection AND blue light filter all in one. It is 5G and super fast, beautiful images watching movies. I have the Signature Elite Unlimited plan- highly recommend it. It has 40 gigs for a hotspot without slowing down. (can I get a shout out for the people who travel with kids!!!!) I do wish they would do the same for IPad users. I hope this review helped, I always like to read reviews. ( Texas Owner)'}, {'review_name': 'Anonymous', 'review_date': 'a month ago', 'review_text': 'Love the extra powerful battery for a longer day without charging.'}, {'review_name': 'Anonymous', 'review_date': 'a month ago', 'review_text': 'Phone takes Great pictures'}, {'review_name': 'Anonymous', 'review_date': '2 days ago', 'review_text': 'Lucky number 13 got my to finally upgrade from the iPhone 6S! The iPhone 13 Pro Max is the top of the line! I love the Graphite color, goes well the Apple Leather Case. The 512gb storage makes so I can record large video files with no worry. As a filmmaker the camera on this thing has been a game changer! Does well in low light and the better life is amazing! Lasts all day! I highly recommend it! AT&T shipped this out super fast too! Very pleased customer!'}], 'reviews_count': '6031', 'rating': '4.7', 'images': ['https://www.att.com/shopcms/media/att/2021/Shop/360s/2360514/6196D-2.jpg', 'https://www.att.com/shopcms/media/att/2021/Shop/360s/2360514/6196D-4.jpg', 'https://www.att.com/shopcms/media/att/2021/Shop/360s/2360514/6196D-1.jpg', 'https://www.att.com/shopcms/media/att/2021/Shop/360s/2360514/6196D-5.jpg', 'https://www.att.com/shopcms/media/att/2021/Shop/360s/2360514/6196D-3.jpg']}