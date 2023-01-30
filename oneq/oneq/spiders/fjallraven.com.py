# homepage: https://www.fjallraven.com/us/en-us
# template: sample_sitemap.py
# sitemaps index: https://www.fjallraven.com/us/en-us/Sitemap.xml
# sitemaps product: product url example: https://www.fjallraven.com/us/en-us/men/jackets/trekking-jackets/keb-eco-shell-jacket-m?_t_q=&_t_hit.id=Luminos_Storefront_Web_Features_Catalog_Product_Domain_CommonProduct/CatalogContent_32c84c67-5758-4118-a828-4bd959db2e7d_en-US&_t_hit.pos=1&_t_tags=andquerymatch%2clanguage%3aen%2csiteid%3a162d49d9-f0ac-4d2d-a110-e8143f6ca828&v=F82411%3a%3a7323450413118
#
# Please copy sample template below and leave above comments as it is

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
import requests
import random


# Class name will start _ and then lower case domain without extension and word Spider as follow
# '_'+DOMAIN_WITHOUT_EXT+'Spider'
class _JallravencomSpider(Spider):
    # spider name will start _ and then  lower case domain without extension as follow
    # '_'+DOMAIN_WITHOUT_EXT
    name = "_jallravencom"
    allowed_domains = ["fjallraven.com"]
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
    start_urls = ["https://www.fjallraven.com/us/en-us/men"]

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
                proxy = random.choice(self.proxy_list)
                proxies = {
                    "http": proxy,
                    "https": proxy,
                }

                try:
                    r = requests.get(url, headers=headers, proxies=proxies)
                    # Apply following pattern to extract all links from sitemap
                    pattern = "<loc>(.*?)</loc>"
                    m = re.findall(pattern, r.text, re.DOTALL)
                    i = 0
                    if len(m) > 0:
                        for l in m:
                            # Apply custom rule for each link found inside xml. If link is another xml file and contains products as follows
                            # send request to that xml too until we reach product html links.
                            if not l in self.foundlinks and l.find("products") != -1:
                                r = requests.get(l, headers=headers, proxies=proxies)
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
                        '//div[@class="product--images"]/a/@href'
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
                        '//a[@aria-label="Next page"]/@href'
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
                            '//h1[@class="heading--root product-card--title"]//text()'
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
                        e.strip()
                        for e in response.xpath(
                            '//span[@class="product-card--price"]/text()'
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
                                    '//span[@class="product-card--color-text"]/text()'
                                ).extract()
                            ],
                        )
                    )
                )
            )
        item["sizes"] = item["size"] = list(
            set(
                list(
                    filter(
                        bool,
                        [
                            e.strip()
                            for e in response.xpath(
                                '//button[contains(@class, "product-card--selector-item")]/text()'
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
                                '//div[@class="reviews--content"]/text()'
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
                        e.strip().replace("star rating", "")
                        for e in response.xpath(
                            '//span[@class="rating"]/span/text()'
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
                                '//meta[@property="og:image"]/@content'
                            ).extract()
                        ],
                    )
                )
            )
        )

        # Specific to this spider we need to follow options AJAX call to collect colour and size attributes.
        product_id = next(
            iter(
                filter(
                    bool,
                    [
                        e.strip()
                        for e in re.findall(
                            '"productId":(.*?),', response.text, re.DOTALL
                        )
                    ],
                )
            ),
            "",
        )
        options_url = "https://productoption.hulkapps.com/store/get_all_relationships?pid={product_id}&store_id=sharon-stambouli.myshopify.com".format(
            product_id=product_id
        )
        self.log("Following options request %s" % options_url)
        print(item)
        # We are yielding options to parse_options method with a meta object which contains prepared item in parse_product
        # This is not going to an issue for all websites most of them will yield item at this level.
        # We want to give priority to this parse_options requests to free memory asap.
        yield response.follow(
            options_url, callback=self.parse_options, meta={"item": item}, priority=1000
        )

    def parse_options(self, response):
        # First we need item from meta to add missing colors and necklace_length fields.
        item = response.meta.get("item")
        item["colors"] = list(
            set(
                list(
                    filter(
                        bool,
                        [
                            e.strip()
                            for e in response.xpath(
                                '//span[@class="product-card--color-text"]/text()'
                            ).extract()
                        ],
                    )
                )
            )
        )
        item["size"] = list(
            set(
                list(
                    filter(
                        bool,
                        [
                            e.strip()
                            for e in response.xpath(
                                '//button[contains(@class, "product-card--selector-item")]/text()'
                            ).extract()
                        ],
                    )
                )
            )
        )

        # Finally yielding item
        yield item


"""
{'category': 'T-SHIRTS & TANK TOPS',
'colors': ['113 - Chalk White',
'560 - Navy'],

'images': ['https://marvel-b1-cdn.bc0a.com/f00000000238876/www.fjallraven.com/49233e/globalassets/catalogs/fjallraven/f8/f870/f87046/f113/space_t-shirt_print_m_87046-113_a_main_fjr.jpg?width=680&height=680&mode=BoxPad&bgcolor=fff&quality=80',
'https://marvel-b1-cdn.bc0a.com/f00000000238876/www.fjallraven.com/49234e/globalassets/catalogs/fjallraven/f8/f870/f87046/f113/space_t-shirt_print_m_87046-113_b_main_fjr.jpg?width=680&height=680&mode=BoxPad&bgcolor=fff&quality=80',
'https://marvel-b1-cdn.bc0a.com/f00000000238876/www.fjallraven.com/49234e/globalassets/catalogs/fjallraven/f8/f870/f87046/f113/space_t-shirt_print_m_87046-113_b_main_fjr.jpg?width=680&height=680&mode=BoxPad&bgcolor=fff&quality=80',
'https://marvel-b1-cdn.bc0a.com/f00000000238876/www.fjallraven.com/49ac81/globalassets/catalogs/fjallraven/f8/f870/f87046/features/space_t-shirt_print_m_87046-113_d_model_fjr.jpg?width=680&height=680&mode=BoxPad&bgcolor=fff&quality=80',
'https://marvel-b1-cdn.bc0a.com/f00000000238876/www.fjallraven.com/49abf2/globalassets/catalogs/fjallraven/f8/f870/f87046/features/space_t-shirt_print_m_87046-113_e_model_fjr.jpg?width=680&height=680&mode=BoxPad&bgcolor=fff&quality=80,
'https://marvel-b1-cdn.bc0a.com/f00000000238876/www.fjallraven.com/49ac26/globalassets/catalogs/fjallraven/f8/f870/f87046/features/space_t-shirt_print_m_87046-113_f_detail_fjr.jpg?width=680&height=680&mode=BoxPad&bgcolor=fff&quality=80'],

'name': 'TREKKING JACKETS',
'price': '$500.00',
'rating': '4',
'reviews': ["I cannot understand some reviews saying this jacket "wets out." I have used this is heavy rain and snow and never had any issues. Amazing stretch, eco-shell is more breathable than Gore-Tex IMHO. Also, FJ has a lifetime warranty; if something breaks, they will fix or replace it! I also have the Arcteryx Beta AR, Mountain Hardwear Exposure 2 and Outdoor Research Helium; I have had the Arcteryx wet out many times, never the MH or the Eco-Shell. We all know how these fabrics work; if the temperature inside the jacket is warmer than the outside temp it works (waterproof/breathable layers). If the opposite is true, the jacket WILL wet out (common in warmer temps). Anyways, the Keb Eco-Shell is AMAZING; I love the inside and outside pocket for organization. The next purchase will be the Bertagen Eco-Shell; I really want to try that one (and the matching trousers). Fjällräven gear is amazing!",
'Owned the smock version of this jacket for a while now, im a wildlife photographer so i need a jacket that will keep me dry and warm whether im moving (with a little perspiration) or stationary (no moisture buildup). I saved this jacket "for best" where occasions where more extreme. The first time i tested this jacket was on a level walk in the rain, the outer fabric soon wetted out soaking the whole outer layer, it never beaded up and ran off keeping the jacket lighter. Inside at least 60% wetted out, making the jacket allot heavier, the water had made it through a few of the joining points especially at the tops of closed zips where the taped seams meet. I tested it again today, in conclusion i like the stretch fabric, the cut/shape colour, but its not waterproof and rain, light or heavy doesn't bead off. The trousers i bought at the same time are just as bad.',
'Great jacket but the wire in the hood brim broke in half. I am not even sure how it happened. I used this jacket only a few times. Unfortunately I am not going to buy this jacket again until they will replace the wire with something more durable.',
'I have owned many outdoors rain jackets and the eco-shell is hands down my absolute favorite. The four way stretch and excellent ventilation makes this a great shell for backpacking, biking and active outdoors use. The ventilation zippers (or pit zips') are LONG. This gives you lots of room to make micro adjustments to the breathability of the shell and the two way zippers can be opened from the bottom to allow the use the hand warmer pockets of a warmer layer underneath. I have used this jacket hiking, backpacking, fishing and guiding groups through the back country and have never had issues with the shell 'wetting out'. The up front price is steep but the warrantee makes this a priceless item for any outdoor enthusiast who expects the most from their gear.',
'Although I am still getting used to the zipper, this jacket is exactly what I have been looking for in a waterproof shell. The jacket is lightweight, breathable, and has a small amount of stretch for more movement. This lightweight stretch material means that the jacket doesn't have the typical crunchy sound of a normal Gore-Tex shell. Not to mention, the materials they use mean they aren't using fluorocarbons that can wash off into the environment! The pocket configuration can be tricky if you aren't used to chest pockets but when I am backpacking, I can use my waist strap and still access everything in my pocket.
Ashley V.'],
'reviews_count': '10',
'sizes': ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL'],
'timestamp': '2021-11-08T2:20:24 pm',
'url': 'https://www.fjallraven.com/us/en-us/men/jackets/trekking-jackets/keb-eco-shell-jacket-m?_t_q=&_t_hit.id=Luminos_Storefront_Web_Features_Catalog_Product_Domain_CommonProduct/CatalogContent_32c84c67-5758-4118-a828-4bd959db2e7d_en-US&_t_hit.pos=1&_t_tags=andquerymatch%2clanguage%3aen%2csiteid%3a162d49d9-f0ac-4d2d-a110-e8143f6ca828&v=F82411%3a%3a7323450413118'}

"""

