#from extract import extract_news_from_page, get_full_html_from_news, get_title, content_sportv, extract_text_from_news_link
from googlesearch import search

query = "globoesporte.globo.com/futebol/ /noticia/2016"
result = search(query, tld='com', lang='pt-br', num=10, start=0, stop=50, pause=2.0)

news_links = []
for r in result:
    if "/2016/" in r:
        news_links.append(r)

print(news_links)
