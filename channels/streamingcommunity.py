# -*- coding: utf-8 -*-
# ------------------------------------------------------------
# Canale per StreamingCommunity
# ------------------------------------------------------------
import functools
import json, requests, re, sys
from core import support, channeltools, httptools, jsontools, filetools
from platformcode import logger, config, platformtools

if sys.version_info[0] >= 3:
    from concurrent import futures
else:
    from concurrent_py2 import futures

# def findhost(url):
#     return 'https://' + support.match(url, patron='var domain\s*=\s*"([^"]+)').match


host = support.config.get_channel_url()
session = requests.Session()
session.request = functools.partial(session.request, timeout=httptools.HTTPTOOLS_DEFAULT_DOWNLOAD_TIMEOUT)
headers = {}


def getHeaders(forced=False):
    global headers
    global host
    if not headers:
        # try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.8.1.14) Gecko/20080404 Firefox/2.0.0.14'}
        response = session.get(host, headers=headers)
        # if not response.url.startswith(host):
        #     host = support.config.get_channel_url(findhost, forceFindhost=True)
        csrf_token = support.match(response.text, patron='name="csrf-token" content="([^"]+)"').match
        headers = {'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.8.1.14) Gecko/20080404 Firefox/2.0.0.14',
                    'content-type': 'application/json;charset=UTF-8',
                    'Referer': host,
                    'x-csrf-token': csrf_token,
                    'Cookie': '; '.join([x.name + '=' + x.value for x in response.cookies])}
        # except:
        #     host = support.config.get_channel_url(findhost, forceFindhost=True)
        #     if not forced: getHeaders(True)

getHeaders()

@support.menu
def mainlist(item):
    film=['',
          ('Generi',['/film','genres']),
          ('Titoli del Momento',['/film','peliculas',0]),
          ('Novità',['/film','peliculas',1]),
          ('Popolari',['/film','peliculas',2])]
    tvshow=['',
            ('Generi',['/serie-tv','genres']),
            ('Titoli del Momento',['/serie-tv','peliculas',0]),
            ('Novità',['/serie-tv','peliculas',1]),
            ('Popolari',['/serie-tv','peliculas',2])]
    search=''
    return locals()


def genres(item):
    # getHeaders()
    logger.debug()
    itemlist = []
    data = support.scrapertools.decodeHtmlentities(support.match(item).data)
    args = support.match(data, patronBlock=r'genre-options-json="([^\]]+)\]', patron=r'name"\s*:\s*"([^"]+)').matches
    for arg in args:
        itemlist.append(item.clone(title=support.typo(arg, 'bold'), args=arg, action='peliculas'))
    support.thumb(itemlist, genre=True)
    return itemlist


def search(item, text):
    logger.debug('search', text)
    item.search = text

    try:
        return peliculas(item)
    # Continua la ricerca in caso di errore
    except:
        import sys
        for line in sys.exc_info():
            logger.error(line)
        return []


def newest(category):
    logger.debug(category)
    itemlist = []
    item = support.Item()
    item.args = 1
    item.newest = True
    if category == 'peliculas':
        item.url = host + '/film'
    else:
        item.url = host + '/serie-tv'

    try:
        itemlist = peliculas(item)

        if itemlist[-1].action == 'peliculas':
            itemlist.pop()
    # Continua la ricerca in caso di errore
    except:
        import sys
        for line in sys.exc_info():
            logger.error(line)
        return []

    return itemlist



def peliculas(item):
    logger.debug()
    if item.mainThumb: item.thumbnail = item.mainThumb
    global host
    itemlist = []
    items = []
    recordlist = []
    videoType = 'movie' if item.contentType == 'movie' else 'tv'

    page = item.page if item.page else 0
    offset = page * 60

    if item.records:
        records = item.records
    elif type(item.args) == int:
        data = support.scrapertools.decodeHtmlentities(support.match(item).data)
        records = json.loads(support.match(data, patron=r'slider-title titles-json="(.*?)"\s*slider-name="').matches[item.args])
    elif not item.search:
        payload = json.dumps({'type': videoType, 'offset':offset, 'genre':item.args})
        records = session.post(host + '/api/browse', headers=headers, data=payload).json()['records']
    else:
        payload = json.dumps({'q': item.search})
        records = session.post(host + '/api/search', headers=headers, data=payload).json()['records']


    if records and type(records[0]) == list:
        js = []
        for record in records:
            js += record
    else:
        js = records

    for i, it in enumerate(js):
        if i < 20:
            items.append(it)
        else:
            recordlist.append(it)

    with futures.ThreadPoolExecutor() as executor:
        itlist = [executor.submit(makeItem, i, it, item) for i, it in enumerate(items)]
        for res in futures.as_completed(itlist):
            if res.result():
                itemlist.append(res.result())

    itemlist.sort(key=lambda item: item.n)
    if not item.newest:
        item.mainThumb = item.thumbnail
        if recordlist:
            itemlist.append(item.clone(title=support.typo(support.config.get_localized_string(30992), 'color kod bold'), thumbnail=support.thumb(), page=page, records=recordlist))
        elif len(itemlist) >= 20:
            itemlist.append(item.clone(title=support.typo(support.config.get_localized_string(30992), 'color kod bold'), thumbnail=support.thumb(), records=[], page=page + 1))

    support.tmdb.set_infoLabels_itemlist(itemlist, seekTmdb=True)
    support.check_trakt(itemlist)
    return itemlist

def makeItem(n, it, item):
    info = session.post(host + '/api/titles/preview/{}'.format(it['id']), headers=headers).json()
    logger.debug(jsontools.dump(it))
    title = info['name']
    lang = 'Sub-ITA' if 'sub-ita' in title.lower() else 'ITA'
    title = support.cleantitle(re.sub('\[|\]|[Ss][Uu][Bb]-[Ii][Tt][Aa]', '', title))
    itm = item.clone(title=support.typo(title,'bold') + support.typo(lang,'_ [] color kod bold'))
    itm.contentType = info['type'].replace('tv', 'tvshow')
    itm.language = lang
    itm.year = info['release_date'].split('-')[0]


    if itm.contentType == 'movie':
        # itm.contentType = 'movie'
        itm.fulltitle = itm.show = itm.contentTitle = title
        itm.action = 'findvideos'
        itm.url = host + '/watch/%s' % it['id']

    else:
        # itm.contentType = 'tvshow'
        itm.contentTitle = ''
        itm.fulltitle = itm.show = itm.contentSerieName = title
        itm.action = 'episodios'
        itm.season_count = info['seasons_count']
        itm.url = host + '/titles/%s-%s' % (it['id'], it['slug'])
    itm.n = n
    return itm

def episodios(item):
    # getHeaders()
    logger.debug()
    itemlist = []

    js = json.loads(support.match(item.url, patron=r'seasons="([^"]+)').match.replace('&quot;','"'))

    for episodes in js:
        # logger.debug(jsontools.dump(js))
        for it in episodes['episodes']:

            itemlist.append(
                item.clone(title=support.typo(str(episodes['number']) + 'x' + str(it['number']).zfill(2) + ' - ' + support.cleantitle(it['name']), 'bold'),
                           episode=it['number'],
                           season=episodes['number'],
                           contentSeason=episodes['number'],
                           contentEpisodeNumber=it['number'],
                           thumbnail=it['images'][0]['original_url'] if 'images' in it and 'original_url' in it['images'][0] else item.thumbnail,
                           contentThumbnail=item.thumbnail,
                           fanart=item.fanart,
                           contentFanart=item.fanart,
                           plot=it['plot'],
                           action='findvideos',
                           contentType='episode',
                           contentSerieName=item.fulltitle,
                           url=host + '/watch/' + str(episodes['title_id']),
                           episodeid= '?e=' + str(it['id'])))

    if config.get_setting('episode_info') and not support.stackCheck(['add_tvshow', 'get_newest']):
        support.tmdb.set_infoLabels_itemlist(itemlist, seekTmdb=True)
    support.check_trakt(itemlist)
    support.videolibrary(itemlist, item)
    support.download(itemlist, item)
    return itemlist


def findvideos(item):
    itemlist = [item.clone(title = channeltools.get_channel_parameters(item.channel)['title'], server='directo')]
    return support.server(item, itemlist=itemlist)

def play(item):
    from time import time
    from base64 import b64encode
    from hashlib import md5

    data = support.httptools.downloadpage(item.url + item.episodeid, headers=headers).data.replace('&quot;','"').replace('\\','')
    scws_id = support.match(data, patron=r'scws_id"\s*:\s*(\d+)').match
    # support.dbg()

    if not scws_id:
        if '<strong>Prossimamente' in data:
            platformtools.dialog_ok('StreamingCommunity', 'Il sito notifica che il contenuto sarà disponibile prossimamente')
            platformtools.play_canceled = True
        return []

    # Calculate Token
    client_ip = httptools.downloadpage('https://api.ipify.org/').data
    expires = int(time() + 172800)
    token = b64encode(md5('{}{} Yc8U6r8KjAKAepEA'.format(expires, client_ip).encode('utf-8')).digest()).decode('utf-8').replace('=', '').replace('+', '-').replace('/', '_')

    url = 'https://scws.xyz/master/{}?token={}&expires={}&n=1'.format(scws_id, token, expires)
    subs = []
    urls = []

    info = support.match(url, patron=r'LANGUAGE="([^"]+)",\s*URI="([^"]+)|RESOLUTION=\d+x(\d+).*?(http[^"\s]+)').matches
    if info:
        for lang, sub, res, url in info:
            if sub:
                if lang == 'auto': lang = 'ita-forced'
                s = config.get_temp_file(lang +'.srt')
                subs.append(s)
                filetools.write(s, support.vttToSrt(httptools.downloadpage(support.match(sub, patron=r'(http[^\s\n]+)').match).data))
            elif url:
                urls.append(['hls [{}]'.format(res), url])

        return [item.clone(title = channeltools.get_channel_parameters(item.channel)['title'], server='directo', video_urls=urls, subtitle=subs, manifest='hls')]
    else:
        return [item.clone(title = channeltools.get_channel_parameters(item.channel)['title'], server='directo', url=url, manifest='hls')]
