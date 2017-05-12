import os
import logging
from time import sleep
from raven import Client
from reality import collect

if __name__ == '__main__':
    INTERVAL = 60 * 60
    logging.basicConfig(level=logging.INFO)
    while True:
        try:
            feeds = [l.strip() for l in open('feeds.txt', 'r')]
            collect(feeds)
            sleep(INTERVAL)
        except (KeyboardInterrupt, SystemExit):
            break
        except:
            dsn = os.environ.get('SENTRY_DSN', None)
            if dsn is not None:
                client = Client(dsn)
                client.captureException()
            else:
                raise