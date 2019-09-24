from bs4 import BeautifulSoup as bs
from pprint import pprint
from pymongo import MongoClient
import json
import re
import requests


class ScrapingJob():

    def __init__(self, mongodb_uri, db_name, collection_name):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:69.0) Gecko/20100101 Firefox/69.0'
        }
        self.link_hh = 'https://hh.ru/search/vacancy'
        self.link_seperjob = 'https://www.superjob.ru/vacancy/search/'

        self.mongodb = MongoClient(mongodb_uri)
        self.db = self.mongodb[db_name]
        self.collection = self.db[collection_name]

    def print_salary(self, salary):
        objects = self.collection.find({'salary_max': {'$gt': salary}})
        for obj in objects:
            pprint(obj)

    def search_job(self, vacancy):
        self._parser_hh(vacancy)
        self._parser_superjob(vacancy)

    def _parser_hh(self, vacancy):
        params = {
            'text': vacancy, \
            'search_field': 'name', \
            'items_on_page': '100', \
            'page': ''
        }

        html = self._get_html(self.link_hh, params)

        last_page = self._get_last_page_hh(html)

        for page in range(0, last_page):
            params['page'] = page
            html = self._get_html(self.link_hh, params)

            if html.ok:
                parsed_html = self._get_parsed_html(html)

                vacancy_items = parsed_html.find('div', {'data-qa': 'vacancy-serp__results'}) \
                                            .find_all('div', {'class': 'vacancy-serp-item'})
                for item in vacancy_items:
                    vacancy = self._parser_item_hh(item)

                    if self._is_exists('vacancy_link', vacancy['vacancy_link']):
                        self.collection.update_one({'vacancy_link': vacancy['vacancy_link']}, {'$set': vacancy})
                    else:
                        self.collection.insert_one(vacancy)

    def _parser_superjob(self, vacancy):
        params = {
            'keywords': vacancy, \
            'profession_only': '1', \
            'geo[c][0]': '15', \
            'geo[c][1]': '1', \
            'geo[c][2]': '9', \
            'page': ''
        }

        html = self._get_html(self.link_seperjob, params)

        last_page = self._get_last_page_superjob(html)

        for page in range(0, last_page + 1):
            params['page'] = page
            html = self._get_html(self.link_seperjob, params)

            if html.ok:
                parsed_html = self._get_parsed_html(html)

                vacancy_items = parsed_html.find_all('div', {'class': 'f-test-vacancy-item'})

                for item in vacancy_items:
                    vacancy = self._parser_item_superjob(item)

                    if self._is_exists('vacancy_link', vacancy['vacancy_link']):
                        self.collection.update_one({'vacancy_link': vacancy['vacancy_link']}, {'$set': vacancy})
                    else:
                        self.collection.insert_one(vacancy)

    def _parser_item_hh(self, item):
        vacancy_data = {}

        # vacancy_name
        vacancy_name = item.find('div', {'class': 'resume-search-item__name'}) \
                            .getText() \
                            .replace(u'\xa0', u' ')

        vacancy_data['vacancy_name'] = vacancy_name

        # company_name
        company_name = item.find('div', {'class': 'vacancy-serp-item__meta-info'}) \
                            .getText() \
                            .replace(u'\xa0', u' ')

        vacancy_data['company_name'] = company_name

        # city
        city = item.find('span', {'class': 'vacancy-serp-item__meta-info'}) \
                    .getText() \
                    .split(', ')[0]

        vacancy_data['city'] = city

        #metro station
        metro_station = item.find('span', {'class': 'vacancy-serp-item__meta-info'}).findChild()

        if not metro_station:
            metro_station = None
        else:
            metro_station = metro_station.getText()

        vacancy_data['metro_station'] = metro_station

        #salary
        salary = item.find('div', {'class': 'vacancy-serp-item__compensation'})

        salary_min = None
        salary_max = None
        salary_currency = None

        if salary:

            salary = salary.getText() \
                            .replace(u'\xa0', u'')

            salary = re.split(r'\s|-', salary)

            if salary[0] == 'до':
                salary_max = int(salary[1])
            elif salary[0] == 'от':
                salary_min = int(salary[1])
            else:
                salary_min = int(salary[0])
                salary_max = int(salary[1])

            salary_currency = salary[-1]
            salary_currency = self._get_name_currency(salary_currency)

        vacancy_data['salary_min'] = salary_min
        vacancy_data['salary_max'] = salary_max
        vacancy_data['salary_currency'] = salary_currency

        # vacancyId
        vacancy_json = json.loads(item.find('script', {'data-name': 'HH/VacancyResponsePopup/VacancyResponsePopup'})['data-params'])

        vacancy_id = vacancy_json['vacancyId']

        # link
        vacancy_data['vacancy_link'] = f'https://hh.ru/vacancy/{vacancy_id}'

        # site
        vacancy_data['site'] = 'hh.ru'

        return vacancy_data

    def _parser_item_superjob(self, item):
        vacancy_data = {}

        # vacancy_name
        vacancy_name = item.find_all('a')
        if len(vacancy_name) > 1:
            vacancy_name = vacancy_name[-2].getText()
        else:
            vacancy_name = vacancy_name[0].getText()
        vacancy_data['vacancy_name'] = vacancy_name

        # company_name
        company_name = item.find('span', {'class': 'f-test-text-vacancy-item-company-name'})

        if not company_name:
            company_name = item.findParent() \
                                .find('span', {'class': 'f-test-text-vacancy-item-company-name'}) \
                                .getText()
        else:
            company_name = company_name.getText()

        vacancy_data['company_name'] = company_name

        # city
        company_location = item.find('span', {'class': 'f-test-text-company-item-location'}) \
                                .findChildren()[1] \
                                .getText() \
                                .split(',')

        vacancy_data['city'] = company_location[0]

        #metro station
        if len(company_location) > 1:
            metro_station = company_location[1]
        else:
            metro_station = None

        vacancy_data['metro_station'] = metro_station

        #salary
        salary = item.find('span', {'class': 'f-test-text-company-item-salary'}) \
                      .findChildren()
        salary_min = None
        salary_max = None
        salary_currency = None

        if salary:
            salary_currency = salary[-1].getText()
            salary_currency = self._get_name_currency(salary_currency)

            is_check_sarary = item.find('span', {'class': 'f-test-text-company-item-salary'}) \
                                    .getText() \
                                    .replace(u'\xa0', u' ') \
                                    .split(' ', 1)[0]
            if is_check_sarary == 'до' or len(salary) == 2:
                 salary_max = int(salary[0].getText() \
                                            .replace(u'\xa0', u''))
            elif is_check_sarary == 'от':
                salary_min = int(salary[0].getText() \
                                             .replace(u'\xa0', u''))
            else:
                salary_min = int(salary[0].getText() \
                                             .replace(u'\xa0', u''))
                salary_max = int(salary[2].getText() \
                                             .replace(u'\xa0', u''))

        vacancy_data['salary_min'] = salary_min
        vacancy_data['salary_max'] = salary_max
        vacancy_data['salary_currency'] = salary_currency

        # link
        vacancy_link = item.find_all('a')

        if len(vacancy_link) > 1:
            vacancy_link = vacancy_link[-2]['href']
        else:
            vacancy_link = vacancy_link[0]['href']

        vacancy_data['vacancy_link'] = f'https://www.superjob.ru{vacancy_link }'

        # site
        vacancy_data['site'] = 'www.superjob.ru'

        return vacancy_data

    def _get_last_page_hh(self, html):
        parsed_html = self._get_parsed_html(html)

        if parsed_html:
            page_block = parsed_html.find('div', {'data-qa': 'pager-block'})
            if not page_block:
                last_page = 1
            else:
                last_page = int(
                    page_block.find_all('a', {'class': 'HH-Pager-Control'})[-2] \
                                .getText()
                                )

        return last_page

    def _get_last_page_superjob(self, html):
        parsed_html = self._get_parsed_html(html)

        if parsed_html:
            page_block = parsed_html.find('a', {'class': 'f-test-button-1'})
            if not page_block:
                last_page = 1
            else:
                page_block = page_block.findParent()
                last_page = int(
                    page_block.find_all('a')[-2] \
                                .getText()
                )

        return last_page

    def _get_parsed_html(self, html):
        if html.ok:
            parsed_html = bs(html.text,'html.parser')
            return parsed_html

    def _get_html(self, link, params=None):
        html = requests.get(link, params=params, headers=self.headers)
        return html

    def _is_exists(self, name_tags, field):
        return bool(self.collection.find_one({name_tags: { "$in": [field]}}))

    def _get_name_currency(self, currency_name):
        currency_dict  = {
            'EUR': {' €'}, \
            'KZT': {' ₸'}, \
            'RUB': {' ₽', 'руб.'}, \
            'UAH': {' ₴', 'грн.'}, \
            'USD': {' $'}
        }

        name = currency_name

        for item_name, items_list in currency_dict.items():
            if currency_name in items_list:
                name = item_name

        return name
