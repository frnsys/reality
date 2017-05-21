"""
FeedFinder
==============

Tries to find feeds for a given URL.

This is essentially a rewrite of feedfinder.py,
originally by Mark Pilgrim and Aaron Swartz.

Credits from the original:
Abe Fettig for a patch to sort Syndic8 feeds by popularity
Also Jason Diamond, Brian Lalor for bug reporting and patches

Original is located at:
    http://www.aaronsw.com/2002/feedfinder/

How it works:
    0. At every step, feeds are minimally verified to make sure they are really feeds.
    1. If the URI points to a feed, it is simply returned; otherwise
       the page is downloaded and the real fun begins.
    2. Feeds pointed to by LINK tags in the header of the page (autodiscovery)
    3. <A> links to feeds on the same server ending in ".rss", ".rdf", ".xml", or
       ".atom"
    4. <A> links to feeds on the same server containing "rss", "rdf", "xml", or "atom"
    5. Try some guesses about common places for feeds (index.xml, atom.xml, etc.).
    6. <A> links to feeds on external servers ending in ".rss", ".rdf", ".xml", or
       ".atom"
    7. <A> links to feeds on external servers containing "rss", "rdf", "xml", or "atom"

Copyright:
    2002-2004: Mark Pilgrim
    2006: Aaron Swartz
    2013: Francis Tseng
"""

# python 2.7 support
try:
    from urllib import parse
except ImportError:
    import urlparse as parse

import requests
import lxml.html


def feeds(url):
    """try to find feeds for a given url"""
    url = _full_url(url)
    data = _get(url)

    # check if the url is a feed
    if _is_feed(url):
        return [url]

    # try to get feed links from markup
    try:
        feed_links = [link for link in _get_feed_links(data, url) if _is_feed(link)]
    except:
        feed_links = []
    if feed_links:
        return feed_links

    # try 'a' links
    try:
        links = _get_a_links(data)
    except:
        links = []

    if links:
        # filter to only local links
        local_links = [link for link in links if link.startswith(url)]

        # try to find feed links
        feed_links.extend(_filter_feed_links(local_links))

        # if still nothing has been found...
        if not feed_links:
            # try to find feed-looking links
            feed_links.extend(_filter_feedish_links(local_links))

    # if still nothing has been found...
    if not feed_links:
        # BRUTE FORCE IT!
        guesses = [
                'atom.xml',     # Blogger, TypePad
                'index.atom',   # MoveableType
                'index.rdf',    # MoveableType
                'rss.xml',      # Dave Winer/Manila
                'index.xml',    # MoveableType
                'index.rss',    # Slash
                'feed'          # WordPress
        ]
        tries = [parse.urljoin(url, g) for g in guesses]
        feed_links.extend([link for link in tries if _is_feed(link)])

    # if *still* nothing has been found,
    # just try all the links
    if links and not feed_links:
        feed_links.extend(_filter_feed_links(links))
        feed_links.extend(_filter_feedish_links(links))

    # filter out duplicates
    return list(set(feed_links))


def feed(url):
    feed_links = feeds(url)
    if feed_links:
        return feed_links[0]
    else:
        return None


def _full_url(url):
    """assemble the full url for a url"""
    url = url.strip()
    for proto in ['http', 'https']:
        if url.startswith('%s://' % proto):
            return url
    return 'http://%s' % url


def _get_feed_links(data, url):
    """try to get feed links defined in the markup"""
    FEED_TYPES = ('application/rss+xml',
                  'text/xml',
                  'application/atom+xml',
                  'application/x.atom+xml',
                  'application/x-atom+xml')
    links = []
    html = lxml.html.fromstring(data)

    # for each link...
    for link in html.xpath('//link'):

        # try to get the 'rel' attribute
        rel = link.attrib.get('rel', False)
        href = link.attrib.get('href', False)
        type = link.attrib.get('type', False)

        # check some things
        if not rel or not href or not type: continue
        if 'alternate' not in rel.split(): continue
        if type not in FEED_TYPES: continue

        links.append(parse.urljoin(url, href))
    return links


def _get_a_links(data):
    """gathers all 'a' links from the markup"""
    html = lxml.html.fromstring(data)
    return html.xpath('//a/@href')


def _is_feed(url):
    """test if a given URL is a feed"""
    # if it's not http or https,
    # it's not a feed
    scheme = parse.urlparse(url).scheme
    if scheme not in ('http', 'https'):
        return 0

    data = _get(url)

    # if an html tag is present,
    # assume it's not a feed
    if data.count('<html'):
        return 0

    return data.count('<rss') + data.count('<rdf') + data.count('<feed')


def _is_feed_link(url):
    """check if a link is a feed link"""
    return url[-4:] in ('.rss', '.rdf', '.xml', '.atom')


def _filter_feed_links(links):
    """filters a list of links for only feed links"""
    candidates = [link for link in links if _is_feed_link(link)]
    return [link for link in candidates if _is_feed(link)]


def _filter_feedish_links(links):
    """filters a list of links for links
    that _look_ like they may be feed links"""
    feed_links = []
    for link in links:
        if link.count('rss') + link.count('rdf') + link.count('xml') + link.count('atom'):
            if _is_feed(link):
                feed_links.append(link)
    return feed_links


def _get(url):
    """try to access the url and return its data"""
    return requests.get(url).content.decode('utf8')


if __name__ == '__main__':
    import sys
    for url in feeds(sys.argv[1]):
        print(url)