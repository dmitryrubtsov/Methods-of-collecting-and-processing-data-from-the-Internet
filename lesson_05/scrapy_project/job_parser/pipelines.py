# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html


from pymongo import MongoClient


class JobParserPipeline(object):
    def __init__(self):
        MONGO_URI = 'mongodb://172.17.0.2:27017/'
        MONGO_DATABASE = 'vacancy_db'

        client = MongoClient(MONGO_URI)
        self.mongo_base = client[MONGO_DATABASE]

    def process_item(self, item, spider):
        if spider.name == 'superjob_ru':
            item['salary'] = self.salary_parse_superjob(item['salary'])

        vacancy_name = ''.join(item['name'])

        salary_min = item['salary'][0]
        salary_max = item['salary'][1]
        salary_currency = item['salary'][2]
        vacancy_link = item['vacancy_link']
        site_scraping = item['site_scraping']

        vacancy_json = {
            'vacancy_name': vacancy_name, \
            'salary_min': salary_min, \
            'salary_max': salary_max, \
            'salary_currency': salary_currency, \
            'vacancy_link': vacancy_link, \
            'site_scraping': site_scraping
        }

        collection = self.mongo_base[spider.name]
        collection.insert_one(vacancy_json)
        return vacancy_json

    def salary_parse_superjob(self, salary):
        salary_min = None
        salary_max = None
        salary_currency = None

        for i in range(len(salary)):
            salary[i] = salary[i].replace(u'\xa0', u'')

        if salary[0] == 'до':
            salary_max = salary[2]
        elif len(salary) == 3 and salary[0].isdigit():
            salary_max = salary[0]
        elif salary[0] == 'от':
            salary_min = salary[2]
        elif len(salary) > 3 and salary[0].isdigit():
            salary_min = salary[0]
            salary_max = salary[2]

        salary_currency = self._get_name_currency(salary[-1])

        result = [
            salary_min, \
            salary_max, \
            salary_currency
        ]
        return result

    def _get_name_currency(self, currency_name):
        currency_dict  = {
            'EUR': {'€'}, \
            'KZT': {'₸'}, \
            'RUB': {'₽', 'руб.'}, \
            'UAH': {'₴', 'грн.'}, \
            'USD': {'$'}
        }

        name = None

        for item_name, items_list in currency_dict.items():
            if currency_name in items_list:
                name = item_name

        return name
