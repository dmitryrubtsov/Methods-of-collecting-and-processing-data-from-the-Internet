from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common import exceptions
from pymongo import MongoClient
from selenium.webdriver.firefox.options import Options


def _parse_element(element, css_selector):
    result = WebDriverWait(element, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))).text
    return result


def parse_email(element):
    item = {}

    item['from_name'] = _parse_element(
        element, 'span[class~="ns-view-message-head-sender-name"]')
    item['from_email'] = _parse_element(
        element, 'span[class~="mail-Message-Sender-Email"]')
    item['date'] = _parse_element(element,
                                  'div[class~="ns-view-message-head-date"]')
    item['subject'] = _parse_element(
        element, 'div[class~="mail-Message-Toolbar-Subject"]')
    item['text_messege'] = _parse_element(
        element, 'div.mail-Message-Body-Content')

    return item


MONGO_URI = 'mongodb://172.17.0.2:27017/'
MONGO_DATABASE = 'mail_db'

client = MongoClient(MONGO_URI)
mongo_base = client[MONGO_DATABASE]
collection = mongo_base['messeges']

firefox_options = Options()
firefox_options.add_argument("--headless")

driver = webdriver.Firefox()

url = 'https://yandex.ru/'
title_site = 'Яндекс'

driver.get(url)

assert title_site in driver.title

try:
    mail_button = driver.find_element_by_css_selector(
        'a[class="button desk-notif-card__login-enter-expanded button_theme_gray i-bem"]'
    )
except exceptions.NoSuchElementException:
    print('Mail login not found')

mail_button.click()

driver.title

if 'Авторизация' in driver.title:
    login_form = driver.find_element_by_css_selector('div[class="passp-auth"]')

    field_login = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, 'passp-field-login')))
    field_login.send_keys('tibo78')
    field_login.send_keys(Keys.ENTER)
    field_passwd = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, 'passp-field-passwd')))
    field_passwd.send_keys('yj7kba')
    field_passwd.send_keys(Keys.ENTER)

first_messege = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located(
        (By.CLASS_NAME, 'ns-view-messages-item-wrap')
    )
)
first_messege.click()

while True:
    try:
        collection.insert_one(parse_email(driver))

        button_next = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, 'след.')))
        button_next.click()
    except exceptions.TimeoutException:
        print('E-mails are over')
        break

driver.quit()
