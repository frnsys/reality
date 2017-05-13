import os
import io
import json
import spacy
import hashlib
import logging
import requests
import newspaper
import tldextract
import feedparser
from glob import glob
from dateutil import parser
from datetime import datetime
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

KEEP = 500 # keep only this many url/title hashes for a domain
nlp = spacy.load('en')
logger = logging.getLogger(__name__)
HEADERS = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/53.0.2785.143 Chrome/53.0.2785.143 Safari/537.36'}


def request(url):
    s = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.1,
        status_forcelist=[500, 502, 503, 504])
    s.mount('http://', HTTPAdapter(max_retries=retries))
    s.mount('https://', HTTPAdapter(max_retries=retries))
    return s.get(url, headers=HEADERS)


def update(feed, check_exists):
    """fetches latest articles given a feed url,
    skipping those where `check_exists` returns `True`"""
    try:
        resp = request(feed)
    except requests.ReadTimeout:
        logger.error('Timeout while updating "{}"'.format(feed))
        return []
    data = feedparser.parse(io.BytesIO(resp.content))

    # if the `bozo` value is anything
    # but 0, there was an error parsing (or connecting) to the feed
    if data.bozo:
        # some errors are ok
        if not isinstance(data.bozo_exception, feedparser.CharacterEncodingOverride) \
                and not isinstance(data.bozo_exception, feedparser.NonXMLContentType):
            logger.error('Parsing error:')
            logger.error(resp.content)
            raise data.bozo_exception

    for entry in data.entries:
        url = entry['links'][0]['href']

        # check for an existing Article;
        # if one exists, skip
        if check_exists(url, entry['title']):
            continue

        a_data = fetch(url)
        if a_data is None:
            continue
        a_data['feed'] = url

        # although `newspaper` can extract published datetimes using metadata,
        # generally the published datetime included with the RSS entry will
        # be more precise (and sometimes `newspaper` does not successfully
        # extract a published datetime)
        # (see https://github.com/codelucas/newspaper/blob/41b930b467979577710b86ecb93c2a952e5c9a0d/newspaper/extractors.py#L166)
        if 'published' in entry:
            a_data['published'] = parser.parse(entry['published'])

        # skip empty or short articles (which may be 404 pages)
        if a_data is None:
            continue

        doc = nlp(a_data['text'])
        if len(doc) <= 150:
            continue

        # ref: <https://spacy.io/docs/usage/entity-recognition>
        a_data['entities'] = [(ent.text, ent.label_) for ent in doc.ents]
        a_data['published'] = a_data['published'].timestamp()

        yield a_data


def fetch(url):
    """fetch article data for a given url"""
    a = newspaper.Article(url, keep_article_html=True)
    a.download()

    # Was unable to download, skip
    if not a.is_downloaded:
        return

    a.parse()

    data = {
        'url': a.url,
        'title': a.title,
        'text': a.text,
        'html': a.article_html,
        'image': a.top_image,
        'published': a.publish_date,
        'authors': a.authors,
        'keywords': a.keywords + a.meta_keywords
    }

    return data


def hash(text):
    return hashlib.md5(text.encode('utf8')).hexdigest()


def get_domain(url):
    return tldextract.extract(url).registered_domain.lower()


def data_dir(feed):
    domain = get_domain(feed)
    dir = 'data/{}'.format(domain)
    return dir


def collect(feeds, on_article=lambda a: None):
    """updates articles for a list of feed urls"""
    logger.info('Collecting: {}'.format(datetime.now().isoformat()))
    for feed in feeds:
        logger.info('Updating: {}'.format(feed))
        dir = data_dir(feed)

        if not os.path.isdir(dir):
            os.mkdir(dir)

        try:
            seen = json.load(open('{}/.seen'.format(dir), 'r'))
        except FileNotFoundError:
            seen = []

        def check_exists(url, title):
            return hash(title) in seen or hash(url) in seen

        news = list(update(feed, check_exists))
        for a in news:
            seen.append(hash(a['url']))
            seen.append(hash(a['title']))
            if a['top_image']:
                download_image(a['top_image'], 'data/_images')
            on_article(a)
        if news:
            now = datetime.now().strftime('%Y%m%d')
            fname = '{}/{}_{}.json'.format(dir, hash(feed), now)
            try:
                prev = json.load(open(fname, 'r'))
            except FileNotFoundError:
                prev = []
            prev.extend(news)
            with open(fname, 'w') as f:
                json.dump(prev, f)

        with open('{}/.seen'.format(dir), 'w') as f:
            json.dump(seen[:KEEP*2], f)


def get_articles(feed):
    """retrieve saved articles for a feed"""
    dir = data_dir(feed)
    files = glob('{}/{}_*.json'.format(dir, hash(feed)))
    articles = []
    for f in files:
        articles.extend(json.load(open(f, 'r')))
    return articles


def download_image(url, dir):
    res = requests.get(url, stream=True, headers=HEADERS)
    fname = hash(url)
    path = os.path.join(dir, fname)
    if res.status_code == 200:
        with open(path, 'wb') as f:
            for chunk in res:
                f.write(chunk)
    else:
        print('failed to download:', url)
        # res.raise_for_status()

