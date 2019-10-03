# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy
from scrapy.loader.processors import Compose, MapCompose, TakeFirst


def cleaner_url(url):
    if url[:2] == '//':
        return f'https:{url}'
    return url


def parse_params(params):
    result = {}
    for i in range(0, len(params), 3):
        key = params[i + 1].strip().strip(':').replace('\xa0', ' ')
        value = params[i + 2].strip().replace('\xa0', ' ')
        result[key] = value

    return result


class AvitoAutoItem(scrapy.Item):
    # define the fields for your item here like:
    _id = scrapy.Field()

    title = scrapy.Field(input_processor=MapCompose(lambda x: x.split(',')),
                         output_processor=TakeFirst())

    images = scrapy.Field(input_processor=MapCompose(cleaner_url))
    auto_params = scrapy.Field(output_processor=Compose(parse_params))
    url = scrapy.Field(output_processor=TakeFirst())
