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
class _ceneoplSpider(Spider):
    # spider name will start _ and then  lower case domain without extension as follow
    # '_'+DOMAIN_WITHOUT_EXT
    name = "_ceneopl"
    allowed_domains = ["ceneo.pl"]
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
    start_urls = ["https://www.ceneo.pl/Smartfony"]

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
                        "//a[contains(@class,'product-link')]/@href"
                    ).extract()
                    if "/Click/" not in e
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

        next_pages = list(
            filter(
                bool,
                [
                    response.urljoin(e.strip())
                    for e in response.xpath(
                        "//a[@class='pagination__item']/@href"
                    ).extract()
                ],
            )
        )
        total_number_of_products = list(
            filter(
                bool,
                [
                    response.urljoin(e.strip())
                    for e in response.xpath(
                        "//a[contains(@class,'product-link')]/@href"
                    ).extract()
                ],
            )
        )  # get total number of products listed in category.
        self.log(
            "total_number_of_products :%s" % total_number_of_products
        )  # printout for debugging later
        for page in next_pages:
            if not page in self.foundlinks:
                self.foundlinks.append(page)
                self.log("Found product link: %s" % page)
                yield scrapy.Request(page, callback=self.parse)

    def parse_product(self, response):
        # First make sure this is a product page check title of product if there is no title return
        name = next(
            iter(
                filter(
                    bool,
                    [
                        e.strip()
                        for e in response.xpath(
                            '//h1[contains(@class,"product-top__product-info")]//text()'
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
        item={}
        item["name"] = name
        item["url"] = response.url
        item["category"] = next(
            iter(
                filter(
                    bool,
                    [
                        e.strip()
                        for e in response.xpath(
                            "//meta[@property='product:category']/@content"
                        ).extract()
                    ],
                )
            ),
            "",
        )
        item["description"] = next(
            iter(
                filter(
                    bool,
                    [
                        e.strip()
                        for e in response.xpath(
                            '//div[@class="product-top__product-info__tags"]//text()'
                        ).extract()
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
                        e.replace(" ", "").strip()
                        for e in response.xpath(
                            '//div[contains(@class,"product-top__price-column")]//span[@class="value"]/text()'
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
                            for e in response.xpath(
                                '//a[contains(@class,"product-family__tiles__options__value")]//text()'
                            ).extract()
                        ],
                    )
                )
            )
        )
        item["reviews"] = list(
            list(
                filter(
                    bool,
                    [
                        {
                            "reviewer_name": e.xpath(
                                ".//span[@class='user-post__author-name']//text()"
                            )
                            .extract_first()
                            .strip(),
                            "review_text": e.xpath(
                                ".//div[@class='user-post__text']//text()"
                            )
                            .extract_first()
                            .strip(),
                            "review_date": e.xpath(
                                ".//span[@class='user-post__published']/time/text()"
                            )
                            .extract_first()
                            .strip(),
                        }
                        for e in response.xpath(
                            '//div[@class="user-post user-post__card js_product-review"]'
                        )
                    ],
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
                            '//a[contains(@class,"product-review__link")]/span/text()'
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
                            "//span[@class='product-review__score']/text()"
                        ).extract()
                    ],
                )
            ),
            "",
        )
        item["pros"] = list(
            set(
                list(
                    filter(
                        bool,
                        [
                            e.strip()
                            for e in response.xpath(
                                '//div[@class="review-feature__item"]//text()'
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
                            response.urljoin(e.strip())
                            for e in response.xpath(
                                '//div[@id="product-carousel"]//a[contains(@class,"js_gallery-anchor")]/img/@src'
                            ).extract()
                        ],
                    )
                )
            )
        )
        print(item)
        # Finally yielding item
        yield item

        """# Sample Output:

        {
            "name": "Samsung Galaxy A52s 5G SM-A528 6/128GB Czarny",
            "url": "https://www.ceneo.pl/113706425",
            "category": "Telefony i akcesoria > Telefony komórkowe > Smartfony",
            "description": "Smartfon Samsung z ekranem 6,5 cala, wyświetlacz Super AMOLED 2X. Aparat 64 Mpx, pamięć 6 GB RAM, bateria 4500mAh. Obsługuje sieć: 5G",
            "price": "1748",
            "colors": ["Biały", "Fioletowy", "Czarny", "Zielony"],
            "reviews": [
                {
                    "reviewer_name": "a...o",
                    "review_text": "Smartfon super. Pozytywne opinie z internetu całkowicie potwierdzam. Drugi dzień użytkuję A52s 5g. Telefon nie zawiesza się, jest szybki. Aparat jest naprawdę dobry. Stabilizacja robi swoje. Zdjęcia są o niebo lepsze niż w moim poprzednim telefonie A50. Gierki hulają także świetnie. Głośniki stereo dają radę. Także polecam telefonik w 100%.",
                    "review_date": "2 tygodnie temu,",
                },
                {
                    "reviewer_name": "b...4",
                    "review_text": "Telefon kupiony w Elektro.pl po bardzo dobrych pieniadzach. używam go od 3 dni i moge powiedziec ze naprawde berdo dobry telefon wszystko chodi płynnie, aparat robi bardzo dobre zdjęcia nawet w gorszych warunkach oswietleniowych. Jedynym minusem jest czytnik lini papilarnych ktory działa stosunkowo wolno...",
                    "review_date": "2 miesiące temu,",
                },
                {
                    "reviewer_name": "a...j",
                    "review_text": "Jak na razie śmiga aż miło. Poprzedni model to samsung A50, więc ogromnych różnic nie ma, nie trzeba było się uczyć wszystkiego na nowo. Zdecydowanie lepszy dźwięk, przy oglądaniu np filmu brzmi jak by było stereo, da się wyczuć głębię. Większych różnic póki co nie zauważyłam, ale pewnie nie przetestowałam wszystkiego. Porównując specyfikację, ten ma dużo lepszy aparat. Fakt zdecydowanie lepszy zoom, ale różnica nie jest aż tak zauważalna jak przy dźwiękach. Jedyne co mnie denerwuje to to, że nie mogę nigdzie znaleźć jak ustawić dzwonek telefonu w formie gradientu, narastająco, od razu wchodzi w głośne tony, co na mieście jest ok, ale w domu może przyprawić o zawał. Wydaje mi się, że ten model nie ma takiej możliwości.",
                    "review_date": "miesiąc temu,",
                },
                {
                    "reviewer_name": "p...w",
                    "review_text": "Długo szukałem, wybór padł na Samsung Galaxy A52s 5G, naprawdę telefon wart swojej ceny dla mnie rewelacja i polecam.",
                    "review_date": "2 miesiące temu,",
                },
                {
                    "reviewer_name": "d...1",
                    "review_text": "Jestem zadowolony z tego produktu. W pełni spełnia moje oczekiwania jak na razie (2 tygodnie użytkowania)",
                    "review_date": "3 tygodnie temu,",
                },
                {
                    "reviewer_name": "m...4",
                    "review_text": "_-Świetny telefon, z nowoczesnym oprogramowaniem i rozwiązaniami na obecne czasy, działa bez zarzutu-_",
                    "review_date": "2 miesiące temu,",
                },
                {
                    "reviewer_name": "m...3",
                    "review_text": "Super telefon w dobrej cenie kupiony w sieci AVANS za 1500 zł",
                    "review_date": "miesiąc temu,",
                },
                {
                    "reviewer_name": "a...5",
                    "review_text": "Jak na średnią półkę nawet dobry telefon , polecam",
                    "review_date": "miesiąc temu,",
                },
                {
                    "reviewer_name": "m...i",
                    "review_text": "póki co mam go kilka dni i jest spoko",
                    "review_date": "3 tygodnie temu,",
                },
                {
                    "reviewer_name": "p...6",
                    "review_text": "Przesiadka z a40 także tylkonlepeij",
                    "review_date": "2 dni temu,",
                },
            ],
            "reviews_count": "38",
            "rating": "4,9",
            "pros": [
                "łatwość obsługi",
                "czas pracy na baterii",
                "wygląd",
                "funkcjonalność",
            ],
            "images": [
                "https://image.ceneostatic.pl/data/productGalleryThumb/113706425/07905f3c-d4fc-49ae-bea5-a0d90e56638a_productGalleryThumb.jpg",
                "https://image.ceneostatic.pl/data/productGalleryThumb/113706425/86b454c0-1a89-4879-9827-b38f32ba7b66_productGalleryThumb.jpg",
                "https://image.ceneostatic.pl/data/productGalleryThumb/113706425/b9863ec6-d606-4011-85eb-8a4422f82159_productGalleryThumb.jpg",
                "https://image.ceneostatic.pl/data/products/113706425/f-samsung-galaxy-a52s-5g-sm-a528-6-128gb-czarny.jpg",
                "https://image.ceneostatic.pl/data/productGalleryThumb/113706425/productGalleryThumb.jpg",
                "https://image.ceneostatic.pl/data/productGalleryThumb/113706425/b147fdac-a0e2-42bd-afa1-2687dfd67af5_productGalleryThumb.jpg",
            ],
        }"""

