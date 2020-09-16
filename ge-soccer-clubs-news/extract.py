#encoding=utf-8
import pandas as pd
import numpy as np
import pdb
import requests
import time
import random
import os
import glob
import sys

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from tqdm import tqdm_notebook, tqdm
from joblib import Parallel, delayed

PAGE_PREFIX = {"athletico-pr": "/pr",
               "atletico-go": "/go",
               "bahia": "/ba",
               "bragantino": "/sp/vale-do-paraiba-regiao",
               "ceara": "/ce",
               "coritiba": "/pr",
               "fortaleza": "/ce",
               "goias": "/go",
               "internacional": "/rs",
               "sport": "/pe",
               "gremio": "/rs"}

SERIES_A_TEAMS = ["athletico-pr", "atletico-go", "atletico-mg",
                  "bahia", "bragantino", "botafogo", "ceara", "corinthians",
                  "coritiba", "flamengo", "fluminense", "fortaleza", "goias",
                  "gremio", "internacional", "palmeiras", "santos", "sao-paulo",
                  "sport", "vasco", "cruzeiro"]

SAVING_PATH = "~/Documents/ge_news/"

def extract_news_from_page(page):
    html = requests.get(page).text
    soup = BeautifulSoup(html)

    links = soup.find_all("a",
                          {"class": "feed-post-link"},
                          href=True)
    links = [link["href"] for link in links]

    return links


def get_full_html_from_news(news_link, driver):

    driver.get(news_link)
    ### Scroll para carregar o restante da página
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    ### Aguardando carregar
    time.sleep(10)
    ## Clicando no botão de carregar mais comentários
#     more_comments = True
#     while more_comments:
#         try:
#             driver.find_element_by_class_name("glbComentarios-botao-mais").click()
#         except:
#             more_comments = False

    return driver.page_source

def get_title(soup):
    try:
        title = soup.find_all("h1", {"class": "content-head__title"})[0].text
    except:
        try:
            title = soup.find_all("h1", {"class": "entry-title"})[0].text
        except:
            title = None

    return title

def content_sportv(soup):
    content = soup.find_all("div",
                                {"class": "materia-conteudo entry-content"})

    paragraphs = content[0].findChildren("p", recursive=True)

    return paragraphs

def extract_text_from_news_link(news_link, driver):
    html = get_full_html_from_news(news_link, driver)
    soup = BeautifulSoup(html)

    try:
        date = soup.find_all("time")[0].text
    except:
        date = None

    title = get_title(soup)

    #print("Getting {}, from {}".format(title, date))
    paragraphs = soup.find_all("p",
                                {"class": "content-text__container "})

    if len(paragraphs) == 0:
        content = soup.find_all("div",
                                {"class": "corpo-conteudo"})
        if len(content) == 0:
            content = soup.find_all("div",
                                {"class": "materia-conteudo entry-content"})

        paragraphs = content[0].findChildren("p", recursive=True)

    paragraphs = [paragraph.text for paragraph in paragraphs]

    ### Filter date from first p element
    if date in paragraphs[0]:
        paragraphs = paragraphs[1:]

    article_text = "".join(paragraphs)
    data = pd.DataFrame([[date, title, article_text, news_link]],
                        columns=["date", "title", "article_text", "article_link"])
    return data

def get_all_files_in_a_folder(team, full=False):
    path = "{}data/{}".format(SAVING_PATH, team)

    files = [f for f in glob.glob(path + "**/*.csv", recursive=True)]

    if not full:
        files = [file.replace(path + "/", "") for file in files]
        files = [file.replace(".csv", "") for file in files]

    return files

def aggregate_all_saved_sections_from_zones_files(team):
    files = get_all_files_in_a_folder(team, full=True)

    all_dataframes = []
    for file in files:
        all_dataframes.append(pd.read_csv(file))

    return pd.concat(all_dataframes)


def news_from_soccer_club(team, n_pages=2):
    page_prefix = "https://globoesporte.globo.com/futebol/times/{}/index/feed/pagina-{}.ghtml"
    page_prefix = "https://globoesporte.globo.com/rs/futebol/times/{}/index/feed/pagina-{}.ghtml"
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Firefox(options=options, executable_path="/usr/local/bin/geckodriver")
    driver.implicitly_wait(5)

    try:
        data = pd.read_csv("{}data/{}.csv".format(SAVING_PATH, team), index_col=False)
        downloaded = list(data["article_link"].values)
        data.to_csv("{}data/backup-{}.csv".format(SAVING_PATH, team), index=False)
    except:
        downloaded = []
        data = pd.DataFrame()

    news_links = []
    for n_page in tqdm(range(1, n_pages + 1)):
        page = page_prefix.format(team, n_page)
        new_news_links = extract_news_from_page(page)
        news_links += new_news_links

    news_links = [link for link in news_links if "/noticia/" in link]

    #news_links = random.shuffle(news_links)
    news_links = [news_link for news_link in news_links if news_link not in downloaded]

    print("{} links to extract".format(len(news_links)))

    for i, news_link in enumerate(tqdm(news_links)):
        try:
            news_data = extract_text_from_news_link(news_link, driver)
            data = pd.concat([data, news_data], sort=True)
        except:
            print("Couldn't get from {}".format(news_link))
        if i % 5 == 0:
            #print("Saving {} news".format(len(data)))
            data.to_csv("{}data/{}.csv".format(SAVING_PATH, team), index=False)

    try:
        data["article_time"] = data["date"].apply(lambda x: x.strip().split(" ")[1] if not pd.isnull(x) else x)
        data["article_date"] = data["date"].apply(lambda x: x.strip().split(" ")[0] if not pd.isnull(x) else x)
        data.to_csv("{}data/{}.csv".format(SAVING_PATH, team), index=False)
    except:
        print("no date")

    driver.close()
    return data

def prepare_link_to_filename(link):
    link = link.replace("https://", "")
    link = link.replace("/", "-")
    link = link.replace(".", "-")

    return link
def team_section(team):
    return PAGE_PREFIX.get(team, "")

def news_from_soccer_club_single(team, start_page, end_page):
    page_prefix = "https://globoesporte.globo.com{}/futebol/times/{}/index/feed/pagina-{}.ghtml"
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Firefox(options=options, executable_path="/usr/local/bin/geckodriver")
    driver.implicitly_wait(5)

    directory = "{}data/{}".format(SAVING_PATH, team)

    if not os.path.isdir(directory):
        os.makedirs(directory, exist_ok=True)

    data = pd.DataFrame()

    downloaded = get_all_files_in_a_folder(team)

    news_links = []
    for n_page in tqdm(range(start_page, end_page + 1)):
        page = page_prefix.format(team_section(team), team, n_page)
        print(page)
        new_news_links = extract_news_from_page(page)
        news_links += new_news_links

    news_links = [link for link in news_links if "/noticia/" in link]

    #news_links = random.shuffle(news_links)
    news_links = [news_link for news_link in news_links if prepare_link_to_filename(news_link) not in downloaded]

    print("{} links to extract".format(len(news_links)))

    for i, news_link in enumerate(tqdm(news_links)):
        try:
            news_data = extract_text_from_news_link(news_link, driver)
            news_data.to_csv("{}data/{}/{}.csv".format(SAVING_PATH, team, prepare_link_to_filename(news_link)), index=False)
            #data = pd.concat([data, news_data], sort=True)
        except:
            print("Couldn't get from {}".format(news_link))
        #if i % 5 == 0:
            #print("Saving {} news".format(len(data)))
            #data.to_csv("data/{}.csv".format(team), index=False)

    data = aggregate_all_saved_sections_from_zones_files(team)
    try:
        data["article_time"] = data["date"].apply(lambda x: x.strip().split(" ")[1] if not pd.isnull(x) else x)
        data["article_date"] = data["date"].apply(lambda x: x.strip().split(" ")[0] if not pd.isnull(x) else x)
        data.to_csv("{}data/{}.csv".format(SAVING_PATH, team), index=False)
    except:
        print("no date")


    driver.close()


    return data

def single_page_fetcher(team, update_pages):
    page = np.random.randint(1, update_pages, 1)[0]
    news_from_soccer_club_single(team, page, page + 1)


if "__main__":
    mode = sys.argv[1]
    update_pages = sys.argv[2]

    if mode == "update":
        for team in SERIES_A_TEAMS:
            print(team)
            for page_number in range(1, int(update_pages) + 1):
                try:
                    news_from_soccer_club_single(team,
                                                 page_number,
                                                 page_number + 1)
                except:
                    print(team)
    elif mode == "all":
        n_hits = sys.argv[3]
        for team in SERIES_A_TEAMS:
            for i in range(int(n_hits)):
                try:
                    single_page_fetcher(team, update_pages)
                except:
                    print("fail")
    else:
        team = sys.argv[1]
        n_hits = sys.argv[3]
        for i in range(int(n_hits)):
            try:
                single_page_fetcher(team, update_pages)
            except:
                print("fail")
