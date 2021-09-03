# -*- coding: utf-8 -*-
# -*- Channel altadefinizione01_link -*-

from core import support
from core.item import Item
from platformcode import config, logger

__channel__ = "altadefinizione01_link"

# ======== def per utility INIZIO ============================
host = config.get_channel_url()
headers = [['Referer', host]]


# =========== home menu ===================
@support.menu
def mainlist(item):
    support.info('mainlist',item)

    film = [
        ('Al Cinema', ['/film-del-cinema', 'peliculas', '']),
        ('Generi', ['', 'genres', 'genres']),
        ('Anni', ['', 'genres', 'years']),
        ('Qualità', ['/piu-visti.html', 'genres', 'quality']),
        ('Mi sento fortunato', ['/piu-visti.html', 'genres', 'lucky']),
        ('Popolari', ['/piu-visti.html', 'peliculas', '']),
        ('Sub-ITA', ['/film-sub-ita/', 'peliculas', ''])
    ]
    return locals()

# ======== def in ordine di action dal menu ===========================

@support.scrape
def peliculas(item):
    patron = r'<a href="(?P<url>[^"]+)">(?P<title>[^<]+)(?:[^>]+>){5}\s*<div class="[^"]+" style="background-image:url\((?P<thumb>[^\)]+)(?:[^>]+>){6}\s*(?P<year>\d{4})[^>]+>[^>]+>(?:\s*(?P<duration>\d+))?(?:[^>]+>){0,2}\s+(?P<quality>[a-zA-Z]+)\s+(?:[^>]+>){2}\s*(?P<lang>[^>]+)\s+[^>]+>'
    patronNext = r'<span>\d</span> <a href="([^"]+)">'
    return locals()

# =========== def pagina categorie ======================================
@support.scrape
def genres(item):
    support.info('genres',item)

    action = 'peliculas'
    if item.args == 'genres':
        patronBlock = r'<ul class="listSubCat" id="Film">(?P<block>.*)<ul class="listSubCat" id="Anno">'
    elif item.args == 'years':
        patronBlock = r'<ul class="listSubCat" id="Anno">(?P<block>.*)<ul class="listSubCat" id="Qualita">'
    elif item.args == 'quality':
        patronBlock = r'<ul class="listSubCat" id="Qualita">(?P<block>.*)<blockquote'
    elif item.args == 'lucky': # sono i titoli random nella pagina
        patronBlock = r'FILM RANDOM.*?class="listSubCat">(?P<block>.*)</ul>'
        action = 'findvideos'
    patronMenu = r'<li><a href="(?P<url>[^"]+)">(?P<title>[^<]+)<'
    return locals()

# =========== def per cercare film/serietv =============
#host+/index.php?do=search&story=avatar&subaction=search
def search(item, text):
    support.info('search', item)
    itemlist = []
    text = text.replace(" ", "+")
    item.url = host+"/index.php?do=search&story=%s&subaction=search" % (text)
    try:
        return peliculas(item)
    # Se captura la excepcion, para no interrumpir al buscador global si un canal falla
    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []

# =========== def per le novità nel menu principale =============

def newest(categoria):
    support.info('newest', categoria)
    itemlist = []
    item = Item()
    try:
        if categoria == "peliculas":
            item.url = host
            item.action = "peliculas"
            item.contentType='movie'
            itemlist = peliculas(item)

            if itemlist[-1].action == "peliculas":
                itemlist.pop()
    # Continua la ricerca in caso di errore
    except:
        import sys
        for line in sys.exc_info():
            logger.error("{0}".format(line))
        return []

    return itemlist

def findvideos(item):
    support.info('findvideos', item)
    return support.server(item, support.match(item, patron='<ul class="playernav">.*?</ul>', headers=headers).match)
