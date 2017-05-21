import os
import json
import logging
import fasteners
from time import sleep
from raven import Client
from reality import collect, hash


def broadcast(article):
    """add an article's data to each listener's FIFO queue"""
    try:
        listeners = [l.strip() for l in open('listeners.txt', 'r').readlines()]
    except FileNotFoundError:
        listeners = []
    for path in listeners:
        with fasteners.InterProcessLock('/tmp/{}.lock'.format(hash(path))):
            with open(path, 'a') as f:
                f.write(json.dumps(article)+'\n')


if __name__ == '__main__':
    INTERVAL = 60 * 60
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    try:
        dsn = open(os.path.expanduser('~/.sentry_dsn'), 'r').read().strip()
        client = Client(dsn)
    except FileNotFoundError:
        client = None
    while True:
        try:
            feeds = [l.strip() for l in open('feeds.txt', 'r')]
            collect(feeds, on_article=broadcast)
            sleep(INTERVAL)
        except (KeyboardInterrupt, SystemExit):
            break
        except Exception as e:
            logger.exception(e)
            if client is not None:
                client.captureException()
            else:
                raise