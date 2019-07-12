from six.moves.urllib.parse import urlencode, urljoin
import requests
import json

class SilkyyClient(object):
    def __init__(self, api_base, app_key=None, app_secret=None):
        self.api_base = api_base
        self.app_key = app_key
        self.app_secret = app_secret

    def _request_json(self, path, method='GET', data=None):
        request_url = urljoin(self.api_base, path)
        headers = {'X-Silkyy-AppKey': self.app_key,
                   'X-Silkyy-AppSecret': self.app_secret}
        response = requests.request(method=method, url=request_url, data=data, headers=headers)
        response.raise_for_status()
        return json.loads(response.content)

    def spider(self, project_name, spider_name, auto_create=True):
        spider_url = 'api/v1/s/%(project)s/%(spider)s' % {"project": project_name, 'spider': spider_name}
        if auto_create:
            response = self._request_json(spider_url, method='PUT')
        else:
            response = self._request_json(spider_url, method='GET')
        project_name = response['project']
        spider_name = response['name']
        return Spider(self, project_name, spider_name)


class Spider(object):
    def __init__(self, client, project_name, spider_name):
        self.client = client
        self.name = spider_name
        self.project = project_name

    def run(self):
        url = 'api/v1/s/%(project)s/%(spider)s/run' % {"project": self.project, 'spider': self.name}
        run_id = self.client._request_json(url, method='POST')
        return SpiderRun(self, run_id)

    def settings(self, **kwargs):
        url = 'api/v1/s/%(project)s/%(spider)s/settings' % {"project": self.project, 'spider': self.name}
        if kwargs:
            data = json.dumps(kwargs)
            return self.client._request_json(url, method='PATCH', data=data)
        else:
            return self.client._request_json(url, method='GET')

class SpiderRun(object):
    def __init__(self, spider, run_id):
        self.spider = spider
        self.run_id = run_id

    def seen(self, item):
        url = 'api/v1/s/%(project)s/%(spider)s/run/%(run_id)s/seen' % {"project": self.spider.project,
                                                                           'spider': self.spider.name,
                                                                           'run_id': self.run_id}
        return self.spider.client._request_json(url, method='POST', data={'item': item})

    def complete(self):
        url = 'api/v1/s/%(project)s/%(spider)s/run/%(run_id)s/complete' % {"project": self.spider.project,
                                                                           'spider': self.spider.name,
                                                                           'run_id': self.run_id}
        return self.spider.client._request_json(url, method='POST')

