import unittest
from silkyy.client import SilkyyClient
from tornado.testing import AsyncHTTPTestCase, gen_test
from silkyy.service import *
from silkyy.model import *
from tornado.ioloop import IOLoop

@unittest.skip
class ClientTest(AsyncHTTPTestCase):
    @classmethod
    def setUpClass(cls):
        if os._exists('test.db'):
            os.remove('test.db')
        config = Config(values = {'database_url': 'sqlite:///test.db'})
        init_database(config)
        os.environ['ASYNC_TEST_TIMEOUT'] = '30'

    def setUp(self):
        super(ClientTest, self).setUp()
        self.target = SilkyyClient(self.get_url('/'))

    def get_app(self):
        config = Config()
        redis_conn = redis.StrictRedis.from_url(config.get('redis_url'), decode_responses=True)
        return make_app(redis_conn, config)

    @gen_test
    def test_create_spider(self):
        project_name = 'test_project'
        spider_name = 'test_spider'

        #response = self.fetch('/api/v1/s/a/b')

        spider = self.target.spider(project_name, spider_name, auto_create=True)
        self.assertEqual(project_name, spider.project)
        self.assertEqual(spider_name, spider.name)
        self.stop()

    def test_update_spider_settings(self):
        project_name = 'test_project'
        spider_name = 'test_spider'
        setting_key1 = 'key1'
        setting_value1 = 'value1'
        setting_key2 = 'key2'
        setting_value2 = 'value2'

        spider = self.target.spider(project_name, spider_name, auto_create=True)
        spider.update_setttings({setting_key1:setting_value1,
                                setting_key2:setting_value2})
        settings = self.target.settings()
        self.assertEqual(settings[setting_key1], setting_value1)
        self.assertEqual(settings[setting_key2], setting_value2)

    def test_create_spider_run(self):
        project_name = 'test_project'
        spider_name = 'test_spider'

        self.target.spider(project_name, spider_name).create_run()
