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
import requests
from parsel import Selector
import random


# from ..items import ScraperItem

# Class name will start _ and then lower case domain without extension and word Spider as follow
# '_'+DOMAIN_WITHOUT_EXT+'Spider'
class _patagoniacomSpider(Spider):
    # spider name will start _ and then  lower case domain without extension as follow
    # '_'+DOMAIN_WITHOUT_EXT
    name = "_patagoniacom"
    allowed_domains = ["patagonia.com"]
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
        "https://www.patagonia.com/sitemap_0.xml",
        "https://www.patagonia.com/sitemap_1.xml",
        "https://www.patagonia.com/sitemap_2.xml",
        "https://www.patagonia.com/shop/womens-accessories",
    ]

    def __init__(self, *args, **kwargs):
        self.allowed_domains = (
            kwargs.get("allowed_domains", [])
            if kwargs.get("allowed_domains", [])
            else self.allowed_domains
        )
        # We need to add an aditional domain here where we will use in parse_options method
        self.allowed_domains.append("patagonia.com")
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

                try:
                    # Request with proxies is removed
                    # r = requests.get(url, headers=headers, proxies=proxies)
                    r = requests.get(url, headers=headers)
                    # Apply following pattern to extract all links from sitemap
                    pattern = "<loc>(.*?)</loc>"
                    m = re.findall(pattern, r.text, re.DOTALL)
                    i = 0
                    if len(m) > 0:
                        for x in m:
                            # Apply custom rule for each link found inside xml. If link is another xml file and contains products as follows
                            # send request to that xml too until we reach product html links.
                            if not x in self.foundlinks:
                                if (
                                    not x in self.foundlinks
                                    and x.find("/product/") != -1
                                ):
                                    i += 1
                                    self.log("%d - %s" % (i, x))
                                    self.foundlinks.append(x.strip())

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
                elif url.find("/shop/") != -1:
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
                        '//div[@class="product-tile__cover"]/a/@href'
                    ).extract()
                ],
            )
        )
        count = 1

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

        if (
            response.xpath(
                '//div[@class="show-more is-desktop-only"]/div/button/text()'
            )
            .get("")
            .strip()
            == "Load More"
        ):
            pages = ["https://www.patagonia.com/shop/womens-accessories"]
            for count, page in enumerate(pages):
                if count == 0:
                    count += 2
                page_url = page + f"?page={count}"
                if not page_url in self.foundlinks:
                    self.foundlinks.append(page_url)
                    yield scrapy.Request(
                        page_url,
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
                            '//h1[@id="product-title"]/text()'
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
                            '//meta[@itemprop="category"]/@content'
                        ).get("")
                    ],
                )
            ),
            "",
        )

        regular_price = (
            response.xpath('//span[@class="strike-through list"]/span/text()')
            .get("")
            .strip()
        )
        regular_price = regular_price.replace("$", "")
        item["regular_price"] = regular_price

        sale_price = (
            response.xpath('//span[@class="sales"]/span/text()').get("").strip()
        )
        sale_price = sale_price.replace("$", "")
        item["sale_price"] = sale_price
        item["colors"] = list(
            set(
                list(
                    filter(
                        bool,
                        [
                            e.strip()
                            for e in re.findall(
                                '<div>\s*<h3\s*class="product-tile\_\_name"\>([\w\W]*?)<\/h3>',
                                response.text,
                                re.DOTALL,
                            )
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
                                '<span\s*class\="cta\-circle__heading\s*h9"\>([\w\W]*?)<\/span>',
                                response.text,
                                re.DOTALL,
                            )
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
                                '//div[@class="img-wrapper"]/meta[@itemprop="image"]/@content'
                            ).extract()
                        ],
                    )
                )
            )
        )

        review_url = response.xpath(
            '//span[contains(text(),"See All Reviews")]/parent::a/@href'
        ).get("")
        if review_url:
            review_link = response.urljoin(review_url)
            review_page = requests.get(review_link)
            review_page_sel = Selector(text=review_page.text)
            reviews = list(
                set(
                    list(
                        filter(
                            bool,
                            [
                                e.strip()
                                for e in re.findall(
                                    '<span class="review-text-js"\>([\w\W]*?)<\/span>\s*<\/p>',
                                    review_page.text,
                                    re.DOTALL,
                                )
                            ],
                        )
                    )
                )
            )
            reviews = [re.sub(r"<[^>]*?>", "", x) for x in reviews]
            reviews = [re.sub(r"&#41;... Read More", "", x) for x in reviews]
            reviews = [re.sub(r"&#x27;", "'", x) for x in reviews]
            reviews = [re.sub(r"&amp;&#35;x27;", "'", x) for x in reviews]
            reviews = [re.sub(r"... Read More", "", x) for x in reviews]
            reviews = [re.sub(r"&#40;", "", x) for x in reviews]
            item["reviews"] = reviews
            reviews_count = review_page_sel.xpath(
                '//span[@data-default="All {0} Reviews"]/text()'
            ).get("")
            reviews_count = int(
                reviews_count.replace("All", "").replace("Reviews", "").strip()
            )
            item["reviews_count"] = reviews_count
            review_rating = review_page_sel.xpath(
                '//span[@class="rounded-rating-js"]/text()'
            ).get("")
            review_rating = review_rating.replace("/5", "").strip()
            item["rating"] = review_rating

        # Finally yielding item
        yield item


# Output {'name': 'Nano-Air™ Face Mask', 'url': 'https://www.patagonia.com/product/nano-air-face-mask/12102.html?dwvar_12102_color=CTRB&cgid=womens-hats-accessories', 'category': 'W', 'regular_price': '', 'sale_price': '15', 'colors': ['Crater Blue (CTRB)', 'Ink Black (INBK)'], 'sizes': ['M/L'], 'reviews': ['Fantastic Mask! Working full-time while wearing a mask has been a tough transition and Nano-Air is my favorite reusable mask. I recommend washing on cool with no laundry detergent (the detergent can make your face irritated).', 'I CAN NOT SAY ENOUGH!!! GOOD THINGS!!! ABOUT THESE NANO AIR MASKS!!! GREAT FIT!!! COMFORTABLE!!! FAIR PRICED!!! SIMPLY PUT!!! TOP QUALITY!!! I OWN 8 OF THEM!!! I SUGGEST YOU DO THE SAME!!! EXCELLENT MASK!!! A+++', 'I was so excited about getting these masks, I ordered three! They are super comfortable, a load off my ears, and are so easy to wash. However, I work in a business where I talk a lot with clients, and whenever I talk, the mask goes into my mouth. I end up having to hold the mask away from my mouth when Im talking, which makes for a frustrating interaction. Additionally, the fabric sometimes irritates my skin, leaving my face a little red. Ive noticed this only happens with the blue mask, not the black masks, though. Overall, I still like the mask because it doesnt pull on my ears, but the eating the mask thing is certainly a drag.', "I've bought a ton of different face mask to solve the problem of glasses steaming up, including those plastic face mask brackets, and nothing has worked....until I tried these mask. The fabric really does breath very well although I wish there was a pocket for filters. I was worried the head strap wasn't going to be either too tight or too lose, but it's actually perfect and holds well while still being able to take on and off freely. The salesman at the S.F. store recommended putting on a small plastic toggle lock to hold the bottom two straps together so you can adjust their tightness and length much easier.\nLastly I have found these mask for some reason, in typical Patagonia fashion, look better than other mask which makes wearing them in added plus.", "After trying tons of masks designed for outdoor activities, I've settled on this this as one of my favorites. It seems to do a great job of filtration and the coverage is nice so you're not sucking air through gaps but actually breathing through the fabric. I just walked for a few minutes in a blizzard I work on a mountain&#41; and within minutes of stepping inside my office, the mask had dried out. It's also comfortable and can be worn under a helmet which is great. The only thing I wish it had is a flexible nose bridge as the only gaps in this mask (on my face) are between the bridge of my nose and my cheeks. A bit of air escapes and enters through that gap making it slightly less effective and with prolonged use, that air irritates my eyes. I also wear it with a silicon mask bracket to keep the fabric away from my mouth and with the exception of the previously mentioned nose/cheek gap, it works great! All in all, it's an awesome mask and I just ordered more so I can swap them throughout the day.", 'I am a high school teacher so I wear a mask all day and I have to do a lot of talking. I have tried many masks and this is by far the best one I have found. It fits well, is comfortable, doesnt make me feel as if I am suffocating when I talk, and it doesnt move fall off my nose or pull up below my chin&#41; when I talk. Feels super light and does not constantly irritate or tickle my face like many other masks I have tried. Nice color as well.', 'Great product, easy to get used to, breathable and so convenient. Another great Patagonia product.', 'I BOUGHT S/M M/L SIZE. I LOVE BOTH OF THEM. THE S/M IS A TRUE SIZE FITS MY FACE. WITH M/L I CAN DOUBLE MASK INSIDE,WHICH IS NICE. THE ONLY SUCKY PART IS THAT WHEN I BREATHE, THE MASK SUCKS INTO MY NOSE OR MOUTH MOUTH BREATHER&#41;. BUT I BOUGHT THIS COOL TURTLE FROM HOMEDEPOT AND IT WORKED. I LOVE FOR NOT HAVING A MASK THAT LOOPS AROUND MY EARS. I LIKE EM. I BOUGHT FIVE (5) - CHANGE ONE A DAY. ITS MORE SANITARY THAT WAY. THANKS DUDES FOR MAKING THIS.', "I love where the profits go, and the practicality and better protection of the ties. However, without a nose wire and filter pocket the mask is not useful for me! A nose wire fits the mask more closely to my face better safety for others&#41; and combined with a filter pocket with a paper towel or coffee filter inside, masks don't fog my glasses AND protect others better. Please modify the design, to protect customers and everyone else around us.", 'I love the the mask, just wish it had a metal nose strip to stop my breath from going into my eyes. Maybe I will try and sew one in.\nOtherwise, it is a very comfortable mask. Love that it hangs around the neck and is super quick and easy to throw back on when needed.', 'This is one of my best and favorite masks for Covid safety. Does not say or drool over time. I am and school teacher and many masks fall down after a prolonged time speaking And this mask stays snug and comfy! My only slight&#41; concern is that it is very thin and I wonder if it provides as much protection as other masks- although it does shave two layers of capilene. I love it. Wish they offered more colors.', "Love the lightweight feel of this mask. Breathable for hiking and running and doesn't get damp and sweated out like some. I like how it fits on my face with the one loop around your head and another that you tie so it doesn't pinch on my ears&#41;. I don't like it for extended wear however or when it's cold out as I breathe more heavily and find that the fabric sits too close to my mouth -- for those times, I really prefer masks that have a nose clip to allow some space between the fabric and face. But otherwise a great mask (and fits smaller faces well).", 'The mask is great in that it is secure enough to stay in place while you are having a conversation (other masks that I have purchased tend to slide down as I speak). The fact that it loops completely around the back of your head means that you can slide it down to your neck while eating/drinking, and then just pull it up when you are done.', "I'm not sure how it's possible but this mask is both too tight and too loose simultaneously! The top elastic is too tight resulting in discomfort around my nose, but the mouth area is too loose allowing the fabric to migrate into my mouth when i talk. I agree with another reviewer, for quick trips to the grocery with minimum interaction this mask is fine, but for work or any activity that requires frequent comunication this mask immediately sucks into my mouth and becomes very wet and saggy. I also agree with a previous user that ear loops or adjustable head loops are prefered to a fixed top strap. All in all, I would rather use a disposable N95", 'It fits great and has a good seal even though there is no nose bridge piece. Im able to wear my glasses without them fogging up too much. Its breathable and my voice is not muffled. I have to wear a mask for 8 hours straight for work and I have had no issues. I barely notice its on to be honest. I prefer the tie back opposed to ear loop masks. I could easily run with this or do any other exerting activity if needed. My local indoor climbing gym requires a mask at all times and this mask is perfect for that.', 'I have a birdwell mask which I love but cannot breathe in. I got two for myself and my wife and we both love them. Walked around campus and worn it with another mask underneath. No issues.', 'At first I was wary of buying a face mask that wasnt elastic ear loops, but put my faith in the companys ability to innovate everything they do- thankfully it paid off. The mask is comfortable, light, and form-fitting. Additionally, the straps all have a bit of stretch to them which helps immensely. 10/10', 'I love this great mask as you can put it around your neck and not worry about losing it. It provides good protection and is breathable. I have worn a variety of masks during this pandemic and this one is the absolute best. I would love to see it offered in more colors.', 'Size is good. Fit kinda narrow. The tag is too long', 'Perfect. I own quite a few of these, got a few friends stoked on them as well. Best mask to climb in.', 'This is a great quality mask, however the sizing is way off! As a petite female and based on reading the reviews, I went with the xs/s and it is so tight and uncomfortable it hurts my ears and leaves marks on my face. Would like to exchange but dont think that is an option with masks.', 'I really like the weight and breath-ability of the material, but I found the upper elastic band to be slightly uncomfortably tight. Its fine for a quick trip to the store but I dont wear it at work because it ends up digging into my cheeks, so its fallen out of rotation. I wear a 7 5/8 hat for reference.', 'This is one of my favorite masks to wear for personal/professional use and I find it beyond comfortable! Just disappointed that its never available in my size in black or any other color outside of the blue/turquoise.\nHighly recommend it tho!', "I was hoping this mask would be an improvement on my disposable ear-loop N95 masks, but it's not. The fabric on this mask is too loose and makes it hard to breath during a hike or bike ride. The obvious thing is to take it off, but without ear-loops this mask takes longer to put back on when someone is passing on the trail again, my ear-loop N95 masks are super quick to put back on). I still use my N95 masks for mountain biking as well (as they are pointed like a beak and are aerodynamic as well).\nAll in all, this Patagonia face mask is great for non-aerobic longterm wear (like, if you're walking around town) but nothing that requires huffing and puffing. Nice materials, but bad design for athletic activities.", "This is a great lightweight face mask. I walk to work every day and spend time walking around a pretty hilly campus. I needed a mask for everyday use as well as going on runs and climbing. This is a very breathable and lightweight mask that I can sometimes almost forget I'm wearing.\nThe one problem is that it seems to hold quite a stink. My other face masks don't keep this stink despite being made of thicker material. Obviously this says something about my coffee breath, but it's notable to me that this mask seems stinkier than my cotton or disposable ones.", "Love the mask. The stretchy ties are a very nice touch. The enormous product label inside seems a bad idea. And, even if it is snipped out it will likely leave a stub. Seems like it wasn't well planned out. I'd have given a 5 but label placement is a definite loss of 1 star", 'Mask fits well with a fine seal, It stays in place and does not wear out your ears!', 'I have a normal to small sized head and thought the small would fit better than the medium, but it is actually tight. The material, while very soft and comfortable and high quality , kind of sticks to your mouth because it is so thin.\nI wanted to love this because it is made very well but I havent worn it much.', 'The masks are not going away... This mask was engineered with the user in mind. No stress on the ears. The tie end works perfect for a loose fit on the neck. The mask fits comfortably on the face, and the top elastic band is almost ideal for any situation. The only time I have had trouble putting it on, it when I am wearing a ball cap, forward.', 'The only one I want to wear. I lose masks like crazy, this stays around my neck the whole day for easy on and off. Easy to breath in while walking and cycling. The only mask needed.', 'I am completely satisfied with this mask ! I can breath in this mask. I was not able to breath I. Other masks and even then the others didnt really wrap the face and feel like I was breathing g through a filtered material. This mask actua wed like to mask. This mask is great for gym, campus &amp; masking up in vans with students.', "I bought this mask for myself XS/S - I have a small head/face&#41; and for my husband M/L&#41;. We both love these masks easily our favorites&#41;. It's perfect for wearing with a beanie, for quick on/off while on a run/hike outdoors where you want to have a mask for passing other people, for rock climbing, etc.. I love that I can tie it around my neck when not using and then pull the other strap up easily. Nice to have a break from masks behind my ears. We'll be buying more.", "I can actually breathe in the mask. Had one from another company that I couldn't and this is night and day. Really like how it ties too. Dont hesitate.", 'I purchased this because I like buying Patagonia stuff, light on face and conforms to my face.', "This mask is very comfortable. It takes the pressure off of my ears with the elastic strap. I think that loose end that needs to be tied together is a little unnecessary for me personally, although others may find the ability to adjust the fit comforting. I did try to blow out a candle and I was unable to do so. I have also found that the light material is able to wick away moisture better than cotton. I haven't personally used it for exercising or other strenuous activities however it does fit snugly and I feel it is very secure.\nI really like the way it continues down past my chin and almost to my adam's apple. I have found that many masks become loose when I speak and my jaw pulls the material down off of my nose. That hasn't been a problem so far. I have to say that overall the mask just feels very premium and I am very happy with it. I have ordered another one for my girlfriend because I am happy.\nIn the pictures on the website, I thought the color was black but in person, I would probably call it more of a charcoal color or very dark grey. It's not an issue for me but others may want to know.", "Finally found THE most comfortable mask. Super lightweight and wicks away moisture. Practically nonexistent. I wear a mask at work at least 10 hours a day. I cut the head strap and just tie both ties behind the ears. Doesn't bind or hurt my ears at all. I wear too many different hats at work, literally, and the head strap just got in the way. Glasses still fog up but much less than other masks. If they had other colors I would buy them. Perfect Christmas gift to my sporty family members! The smaller mask is definitely too snug and less comfy than the larger one.", 'The masks breathe nicely, but are small! I purchase a M/L. I usually buy Patagonia mens clothing in a Medium. The upper strap is tight around my head, and the fabric is very tight across the bridge of my nose to the point of discomfort. Yet, they are the most breathable I have found. I also do not have any of the odor issues I read about in other reviews.', 'This is probably one of the best fitting most comfortable masks that I have worn. The ties around the head and neck are far superior than having the ties around the ears.', "The mask is thin, lightweight, and comfotable. My only complaint is the size of the tag that is on the inside of the mask. I'll probably be cutting it out soon. Otherwise, it is a nice. I agree with another review that I wish they came in more colors.", 'Its easy to slip on and off and yet maintains the kind of snugness you want to feel.', 'Purchased this mask when mask requirements first started and havent looked back. Its the only mask I wear now. They way it fits around your head makes it very easy to pull down if youre eating/drinking and it is perfect for working out. Also I purchased the blue and it was darker than expected, but looks better than pictured', 'Wow. At last. Took 7 months into the pandemic, but here is the perfect mask. The fact that it has one fixed strap and one that ties means that it is easy to get on and off, while also being easy to get the perfect fit.', 'This is the perfect mask and the only one I want to wear most days. Best fit for a long period of time and easiest to both talk and be active in.', "This mask has all the right ingredients to be the perfect face mask. The material is lightweight and soft, the appearance is neutral and cool. Unfortunately the tightness mentioned by other users is very uncomfortable. I bought a small for myself and a large for my partner. Both of us experienced lines on our cheeks and nose after wearing for less than an hour! The mask also quickly gets wet and uncomfortable. There are much better masks on the market for far less $$. I'll be returning.", 'This mask is excellent. Super comfortable, fits well, and is breathable. Glad that I bought two for multiple uses.', "This is my favorite of all mask styles I've tried so far. The elastic headband and ties make the size perfect and make the mask fit snugly without being tight, even over the bridge of my nose, and avoid stress on my ears. My glasses rarely fog up and even then only minimally. Wish they were available in stores and in more colors--I plan to buy more.", "I bought both sizes figuring hubby could wear the larger, but the M/L does fit better on my round face than the S/M. Love how well this mask covers so there is no gap between cheeks and nose so you are breathing through the mask instead of gaps alongside the nose. Very comfy with stretch. I added a toggle to one set of straps so easy to adjust the straps. My search is finally over after 8.5 months. You'll need masks again in the future. Buy it!", 'This is a form fitting face mask. No gaps for aerosol droplets to slip through. Achieved with stretch in material and a little extra cloth folded into mask if needed.', "The material is soft and breathable and very lightweight. I find breathing to be comfortable and not restricted.\nThe mask covers my face easily from the bridge of my nose to under my chin. I don't have a big head/face and there is plenty of extra length left after tying it around the back of my neck. Seems like it would accommodate most head sizes. I was initially on the fence between the smaller vs larger size. I'm glad I went larger. I think most adults would be happier with the larger size for better coverage and comfort."], 'reviews_count': 50, 'rating': '4.4', 'images': ['https://www.patagonia.com/dw/image/v2/BDJB_PRD/on/demandware.static/-/Sites-patagonia-master/default/dw578268fe/images/hi-res/12102_INBK.jpg?sw=1600&sh=1600&sfrm=png&q=80&bgcolor=f6f6f6', 'https://www.patagonia.com/dw/image/v2/BDJB_PRD/on/demandware.static/-/Sites-patagonia-master/default/dwd77a2590/images/hi-res/12102_CTRB.jpg?sw=1600&sh=1600&sfrm=png&q=80&bgcolor=f6f6f6']}
