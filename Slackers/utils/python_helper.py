import pyotp
from selenium import webdriver
from selenium.webdriver.chrome.service import Service


def init_selenium():
    service = Service(r"D:\VSC\martin_matijevic\chromedriver-win64\chromedriver.exe")
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def generate_2fa_code(TOTP_SECRET):
    totp = pyotp.TOTP(TOTP_SECRET)
    return totp.now()
