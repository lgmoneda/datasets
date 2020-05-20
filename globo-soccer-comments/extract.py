import pandas as pd
import numpy as np
import pdb
import requests

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from tqdm import tqdm_notebook, tqdm
from joblib import Parallel, delayed


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
    ### Clicando no botão de carregar mais comentários
    more_comments = True
    while more_comments:
        try:
            driver.find_element_by_class_name("glbComentarios-botao-mais").click()
        except:
            more_comments = False

    return driver.page_source

def get_comments_html(soup):

    iframes = soup.find_all("iframe")
    iframe_srcs = [i.get("src", "") for i in iframes]
    comments_src = [src for src in iframe_srcs if "ge.comentarios" in src][0]
    driver.get(comments_src)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    return driver.page_source

def extract_comments_from_news_link(news_link, driver):
    html = get_full_html_from_news(news_link, driver)
    soup = BeautifulSoup(html)

    try:
        date = soup.find_all("time")[0].text
    except:
        date = None

    try:
        title = soup.find_all("h1", {"class": "content-head__title"})[0].text
    except:
        title = None

    comments = soup.find_all("p",
                            {"class": "glbComentarios-texto-comentario"})

    comments = [from_soup_comment_to_dict(comment) for comment in comments]

    if "ge.comentarios" in html:
        html = get_comments_html(soup)
        soup = BeautifulSoup(html)
        comments = soup.find_all("div", {"class": "coral-comment-content"})
        comments = [from_soup_comment_to_dict(comment) for comment in comments]

    if len(comments) > 0:
        comments = pd.DataFrame(comments)
        comments["date"] = date
        comments["title"] = title
        return comments

    return pd.DataFrame()


def from_soup_comment_to_dict(soup_comment):
    new_comment = {}
    new_comment["text"] = soup_comment.text

    return new_comment

def comments_from_soccer_club(team, n_pages=2):
    page_prefix = "https://globoesporte.globo.com/futebol/times/{}/index/feed/pagina-{}.ghtml"
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Firefox(options=options, executable_path="/usr/local/bin/geckodriver")
    driver.implicitly_wait(30)

    news_links = []
    for n_page in tqdm(range(1, n_pages + 1)):
        page = page_prefix.format(team, n_page)
        new_news_links = extract_news_from_page(page)
        news_links += new_news_links

    news_links = [link for link in news_links if "/noticia/" in link]
    data = pd.DataFrame()
    for news_link in tqdm(news_links):
        news_comments_data = extract_comments_from_news_link(news_link, driver)
        print(len(news_comments_data))
        data = pd.concat([data, news_comments_data], sort=True)

    data["time"] = data["date"].apply(lambda x: x.strip().split(" ")[1] if not pd.isnull(x) else x)
    data["date"] = data["date"].apply(lambda x: x.strip().split(" ")[0] if not pd.isnull(x) else x)

    driver.close()
    return data

def comments_from_soccer_club_single_page(team, page_number):
    page_prefix = "https://globoesporte.globo.com/futebol/times/{}/index/feed/pagina-{}.ghtml"
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Firefox(options=options, executable_path="/usr/local/bin/geckodriver")
    driver.implicitly_wait(5)

    page = page_prefix.format(team, page_number)
    news_links = extract_news_from_page(page)

    data = pd.DataFrame()
    for news_link in tqdm(news_links):
        news_comments_data = extract_comments_from_news_link(news_link, driver)
        data = pd.concat([data, news_comments_data], sort=True)

    # data["time"] = data["date"].apply(lambda x: x.strip().split(" ")[1])
    # data["date"] = data["date"].apply(lambda x: x.strip().split(" ")[0])

    driver.close()
    return data

def multiproc_teams_data(team, n_pages=2):
    parts = 16
    partioned = np.array_split(range(n_pages), parts)
    results = Parallel(n_jobs= -1)(delayed(comments_from_soccer_club_single_page)(team, page_number=part) for part in partioned)
    result = pd.concat(results)

    return result

comments = comments_from_soccer_club("flamengo", n_pages=10)

#comments = multiproc_teams_data("flamengo", n_pages=5)

comments.to_csv("flamengo.csv")
