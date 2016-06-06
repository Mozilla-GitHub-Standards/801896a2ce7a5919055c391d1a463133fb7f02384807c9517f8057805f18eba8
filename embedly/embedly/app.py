import os

import redis
from celery import Celery
from flask import Flask
from flask.ext.cors import CORS
from raven.contrib.flask import Sentry

import api.views


def get_config():
    return {
        'MAXIMUM_POST_URLS': 25,
        'URL_BATCH_SIZE': 5,
        'JOB_TTL': 300,
        'EMBEDLY_URL': 'https://api.embedly.com/1/extract',
        'EMBEDLY_KEY': os.environ.get('EMBEDLY_KEY', None),
        'REDIS_DATA_TIMEOUT': 24 * 60 * 60,  # 24 hour timeout
        'REDIS_JOB_TIMEOUT': 60 * 60,  # 1 hour timeout
        'REDIS_URL': os.environ.get('REDIS_URL', None),
        'SENTRY_DSN': os.environ.get('SENTRY_DSN', ''),
        'SENTRY_PROCESSORS': ('raven.processors.RemovePostDataProcessor',),
        'BLOCKED_DOMAINS': ['embedly.com'],
    }


def get_redis_client():  # pragma: nocover
    config = get_config()

    return redis.StrictRedis(host=config['REDIS_URL'], port=6379, db=0)


def get_extractor(redis_client=None):
    from extract import URLExtractor

    config = get_config()

    return URLExtractor(
        config['EMBEDLY_URL'],
        config['EMBEDLY_KEY'],
        redis_client or get_redis_client(),
        config['REDIS_DATA_TIMEOUT'],
        config['REDIS_JOB_TIMEOUT'],
        config['BLOCKED_DOMAINS'],
        config['JOB_TTL'],
        config['URL_BATCH_SIZE'],
    )


def get_celery():
    config = get_config()

    redis_url = 'redis://{redis_url}:6379'.format(
        redis_url=config['REDIS_URL'])

    celery = Celery(
        'embedly',
        backend=redis_url,
        broker=redis_url,
    )

    return celery


def create_app(redis_client=None):
    config = get_config()

    app = Flask(__name__)
    CORS(app)

    # Maximum number of URLs to receive in an API call
    app.config.update(config)

    app.redis_client = redis_client or get_redis_client()

    app.extractor = get_extractor(app.redis_client)

    app.config['VERSION_INFO'] = ''
    if os.path.exists('./version.json'):  # pragma: no cover
        with open('./version.json') as version_file:
            app.config['VERSION_INFO'] = version_file.read()

    app.register_blueprint(api.views.blueprint)

    app.sentry = Sentry(app)

    return app
