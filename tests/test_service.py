from silkyy.service import *
from silkyy.config import Config
from tornado.testing import AsyncHTTPTestCase
from silkyy.idworker import IdWorker
import os.path
import urllib
import logging
from six.moves.urllib.parse import urlencode

logger = logging.getLogger(__name__)

class ServiceTestBase(AsyncHTTPTestCase):
    @classmethod
    def setUpClass(cls):
        if os._exists('test.db'):
            os.remove('test.db')
        config = Config(values = {'database_url': 'sqlite:///test.db'})
        init_database(config)
        os.environ['ASYNC_TEST_TIMEOUT'] = '30'

    def get_app(self):
        config = Config()
        redis_conn = redis.StrictRedis.from_url(config.get('redis_url'), decode_responses=True)
        id_worker = IdWorker(1,1)
        return make_app(redis_conn, config, id_worker)

class SpiderRunTest(ServiceTestBase):
    def test_run(self):
        project_name = 'test_project'
        spider_name = 'test_spider'
        spider_seen_key = ':%(project)s:%(spider)s:seen' % {'project': project_name, 'spider': spider_name}
        redis_conn = redis.StrictRedis(decode_responses=True)
        redis_conn.delete(spider_seen_key)


        url = '/s/%s/%s/run' % (project_name, spider_name)
        response = self.fetch(url, method='POST', body='')
        self.assertEqual(200, response.code)
        run_id = int(response.body)

        run_seen_key = ':%(project)s:%(spider)s:%(run)s:seen' % {'project': project_name, 'spider': spider_name,
                                                                'run': run_id}
        # if run is not complete, run_seen_set should have a ttl >0 and < 86400 (24 hours)
        self.assertTrue(0 < redis_conn.ttl(run_seen_key) <= 86400)

        item_count = 5
        spider_run_seen_url = url = '/s/%s/%s/run/%s/seen' % (project_name, spider_name, run_id)
        for i in range(item_count):
            post_data = {'item': str(i)}
            res = self.fetch(spider_run_seen_url, method='POST', body=urlencode(post_data))
            self.assertIsNotNone(res.body)
            self.assertEqual(200, res.code)
            effect = int(res.body)
            self.assertIsNotNone(effect)

        run_complete_url = '/s/%s/%s/run/%s/complete' % (project_name, spider_name, run_id)
        response = self.fetch(run_complete_url, method='POST', body='')
        self.assertEqual(200, response.code)
        self.assertEqual(redis_conn.zrange(spider_seen_key, 0, -1), [str(x) for x in range(item_count)])

        # run seen set should not exists when complete
        run_seen_key = ':%(project)s:%(spider)s:%(run)s:seen' % {'project': project_name, 'spider': spider_name,
                                                                'run': run_id}
        self.assertEqual(0, redis_conn.exists(run_seen_key))

    def test_merge_when_complete(self):
        project_name = 'test_project'
        spider_name = 'test_spider'
        spider_seen_key = ':%(project)s:%(spider)s:seen' % {'project': project_name, 'spider': spider_name}
        redis_conn = redis.StrictRedis(decode_responses=True)
        redis_conn.delete(spider_seen_key)
        redis_conn.zadd(spider_seen_key, {str(x): 0 for x in range(3,10)})

        url = '/s/%s/%s/run' % (project_name, spider_name)
        response = self.fetch(url, method='POST', body='')
        self.assertEqual(200, response.code)
        run_id = int(response.body)

        run_seen_key = ':%(project)s:%(spider)s:%(run)s:seen' % {'project': project_name, 'spider': spider_name,
                                                                'run': run_id}
        # if run is not complete, run_seen_set should have a ttl >0 and < 86400 (24 hours)
        self.assertTrue(0 < redis_conn.ttl(run_seen_key) <= 86400)

        item_count = 5
        spider_run_seen_url = url = '/s/%s/%s/run/%s/seen' % (project_name, spider_name, run_id)
        for i in range(item_count):
            post_data = {'item': str(i)}
            res = self.fetch(spider_run_seen_url, method='POST', body=urlencode(post_data))
            self.assertIsNotNone(res.body)
            self.assertEqual(200, res.code)
            effect = int(res.body)
            self.assertIsNotNone(effect)

        run_complete_url = '/s/%s/%s/run/%s/complete' % (project_name, spider_name, run_id)
        response = self.fetch(run_complete_url, method='POST', body='')
        self.assertEqual(200, response.code)
        self.assertEqual(set(redis_conn.zrange(spider_seen_key, 0, -1)),
                         {str(x) for x in range(item_count)}.union({str(x) for x in range(3, 10)}))

        # run seen set should not exists when complete
        run_seen_key = ':%(project)s:%(spider)s:%(run)s:seen' % {'project': project_name, 'spider': spider_name,
                                                                'run': run_id}
        self.assertEqual(0, redis_conn.exists(run_seen_key))

    def test_run_not_exist(self):
        project_name = 'test_project'
        spider_name = 'test_spider'
        # an not exist run_id
        run_id = 123
        spider_run_seen_url = url = '/s/%s/%s/run/%s/seen' % (project_name, spider_name, run_id)
        post_data = {'item': '1'}
        response = self.fetch(spider_run_seen_url, method='POST', body=urlencode(post_data))
        self.assertEqual(400, response.code)

    def test_update_spider_settings(self):
        project_name = 'test_project'
        spider_name = 'test_spider'
        response = self.fetch('/api/v1/s/%s/%s' % (project_name, spider_name), method='PUT', body='')
        self.assertEqual(200, response.code)
        spider_settings_url = '/api/v1/s/%s/%s/settings' % (project_name, spider_name)

        test_settings = {'a': '123', 'some_other_setting': 'some very long settings value'}

        response = self.fetch(spider_settings_url, method='PATCH', body=json.dumps(test_settings))
        self.assertEqual(200, response.code)
        updated_settings = json.loads(response.body, )['settings']

        self.assertEqual(test_settings, updated_settings)

        response = self.fetch(spider_settings_url, method='GET')
        self.assertEqual(200, response.code)
        get_settings = json.loads(response.body)['settings']
        self.assertEqual(test_settings, get_settings)


