- add feeds to `feeds.txt`
- run `main.py`
    - this will update the feeds every hour

to retrieve articles for a feed:

```python
from reality import get_articles
feed = 'http://feeds.theguardian.com/theguardian/us/rss'
articles = get_articles(feed)
```