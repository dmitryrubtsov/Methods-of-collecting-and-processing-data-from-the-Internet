# -*- coding: utf-8 -*-
import scrapy
from scrapy.http import HtmlResponse
from job_parser.items import JobParserItem


class HhRuSpider(scrapy.Spider):
    name = 'hh_ru'
    allowed_domains = ['hh.ru']

    def __init__(self, vacancy=None):
        super(HhRuSpider, self).__init__()
        self.start_urls = [
            f'https://hh.ru/search/vacancy?area=1&st=searchVacancy&text={vacancy}'
        ]

    def parse(self, response: HtmlResponse):
        next_page = response.css('a.HH-Pager-Controls-Next::attr(href)') \
            .extract_first()

        yield response.follow(next_page, callback=self.parse)

        vacancy_items  = response.css(
            'div.vacancy-serp \
            div.vacancy-serp-item \
            div.vacancy-serp-item__row_header \
            a.bloko-link::attr(href)'
        ).extract()

        for vacancy_link in vacancy_items:
            yield response.follow(vacancy_link, self.vacancy_parse)

    def vacancy_parse(self, response: HtmlResponse):
        name = response.css(
            'div.vacancy-title \
            h1.header ::text'
        ).extract()

        salary = [
            response.css(
                'span[itemprop="baseSalary"] meta[itemprop="minValue"] ::attr(content)' \
            ).extract_first(), \

            response.css(
                'span[itemprop="baseSalary"] meta[itemprop="maxValue"] ::attr(content)' \
            ).extract_first(), \

            response.css(
                'span[itemprop="baseSalary"] meta[itemprop="currency"] ::attr(content)' \
            ).extract_first()
        ]

        vacancy_link = response.url
        site_scraping = self.allowed_domains[0]

        yield JobParserItem(
            name=name, \
            salary=salary, \
            vacancy_link=vacancy_link, \
            site_scraping=site_scraping
        )
