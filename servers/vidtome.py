# -*- coding: utf-8 -*-

from core import httptools, scrapertools
from platformcode import logger, config
from lib import jsunpack


def test_video_exists(page_url):
    logger.info("(page_url='%s')" % page_url)
    global data
    data = httptools.downloadpage(page_url).data
    if "Not Found" in data or "File Does not Exist" in data:
        return False, config.get_localized_string(70292) % 'Vidto.me'
    return True, ""


def get_video_url(page_url, premium=False, user="", password="", video_password=""):
    logger.info("url=" + page_url)
    global data
    video_urls = []
    code = scrapertools.find_single_match(data, 'name="code" value="([^"]+)')
    hash = scrapertools.find_single_match(data, 'name="hash" value="([^"]+)')
    post = "op=download1&code=%s&hash=%s&imhuman=Proceed+to+video" %(code, hash)
    data = httptools.downloadpage("http://vidtome.co/playvideos/%s" %code, post=post).data
    packed = scrapertools.find_multiple_matches(data, r'(eval\s?\(function\(p,a,c,k,e,d\).*?\n)')
    for p in packed:
        data = jsunpack.unpack(p)
        media_url = scrapertools.find_single_match(data, r"source:\\'([^\\']+)")
        if media_url:
            video_urls.append([media_url.split('.')[-1] + ' [Vidto.me]', media_url])
    return video_urls
