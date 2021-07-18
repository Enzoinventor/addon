# -*- coding: utf-8 -*-
# ------------------------------------------------------------
# Canale per Altadefinizione Community
from core import support
from lib.fakeMail import Gmailnator
from platformcode import config, platformtools, logger
from core import scrapertools, httptools

host = config.get_channel_url()
register_url = 'https://altaregistrazione.com'
headers = [['Referer', host]]


@support.menu
def mainlist(item):
    support.info(item)

    # Ordine delle voci
    # Voce FILM, puoi solo impostare l'url
    film = ['/type/movie', # url per la voce FILM, se possibile la pagina principale con le ultime novità
        #Voce Menu,['url','action','args',contentType]
        ('Generi', ['', 'genres', 'genres']),
        ]

    # Voce SERIE, puoi solo impostare l'url
    tvshow = ['', # url per la voce Serie, se possibile la pagina con titoli di serie
        #Voce Menu,['url','action','args',contentType]
        ('Generi', ['', 'genres', 'genres']),
        ]

    altri = [
        # ('Per Lettera', ['/lista-film', 'genres', 'letters']),
        ('Qualità', ['', 'genres', 'quality']),
        # ('Anni', ['/anno', 'genres', 'years'])
    ]
    search = ''

    return locals()


def login():
    r = httptools.downloadpage(host)
    if 'id="logged"' in r.data:
        logger.info('Già loggato')
    else:
        logger.info('Login in corso')
        r = httptools.downloadpage(host + '/login', post={'email': config.get_setting('username', channel='altadefinizionecommunity'),
                                 'password': config.get_setting('password', channel='altadefinizionecommunity')})
        if not r.success or 'Email o Password non validi' in r.data:
            platformtools.dialog_ok('AltadefinizioneCommunity', 'Username/password non validi')
            return False

    return 'id="logged"' in r.data


def registerOrLogin():
    if config.get_setting('username', channel='altadefinizionecommunity') and config.get_setting('password', channel='altadefinizionecommunity'):
        if login():
            return True

    action = platformtools.dialog_yesno('AltadefinizioneCommunity',
                                  'Questo server necessita di un account, ne hai già uno oppure vuoi tentare una registrazione automatica?',
                                  yeslabel='Accedi', nolabel='Tenta registrazione', customlabel='Annulla')
    if action == 1:  # accedi
        from specials import setting
        from core.item import Item
        user_pre = config.get_setting('username', channel='altadefinizionecommunity')
        password_pre = config.get_setting('password', channel='altadefinizionecommunity')
        setting.server_config(Item(config='altadefinizionecommunity'))
        user_post = config.get_setting('username', channel='altadefinizionecommunity')
        password_post = config.get_setting('password', channel='altadefinizionecommunity')

        if user_pre != user_post or password_pre != password_post:
            return registerOrLogin()
        else:
            return []
    elif action == 0:  # tenta registrazione
        import random
        import string
        logger.debug('Registrazione automatica in corso')
        mailbox = Gmailnator()
        randPsw = ''.join(random.choice(string.ascii_letters + string.digits) for i in range(10))
        logger.debug('email: ' + mailbox.address)
        logger.debug('pass: ' + randPsw)
        reg = platformtools.dialog_register(register_url, email=True, password=True, email_default=mailbox.address, password_default=randPsw)
        if not reg:
            return False
        regPost = httptools.downloadpage(register_url, post={'email': reg['email'], 'password': reg['password']})

        if regPost.url == register_url:
            error = scrapertools.htmlclean(scrapertools.find_single_match(regPost.data, 'Impossibile proseguire.*?</div>'))
            error = scrapertools.unescape(scrapertools.re.sub('\n\s+', ' ', error))
            platformtools.dialog_ok('AltadefinizioneCommunity', error)
            return False
        if reg['email'] == mailbox.address:
            if "L'indirizzo email risulta già registrato" in regPost.data:
                # httptools.downloadpage(baseUrl + '/forgotPassword', post={'email': reg['email']})
                platformtools.dialog_ok('AltadefinizioneCommunity', 'Indirizzo mail già utilizzato')
                return False
            mail = mailbox.waitForMail()
            if mail:
                checkUrl = scrapertools.find_single_match(mail.body, '<a href="([^"]+)[^>]+>Verifica').replace(r'\/', '/')
                logger.debug('CheckURL: ' + checkUrl)
                httptools.downloadpage(checkUrl)
                config.set_setting('username', mailbox.address, channel='altadefinizionecommunity')
                config.set_setting('password', randPsw, channel='altadefinizionecommunity')
                platformtools.dialog_ok('AltadefinizioneCommunity',
                                        'Registrato automaticamente con queste credenziali:\nemail:' + mailbox.address + '\npass: ' + randPsw)
            else:
                platformtools.dialog_ok('AltadefinizioneCommunity', 'Impossibile registrarsi automaticamente')
                return False
        else:
            platformtools.dialog_ok('AltadefinizioneCommunity', 'Hai modificato la mail quindi KoD non sarà in grado di effettuare la verifica in autonomia, apri la casella ' + reg['email']
                                    + ' e clicca sul link. Premi ok quando fatto')
        logger.debug('Registrazione completata')
    else:
        return False

    return True


@support.scrape
def peliculas(item):
    support.info(item)

    patron = r'wrapFilm">\s*<a href="(?P<url>[^"]+)">\s*<span class="year">(?P<year>[0-9]{4})</span>\s*<span[^>]+>[^<]+</span>\s*<span class="qual">(?P<quality>[^<]+).*?<img src="(?P<thumbnail>[^"]+)[^>]+>\s*<h3>(?P<title>[^<]+)'
    patronNext = ''

    # debug = True
    return locals()


def search(item, texto):
    support.info("search ", texto)

    item.args = 'search'
    item.url = host + "/search?s=" + texto
    try:
        return peliculas(item)
    # Continua la ricerca in caso di errore
    except:
        import sys
        for line in sys.exc_info():
            support.logger.error("%s" % line)
        return []


@support.scrape
def genres(item):
    support.info(item)

    patronMenu = r'<a href="(?P<url>[^"]+)">(?P<title>[^<]+)'
    if item.args == 'quality':
        patronBlock = 'Risoluzione(?P<block>.*?)</ul>'
    else:
        patronBlock = ('Film' if item.contentType == 'movie' else 'Serie TV') + r'<span></span></a>\s+<ul class="dropdown-menu(?P<block>.*?)active-parent-menu'
    action = 'peliculas'

    # debug = True
    return locals()


@support.scrape
def episodios(item):
    support.info(item)
    data = item.data
    patron = r'class="playtvshow " data-href="(?P<url>[^"]+)'

    # debug = True
    def itemHook(it):
        spl = it.url.split('/')[-2:]
        it.contentSeason = int(spl[0])+1
        it.contentEpisodeNumber = int(spl[1])+1
        return it
    return locals()


def findvideos(item):
    itemlist = []
    video_url = item.url
    if not '/watch-unsubscribed' in video_url:
        playWindow = support.match(item.url, patron='playWindow" href="([^"]+)')
        video_url = playWindow.match
        if '/tvshow' in video_url:
            item.data = playWindow.data
            return episodios(item)
    itemlist.append(item.clone(action='play', url=support.match(video_url.replace('/watch-unsubscribed', '/watch-external'),
                                patron='src="([^"]+)').match, quality=''))
    itemlist.append(item.clone(action='play', server='directo', title=support.config.get_localized_string(30137),
                               url=video_url.replace('/watch-unsubscribed', '/watch')))
    return support.server(item, itemlist=itemlist)


def play(item):
    if host in item.url:  # intercetto il server proprietario
        if registerOrLogin():
            return support.get_jwplayer_mediaurl(httptools.downloadpage(item.url).data, 'Diretto')
        else:
            platformtools.play_canceled = True
            return []
    else:
        return [item]
