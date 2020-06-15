import pandas as pd
from torpy.http.requests import TorRequests
from requests.exceptions import ReadTimeout, ConnectTimeout, ConnectionError
import pickle
import re
import os
import sys
from tqdm import tqdm
from bs4 import BeautifulSoup
from typing import Union


def parse_title_ru(soup: BeautifulSoup) -> Union[str, None]:
    if (tag := soup.find("h1", class_='moviename-big')) is not None:
        return tag.text


def parse_title_orig(soup: BeautifulSoup) -> Union[str, None]:
    if (tag := soup.find("span", class_='alternativeHeadline')) is not None:
        return tag.text


def parse_duration(soup: BeautifulSoup) -> Union[str, None]:
    if (tag := soup.find("meta", itemprop="duration")) is not None:
        return tag['content']


def parse_slogan(soup: BeautifulSoup) -> Union[str, None]:
    if (tag := soup.find("td", text="слоган")) is not None:
        return tag.find_next("td").text


def parse_tabular(soup: BeautifulSoup, field: str) -> Union[str, None]:
    if (tags := soup.find("td", text=field)) is None:
        return
    item_list = [tag.text for tag in tags.parent.find_all("a")]
    if "..." in item_list:
        idx = item_list.index("...")
        item_list = item_list[:idx]
    return ', '.join(item_list)


def parse_cast(soup: BeautifulSoup) -> Union[str, None]:
    if (tags := soup.find("h4", text="В главных ролях:")) is None:
        return
    item_list = [tag.text for tag in tags.find_next("ul").find_all("li")]
    if "..." in item_list:
        idx = item_list.index("...")
        item_list = item_list[:idx]
    return ', '.join(item_list)


def parse_kinopoisk_score(soup: BeautifulSoup) -> Union[str, None]:
    if (tag := soup.find("span", class_="rating_ball")) is not None:
        return tag.text


def parse_imdb_score(soup: BeautifulSoup) -> Union[str, None]:
    if (tag := soup.find("div", style="color:#999;font:100 11px tahoma, verdana")) is not None:
        return re.search(r"IMDb: ([\d.]+) ", tag.text).group(1)


def parse_critics_score(soup: BeautifulSoup) -> Union[str, None]:
    if (tag := soup.find("div", class_="ratingNum")) is not None:
        return tag.text


def parse_synopsis(soup: BeautifulSoup) -> Union[str, None]:
    if (tag := soup.find("div", class_="brand_words film-synopsys")) is not None:
        return tag.text


if __name__ == '__main__':

    url = "https://www.kinopoisk.ru/film/{}"    # Pattern movie pages

    # Headers from browser request, change User-Agent after every ~300 requests if banned
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

    # Fields with interesting information
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
        parsed = {"id": []}   # Little hack, so parsed.query("id==..") at 131 won't raise exception

    # List of ids of interesting movies was parsed from kinopoisk search with a small script, with a 5 sec latency
    # and no proxy/tor/whatever
    with open("../data/movie_ids.dump", 'rb') as f:
        movie_ids = pickle.load(f)

    # Do not request pages that were already scrapped
    movie_ids = [movie_id for movie_id in movie_ids if (not movie_id in parsed['id'].astype(str).unique()) or
                 (parsed.query(f"id=='{movie_id}'").iloc[0]['title_ru'] is None)]

    parsed = parsed.dropna(subset=['title_ru']).drop_duplicates()

    pbar_ids = tqdm(total=len(movie_ids), position=0)   # Make progress bar
    movie_ids = iter(movie_ids)     # Make iterator from movie_ids list, so we can conveniently iterate by one
    movie_id = next(movie_ids)      # taking next id only after successful scrapping.

    # torpy package forces context-managers usage
    with TorRequests() as tor_requests:
        while True:     # Iterations over this cycle mean changing output TOR-node
            with tor_requests.get_session() as tr:      # Request new TOR-session wioth new output IP
                while True:     # Iterations over this cycle are done within same session with one IP
                    try:
                        r = tr.get(url.format(movie_id), headers=headers, timeout=5)  # Try to request page for movie
                    except (ReadTimeout, ConnectTimeout, ConnectionError):
                        break   # If banned go to outer cycle, request new TOR-session and try again the same movie

                    # Parse recieved page
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

                    if datadict['title_ru'] is None:    # If the page received was CAPTCHA-page, i.e. we were banned,
                        break                           # go to outer cycle, request new TOR-session and try again.
                    else:
                        parsed = parsed.append(datadict, ignore_index=True)     # Append result for movie to the rest
                        parsed.to_csv(output_path, index=False)     # Save current dataframe with appended row
                        try:
                            movie_id = next(movie_ids)      # Get next movie id
                            pbar_ids.update(1)              # Update progress bar
                        except ValueError:      # If all movies were scrapped
                            print("Finished")
                            sys.exit(0)
