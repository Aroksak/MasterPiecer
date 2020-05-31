import pandas as pd
import numpy as np
import requests
from torpy.http.requests import TorRequests
from requests.exceptions import ReadTimeout, ConnectTimeout, ConnectionError
import pickle
import re
import os
import sys
import time
from tqdm import tqdm
from bs4 import BeautifulSoup


def parse_title_ru(soup):
    if (tag := soup.find("h1", class_='moviename-big')) is not None:
        return tag.text


def parse_title_orig(soup):
    if (tag := soup.find("span", class_='alternativeHeadline')) is not None:
        return tag.text


def parse_duration(soup):
    if (tag := soup.find("meta", itemprop="duration")) is not None:
        return tag['content']


def parse_slogan(soup):
    if (tag := soup.find("td", text="слоган")) is not None:
        return tag.find_next("td").text


def parse_tabular(soup, field):
    if (tags := soup.find("td", text=field)) is None:
        return
    item_list = [tag.text for tag in tags.parent.find_all("a")]
    if "..." in item_list:
        idx = item_list.index("...")
        item_list = item_list[:idx]
    return ', '.join(item_list)


def parse_cast(soup):
    if (tags := soup.find("h4", text="В главных ролях:")) is None:
        return
    item_list = [tag.text for tag in tags.find_next("ul").find_all("li")]
    if "..." in item_list:
        idx = item_list.index("...")
        item_list = item_list[:idx]
    return ', '.join(item_list)


def parse_kinopoisk_score(soup):
    if (tag := soup.find("span", class_="rating_ball")) is not None:
        return tag.text


def parse_imdb_score(soup):
    if (tag := soup.find("div", style="color:#999;font:100 11px tahoma, verdana")) is not None:
        return re.search(r"IMDb: ([\d.]+) ", tag.text).group(1)


def parse_critics_score(soup):
    if (tag := soup.find("div", class_="ratingNum")) is not None:
        return tag.text


def parse_synopsis(soup):
    if (tag := soup.find("div", class_="brand_words film-synopsys")) is not None:
        return tag.text


if __name__ == '__main__':

    url = "https://www.kinopoisk.ru/film/{}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36',
        'Accept': 'https://www.kinopoisk.ru/top/',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.5',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Host': 'www.kinopoisk.ru',
        'TE': 'Trailers',
        'Upgrade-Insecure-Requests': '1'
    }

    datadict = {
        "id": [],
        "title_ru": [],
        "title_orig": [],
        "duration": [],
        "slogan": [],
        "year": [],
        "country": [],
        "director": [],
        "cast": [],
        "script": [],
        "producer": [],
        "operator": [],
        "composer": [],
        "artist": [],
        "montage": [],
        "genre": [],
        "budget": [],
        "cash_USA": [],
        "cash_total": [],
        "cash_russia": [],
        "kinopoisk_score": [],
        "imdb_score": [],
        "critics_score": [],
        "synopsis": []
    }

    output_path = "../data/kinopoisk.csv"

    if os.path.exists(output_path):
        parsed = pd.read_csv(output_path)
    else:
        parsed = {"id": []}

    with open("../data/movie_ids.dump", 'rb') as f:
        movie_ids = pickle.load(f)

    movie_ids = [movie_id for movie_id in movie_ids if (not movie_id in parsed['id'].astype(str).unique()) or
                 (parsed.query(f"id=='{movie_id}'").iloc[0]['title_ru'] is None)]
    
    parsed = parsed.dropna(subset=['title_ru']).drop_duplicates()

    pbar_ids = tqdm(total=len(movie_ids), position=0)
    movie_ids = iter(movie_ids)
    movie_id = next(movie_ids)

    with TorRequests() as tor_requests:
        while True:
            with tor_requests.get_session() as tr:
                while True:
                    try:
                        r = tr.get(url.format(movie_id), headers=headers, timeout=5)
                    except (ReadTimeout, ConnectTimeout, ConnectionError):
                        break
                    soup = BeautifulSoup(r.text, "lxml")
                    datadict['id'] = movie_id
                    datadict['title_ru'] = parse_title_ru(soup)
                    datadict['title_orig'] = parse_title_orig(soup)
                    datadict['year'] = parse_tabular(soup, "год")
                    datadict['country'] = parse_tabular(soup, "страна")
                    datadict['duration'] = parse_duration(soup)
                    datadict['slogan'] = parse_slogan(soup)
                    datadict['director'] = parse_tabular(soup, "режиссер")
                    datadict['script'] = parse_tabular(soup, "сценарий")
                    datadict['artist'] = parse_tabular(soup, "художник")
                    datadict['producer'] = parse_tabular(soup, "продюсер")
                    datadict['composer'] = parse_tabular(soup, "композитор")
                    datadict['montage'] = parse_tabular(soup, "монтаж")
                    datadict['operator'] = parse_tabular(soup, "оператор")
                    datadict['genre'] = parse_tabular(soup, "жанр")
                    datadict['budget'] = parse_tabular(soup, "бюджет")
                    datadict['cash_USA'] = parse_tabular(soup, "сборы в США")
                    datadict['cash_total'] = parse_tabular(soup, "сборы в мире")
                    datadict['cash_russia'] = parse_tabular(soup, "сборы в России")
                    datadict['kinopoisk_score'] = parse_kinopoisk_score(soup)
                    datadict['imdb_score'] = parse_imdb_score(soup)
                    datadict['critics_score'] = parse_critics_score(soup)
                    datadict['cast'] = parse_cast(soup)
                    datadict['synopsis'] = parse_synopsis(soup)
                    if datadict['title_ru'] is not None:
                        parsed = parsed.append(datadict, ignore_index=True)
                        parsed.to_csv(output_path, index=False)
                        try:
                            movie_id = next(movie_ids)
                            pbar_ids.update(1)
                        except ValueError:
                            print("Finished")
                            sys.exit(0)
                    else:
                        break
