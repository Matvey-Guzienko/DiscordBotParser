import time

import requests
from bs4 import BeautifulSoup

from config import Config

session = requests.Session()

session.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0.1; SM-A500H) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Mobile Safari/537.36"
    }
)


def login_finviz():
    session.post(
        "https://finviz.com/login_submit.ashx",
        data={"email": Config.FINVIZ_EMAIL, "password": Config.FINVIZ_PASSWORD},
    ).raise_for_status()


def get_stock_data(name: str, with_chart: bool = True):
    url = f"https://finviz.com/quote.ashx?t={name}&p=d"

    resp = session.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    data = {}
    data_elements = soup.find_all("td", attrs={"class": "snapshot-td2"})

    if len(data_elements) == 0:
        data["error"] = "no data"
        return data
    else:
        last_news_url = soup.find("a", attrs={"class": "tab-link-news"}).attrs["href"]

        data["URL"] = url
        data["Last News URL"] = last_news_url

        for i in range(0, len(data_elements) - 1, 2):
            name_el = data_elements[i]
            value_el = data_elements[i + 1]

            data[name_el.text] = value_el.text

    if with_chart:
        data[
            "Chart URL"
        ] = f"https://charts2.finviz.com/chart.ashx?t={name}&ty=c&ta=1&p=d&s=l&timestamp={time.time()}"

    return data
