import pandas as pd
import numpy as np
import pdb
import requests
import time
import random
import os
import glob

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from tqdm import tqdm_notebook, tqdm
from joblib import Parallel, delayed

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


page_prefix = "https://globoesporte.globo.com/futebol/times/{}/index/feed/pagina-{}.ghtml"
options = Options()
options.add_argument("--headless")
driver = webdriver.Firefox(options=options, executable_path="/usr/local/bin/geckodriver")
driver.implicitly_wait(5)

news_links = ["http://globoesporte.globo.com/sp/santos-e-regiao/futebol/noticia/2016/10/de-olho-em-2017-santos-se-interessa-por-marcelo-cirino-do-flamengo.html"]

results = []
for i, news_link in enumerate(news_links):
    news_data = extract_text_from_news_link(news_link, driver)
    results.append(news_data)
