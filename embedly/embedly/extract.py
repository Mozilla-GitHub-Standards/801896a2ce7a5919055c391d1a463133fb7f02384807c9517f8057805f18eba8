import json
import urllib
import urlparse

import requests


class URLExtractor(object):

    def __init__(self, embedly_url, embedly_key, redis_client, redis_timeout):
        self.embedly_url = embedly_url
        self.embedly_key = embedly_key
        self.redis_client = redis_client
        self.redis_timeout = redis_timeout

    def _get_cache_key(self, url):
        split_url = urlparse.urlsplit(url)
        return '{base}{path}'.format(
            base=split_url.netloc, path=split_url.path)

    def _get_cached_url(self, url):
        cache_key = self._get_cache_key(url)
        cached_data = self.redis_client.get(cache_key)

        if cached_data is not None:
            return json.loads(cached_data)

    def _set_cached_url(self, url, data):
        cache_key = self._get_cache_key(url)
        self.redis_client.set(cache_key, json.dumps(data))
        self.redis_client.expire(cache_key, self.redis_timeout)

    def _build_embedly_url(self, urls):
        params = '&'.join([
            'key={}'.format(self.embedly_key),
            'urls={}'.format(','.join([
                urllib.quote_plus(url) for url in urls
            ])),
        ])

        return '{base}?{params}'.format(
            base=self.embedly_url,
            params=params,
        )

    def _get_urls_from_embedly(self, urls):
        request_url = self._build_embedly_url(urls)

        try:
            response = requests.get(request_url)
        except requests.RequestException:
            response = None

        embedly_data = []

        if response is not None:
            try:
                embedly_data = json.loads(response.content)
            except (TypeError, ValueError):
                pass

        parsed_data = {}

        if type(embedly_data) is list:
            parsed_data = {
                url_data['original_url']: url_data
                for url_data in embedly_data
            }

        return parsed_data

    def extract_urls(self, urls):
        url_data = {}

        uncached_urls = []
        for url in urls:
            cached_url_data = self._get_cached_url(url)

            if cached_url_data is not None:
                url_data[url] = cached_url_data
            else:
                uncached_urls.append(url)

        if uncached_urls:
            embedly_url_data = self._get_urls_from_embedly(uncached_urls)

            for embedly_url, embedly_data in embedly_url_data.items():
                self._set_cached_url(embedly_url, embedly_data)

            url_data.update(embedly_url_data)

        return url_data
