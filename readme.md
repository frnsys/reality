- add feeds to `feeds.txt`
- run `main.py`
    - this will update the feeds every hour

to retrieve articles for a feed:

```python
from reality import get_articles
feed = 'http://feeds.theguardian.com/theguardian/us/rss'
articles = get_articles(feed)
```

you can add "listeners" (which are really just FIFO queues) that have article data appended to them when new articles are retrieved. see `listeners.txt` for an example.

an example listener script:

```python
import hashlib
import fasteners

fifo = '/tmp/fifo'
while True:
    hash = hashlib.md5(fifo.encode('utf8')).hexdigest()
    with fasteners.InterProcessLock('/tmp/{}.lock'.format(hash)):
        try:
            with open(fifo, 'r+') as f:
                for l in f:
                    article = json.loads(l.strip())
                    on_article(article)
            open(fifo, 'w').close()
        except FileNotFoundError:
            print('no fifo')
        sleep(10)
    except (KeyboardInterrupt, SystemExit):
        break
```