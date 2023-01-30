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
import pandas as pd

# Class name will start _ and then lower case domain without extension and word Spider as follow
# '_'+DOMAIN_WITHOUT_EXT+'Spider'


class _flipkartSpider(Spider):
    # spider name will start _ and then  lower case domain without extension as follow
    # '_'+DOMAIN_WITHOUT_EXT
    name = 'flipkart'
    allowed_domains = ['flipkart.com']
    custom_settings = {
        'RETRY_ENABLED': True,
        'COOKIES_DEBUG': True,
        'COOKIES_ENABLED': True,
        'REDIRECT_ENABLED': True,
        'DOWNLOAD_DELAY': 1,
        'CONCURRENT_REQUESTS': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'DOWNLOAD_TIMEOUT': 10,
        'LOG_LEVEL': 'DEBUG',
    }
    start_urls = [
        'https://www.flipkart.com/mobiles/mi~brand/pr?sid=tyy%2C4io&otracker=nmenu_sub_Electronics_0_Mi&p%5B%5D=facets.ram%255B%255D%3D6%2BGB%2B%2526%2BAbove'
    ]

    def __init__(self, *args, **kwargs):
        self.allowed_domains = kwargs.get('allowed_domains', []) if kwargs.get(
            'allowed_domains', []) else self.allowed_domains
        Spider.__init__(self, *args, **kwargs)

    def log(self, m):
        logging.error('custom_log:: %s' % m)
        print('custom_log:: %s' % m)

    def exception(self, msg=''):
        t, val, tb = sys.exc_info()
        self.log("custom_exception_log => %s : <%s> ! <%s> ! <%s>" %
                 (msg, t, val, tb))
        return sys.exc_info()

    foundlinks = []

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        # Extract product links from category or search pages ! This method will have all page source after click actions.
        # You must extract xpath of products on category or search pages.
        # You must keep following one line command and change ONLY xpath in it.
        product_links = list(filter(bool, [response.urljoin(
            e.strip()) for e in response.xpath('//a[@rel="noopener noreferrer"]//@href').extract()]))
        self.log("number of products :%s" % product_links)
        for product_link in product_links:
            # Always be sure uniqueness before yielding new product link
            if not product_link in self.foundlinks:
                # Do not forget appending new product link into foundlinks list.
                self.foundlinks.append(product_link)
                # This is product link so callback must be parse_product.
                # If needed request.meta object can be used to pass extra information to parse_product method.
                # If we want to play with priorities product links must have biggest priority number. We should jump to product pages asap.
                self.log('Found product link: %s' % product_link)
                yield scrapy.Request(product_link, callback=self.parse_product)

        next_pages = list(filter(bool, [response.urljoin(e.strip()) for e in response.xpath(
            '//span[contains(text(),"Next")]/parent::a//@href').extract()]))
        # get total number of products listed in category.
        for page in next_pages:
            if not page in self.foundlinks:
                self.foundlinks.append(page)
                self.log('Found product link: %s' % page)
                yield scrapy.Request(page, callback=self.parse)

    def parse_product(self, response):
        # First make sure this is a product page check title of product if there is no title return
        name = next(iter(filter(bool, [e.strip() for e in response.xpath(
            '//h1[@class="yhB1nd"]//span//text()').extract()])), "")
        if not name:
            self.log('There is no Product Name for this product: %s' %
                     response.url)
            return

        # Start preparing item
        item = ScraperItem()
        item["name"] = name
        item["url"] = response.url
        item["category"] = next(iter(filter(bool, [e.strip() for e in re.findall('"category":"(.*?)"', response.text, re.DOTALL)])), "")
        item["sale_price"] = next(iter(filter(bool, [e.replace('$', '').strip() for e in response.xpath('//div[@class="_30jeq3 _16Jk6d"]//text()').extract()])), "")
        item['product_title'] = next(iter(filter(bool, [e.strip() for e in response.xpath('//h1[@class="yhB1nd"]//span//text()').extract()])), "")
        item["price"] = next(iter(filter(bool, [e.replace('$', '').strip() for e in response.xpath('//div[@class="_3I9_wc _2p6lqe"]//text()[2]').extract()])), "")
        item["product_number"] = next(iter(filter(bool, [e.strip() for e in re.findall('"productId":"(.*?)"', response.text, re.DOTALL)])), "")
        detail_list = []
        color_dict = {}
        prize = {}
        prize["price"] = next(iter(filter(bool, [e.replace('$', '').strip() for e in response.xpath('//div[@class="_30jeq3 _16Jk6d"]//text()').extract()])), "")
        detail_list.append(prize)
        color_dict["colors"] = list(set(list(filter(bool, [e.strip() for e in response.xpath('//li[contains(@id,"color")]//div/div//text()').extract()]))))
        detail_list.append(color_dict)
        storage_dict = {}
        storage_dict["storage"] = list(set(list(filter(bool, [e.strip() for e in response.xpath('//li[contains(@id,"storage")]//div/div//text()').extract()]))))
        detail_list.append(storage_dict)
        item['color_and_storage'] = detail_list
        item["brand"] = next(iter(filter(bool, [e.strip() for e in re.findall('\"brand\":"(.*?)"', response.text, re.DOTALL)])), "")
        item['description'] = next(iter(filter(bool, [e.strip() for e in response.xpath('//div[contains(text(),"Description")]/parent::div//div[@class="_1mXcCf RmoJUa"]//text()').extract()])), "")
        item["sku_modal_number"] = next(iter(filter(bool, [e.strip() for e in response.xpath('//td[contains(text(),"Model Number")]//following-sibling::td//li//text()').extract()])), "")
        item["images"] = list(set(list(filter(bool, [e.replace('sw=250&sh=250', 'sw=2000&sh=2000').strip() for e in response.xpath('//div[@class="_3kidJX"]//img/@src').extract()]))))
        dfs = []
        table_extract = list(set(list(filter(bool, [e for e in response.xpath('//table[@class="_14cfVK"]').extract()]))))
        for i in table_extract:
            df = pd.read_html(i)[0]
            dfs.append(df)
        result = pd.concat(dfs)
        result.reset_index(drop=True, inplace=True)
        item['features'] = result.set_index([0]).T.to_dict('list')
        item["options"] = ''
        # Finally yielding item
        yield item


'''
{'name': 'Mi A2 (Red, 128 GB)', 'url': 'https://www.flipkart.com/mi-a2-red-128-gb/p/itmfghsgrkphksag?pid=MOBFD94CUVXZYMZH&lid=LSTMOBFD94CUVXZYMZHSKRQ01&marketplace=FLIPKART&store=tyy%2F4io&srno=b_1_1&otracker=nmenu_sub_Electronics_0_Mi&fm=organic&iid=2ab43bb4-2bfd-44a3-b096-7982a70e108d.MOBFD94CUVXZYMZH.SEARCH&ppt=None&ppn=None&ssid=vc20ws0ao00000001637752681216', 'category': 'Mobile', 'sale_price': '₹13,899', 'product_title': 'Mi A2 (Red, 128 GB)', 'price': '', 'product_number': 'MOBFD94CUVXZYMZH', 'color_and_storage': [{'price': '₹13,899'}, {'colors': ['Blue/Lake Blue', 'Gold', 'Red']}, {'storage': ['128 GB', '64 GB']}], 'brand': 'Mi', 'description': 'NA', 'sku_modal_number': 'MZB7130IN', 'images': ['https://rukminim1.flixcart.com/image/416/416/jrgo4280/mobile/m/z/h/mi-a2-a2-original-imafd92uetypzxma.jpeg?q=70'], 'features': {'In The Box': ['User Guide, Power Adapter, Type-C to Audio Adapter, Clear Soft Case, Warranty Card, USB Cable, SIM Eject Tool, Handset'], 'Model Number': ['MZB7130IN'], 'Model Name': ['Mi A2'], 'Color': ['Red'], 'Browse Type': ['Smartphones'], 'SIM Type': ['Dual Sim'], 'Hybrid Sim Slot': ['No'], 'Touchscreen': ['Yes'], 'OTG Compatible': ['Yes'], 'Sound Enhancements': ['Speaker: Single (Bottom Opening), 2 Microphones (for Noise Cancellation), Smart PA'], 'SAR Value': ['Head - 1.092W/kg, Body - 0.259W/kg'], 'Display Size': ['15.21 cm (5.99 inch)'], 'Resolution': ['2160 x 1080 Pixels'], 'Resolution Type': ['Full HD+'], 'GPU': ['Adreno 512'], 'Display Type': ['IPS'], 'Other Display Features': ['1500:1 Contrast Ratio, 83% NTSC Ratio, 2.5D Glass, Corning Gorilla Glass 5, 18:9 Display'], 'Operating System': ['Android Oreo 8.1'], 'Processor Type': ['Qualcomm Snapdragon 660 AIE'], 'Processor Core': ['Octa Core'], 'Primary Clock Speed': ['2.2 GHz'], 'Operating Frequency': ['GSM: B2, B3, B5, B8, WCDMA: B1, B2, B5, B8, 4G LTE-TDD: B40, B41, 4G LTE-FDD: B1, B3, B5'], 'Internal Storage': ['128 GB'], 'RAM': ['6 GB'], 'Primary Camera Available': ['Yes'], 'Primary Camera': ['20MP + 12MP'], 'Primary Camera Features': ['Panorama Mode, Dual Camera Lens: Sony IMX486, 1.25 micrometer pixels, Large f/1.75 Aperture, PDAF, Video: 4K Video Shooting (3840 x 2160 pixels at 30fps), 1080p Video Shooting (1920 x 1080 pixels at 30fps), 720p Video Shooting (1280 x 720 pixels at 30fps), 480p Video Shooting (720 x 480 pixels at 30fps), Slow Motion Video (720p at 120fps), Single Color Temperature Flash, 2.0 micrometer Pixels, Light Enhancement Technology, Sony IMX376, HDR Imaging Technology, Face Recognition, Burst Mode, Group Selfie, EIS for Video Recording, 4-in-1 Pixel Binning Technique, f/1.75 Large Aperture, AI Beautify 4.0, PDAF, Background Blurring in Portrait Mode, 5P Lens (20MP) + 5P Lens (12MP)'], 'Secondary Camera Available': ['Yes'], 'Secondary Camera': ['20MP Front Camera'], 'Secondary Camera Features': ['Group Selfie, 5P Lens, 4500K Soft-toned Selfie Light, Selfie Timer, F2.2 Aperture, Front Light, HDR, AI-powered Semantic Segmentation, Front Camera pixel Size: 1 micron, AI-powered Beautify 4.0, Face Recognition'], 'Flash': ['Rear Flash'], 'HD Recording': ['Yes'], 'Full HD Recording': ['Yes'], 'Video Recording': ['Yes'], 'Video Recording Resolution': ['3840 x 2160 pixels'], 'Dual Camera Lens': ['Primary Camera'], 'Network Type': ['3G, 4G VOLTE, 4G, 2G'], 'Supported Networks': ['GSM, WCDMA, 4G VoLTE, 4G LTE'], 'Internet Connectivity': ['4G, 3G, Wi-Fi'], '3G': ['Yes'], 'Bluetooth Support': ['Yes'], 'Bluetooth Version': ['5'], 'Wi-Fi': ['Yes'], 'Wi-Fi Version': ['802.11a/b/g/n/ac'], 'Map Support': ['Google Maps'], 'GPS Support': ['Yes'], 'Smartphone': ['Yes'], 'Touchscreen Type': ['Capacitive'], 'SIM Size': ['Nano SIM + Nano SIM'], 'Graphics PPI': ['403 PPI'], 'SIM Access': ['Dual Standby'], 'Sensors': ['Rear Fingerprint Sensor, Ambient Light Sensor, Proximity Sensor, E-compass, Accelerometer, Gyroscope'], 'Upgradable Operating System': ['Android Pie 9.0'], 'Other Features': ['Charger: 5 V/2 A, Support QC 4.0, Cores/Bits: 8 x Kyro/14nm Architecture, Android One, Body: Metal Unibody, IR Blaster, No Expandble Storag, USB Type-C (2.0)'], 'GPS Type': ['A-GPS, GLONASS, BeiDou'], 'Battery Capacity': ['3010 mAh'], 'Battery Type': ['Li-polymer'], 'Width': ['75.4 mm'], 'Height': ['158.7 mm'], 'Depth': ['7.3 mm'], 'Weight': ['168 g'], 'Warranty Summary': ['Brand Warranty of 1 Year Available for Mobile and 6 Months for Battery and Accessories']}, 'options': ''}
'''
