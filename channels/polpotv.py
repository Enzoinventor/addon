# -*- coding: utf-8 -*-
# ------------------------------------------------------------
# KoD - XBMC Plugin
# Canale polpotv
# ------------------------------------------------------------

from core import support, jsontools
from core.item import Item
from platformcode import config, logger
import datetime

host = config.get_channel_url()

headers = [['Accept', 'application/ld+json']]


@support.menu
def mainlist(item):
    # menu = [
    #     ('Ultimi Film aggiunti', ['/api/movies', 'movies', '']),
    #     ('Ultime Serie TV aggiunte', ['/api/shows', 'movies', '']),
    #     ('Generi', ['/api/genres', 'search_movie_by_genre', '']),
    #     ('Anni {film}', ['', 'search_movie_by_year', '']),
    #     ('Cerca... bold', ['', 'search', ''])
    # ]
    film = ['/api/movies',
            ('Generi', ['/api/genres', 'search_movie_by_genre', '']),
            ('Anni', ['', 'search_movie_by_year', '']),]

    tvshow=['/api/shows']

    search=''

    return locals()

def newest(category):
    logger.debug()
    item = Item()
    if category == 'movie':
        item.contentType = 'movie'
        item.url = host + '/api/movies'
    elif category == 'tvshow':
        item.contentType = 'tvshow'
        item.url = host+'/api/shows'
    return movies(item)

def movies(item):
    logger.debug()
    itemlist = []

    data = support.match(item.url, headers=headers).data
    json_object = jsontools.load(data)
    for element in json_object['hydra:member']:
        if 'shows' not in item.url:
            item.contentType='movie'
        else:
            item.contentType='tvshow'
        itemlist.append(get_itemlist_element(element, item))

    support.tmdb.set_infoLabels_itemlist(itemlist, seekTmdb=True)
    try:
        if support.inspect.stack()[1][3] not in ['newest']:
            support.nextPage(itemlist, item, next_page=json_object['hydra:view']['hydra:next'])
    except:
        pass

    return itemlist

def episodes(item):
    logger.debug()
    itemlist = []
    data = support.match(item.url, headers=headers).data
    json_object = jsontools.load(data)
    for season in json_object['seasons']:
        seas_url=host+season['@id']+'/releases'
        itemlist_season=get_season(item, seas_url, season['seasonNumber'])
        if(len(itemlist_season)>0):
            itemlist.extend(itemlist_season)

    support.videolibrary(itemlist, item, 'color kod bold')
    support.download(itemlist, item)

    return itemlist

def get_season(item, seas_url, seasonNumber):
    logger.debug()
    itemlist = []
    data = support.match(seas_url, headers=headers).data
    json_object = jsontools.load(data)
    for episode in json_object['hydra:member']:
        itemlist.append(
            item.clone(action='findvideos',
                       contentType='episode',
                       title=support.typo(str(seasonNumber)+"x"+str("%02d"%episode['episodeNumber']), 'bold'),
                       url=seas_url,
                       extra=str(len(json_object['hydra:member'])-episode['episodeNumber'])))
    return itemlist[::-1]

def search(item, texto):
    logger.debug(item.url, "search", texto)
    itemlist=[]
    try:
        item.url = host + "/api/movies?originalTitle="+texto+"&translations.name=" +texto
        data = support.match(item.url, headers=headers).data
        json_object = jsontools.load(data)
        for movie in json_object['hydra:member']:
            item.contentType='movie'
            itemlist.append(get_itemlist_element(movie,item))
        item.url = host + "/api/shows?originalTitle="+texto+"&translations.name=" +texto
        data = support.match(item.url, headers=headers).data
        json_object = jsontools.load(data)
        for tvshow in json_object['hydra:member']:
            item.contentType='tvshow'
            itemlist.append(get_itemlist_element(tvshow,item))
        support.tmdb.set_infoLabels_itemlist(itemlist, seekTmdb=True)
        return itemlist
    # Continua la ricerca in caso di errore
    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []


def search_movie_by_genre(item):
    logger.debug()
    itemlist = []
    data = support.match(item.url, headers=headers).data
    json_object = jsontools.load(data)
    for genre in json_object['hydra:member']:
        itemlist.append(
            item.clone(action="movies",
                       title=support.typo(genre['name'],'bold'),
                       contentType='movie',
                       url="%s/api/movies?genres.id=%s" %(host,genre['id'])))
    return support.thumb(itemlist, True)


def search_movie_by_year(item):
    logger.debug()
    now = datetime.datetime.now()
    year = int(now.year)
    itemlist = []
    for i in range(100):
        year_to_search = year - i
        itemlist.append(
            item.clone(channel=item.channel,url="%s/api/movies?releaseDate=%s" %(host,year_to_search),
                       plot="1",
                       type="movie",
                       title=support.typo(year_to_search,'bold'),
                       action="movies"))
    return itemlist


def findvideos(item):
    logger.debug()
    itemlist = []
    try:
        data = support.match(item.url, headers=headers).data
        json_object = jsontools.load(data)
        array_index=0
        if item.contentType!='movie':
            array_index=int(item.extra)
        for video in json_object['hydra:member'][array_index]['playlist']['videos']:
            itemlist.append(
                item.clone(action="play",
                           title='Direct',
                           url=video['src'],
                           server='directo',
                           quality=str(video['size'])+ 'p',
                           folder=False))
    except:
        pass
    return support.server(item, itemlist=itemlist)


def get_itemlist_element(element,item):
    logger.debug()
    contentSerieName = ''
    contentTitle =''
    try:
        if element['originalLanguage']['id']=='it':
            scrapedtitle=element['originalTitle']
        else:
            scrapedtitle=element['translations'][1]['name']
        if scrapedtitle=='':
            scrapedtitle=element['originalTitle']
    except:
        scrapedtitle=element['originalTitle']
    try:
        scrapedplot=element['translations'][1]['overview']
    except:
        scrapedplot = ""
    try:
        scrapedthumbnail="https:"+element['bestPosters'].values()[0]
    except:
        scrapedthumbnail=""
    # try:
    #     scrapedfanart="http:"+element['backdropPath']
    # except:
    #     scrapedfanart=""

    infoLabels = {}
    if item.contentType=='movie':
        contentTitle = scrapedtitle
        next_action='findvideos'
        quality=support.typo(element['lastQuality'].upper(), '_ [] color kod bold')
        url="%s%s/releases"
        infoLabels['tmdb_id']=element['tmdbId']
    else:
        contentSerieName = scrapedtitle
        next_action='episodes'
        quality=''
        url="%s%s"

    return item.clone(action=next_action,
                   title=support.typo(scrapedtitle, 'bold') + quality,
                   fulltitle=scrapedtitle,
                   show=scrapedtitle,
                   plot=scrapedplot,
                   # fanart=scrapedfanart,
                   thumbnail=scrapedthumbnail,
                   contentTitle=contentTitle,
                   contentSerieName=contentSerieName,
                   contentType=item.contentType,
                   url=url % (host, element['@id']),
                   infoLabels=infoLabels)
