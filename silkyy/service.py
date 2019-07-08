import tornado
import tornado.web
import tornado.httpserver
import logging
import os
from .config import Config
import hashlib
import json
import datetime
import redis
import time
from .model import init_database, session_scope
from .model import Spider, SpiderSettings
from apscheduler.schedulers.tornado import TornadoScheduler
import re
from .process import fork_processes
from .idworker import IdWorker
from .appcontext import ApplicationContextProvider, DatabaseApplicationContextProvider, api_request_validate
log_dir = 'logs'
log_file = 'silkyy.log'
log_level = logging.INFO
table_name = 'T_BM_PAGES'

logger = logging.getLogger(__name__)

class JSONBaseHandler(tornado.web.RequestHandler):
    def prepare(self):
        super(JSONBaseHandler, self).prepare()
        self.json_data = None
        if self.request.body:
            try:
                self.json_data = tornado.escape.json_decode(self.request.body)
            except ValueError:
                # TODO: handle the error
                pass

    def get_argument(self, arg, default=None):
        # TODO: there's more arguments in the default get_argument() call
        # TODO: handle other method types
        if self.request.method in ['POST', 'PUT'] and self.json_data:
            return self.json_data.get(arg, default)
        else:
            return super(JSONBaseHandler, self).get_argument(arg, default)

class CJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, datetime.date):
            return obj.strftime('%Y-%m-%d')
        else:
            return json.JSONEncoder.default(self, obj)


def init_logging():
    import logging.handlers
    logger = logging.getLogger()

    if not os.path.exists(log_dir):
        os.mkdir(log_dir)
    fh = logging.handlers.TimedRotatingFileHandler(os.path.join(log_dir, log_file), when='D', backupCount=7)
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.setLevel(log_level)


class SpiderDuptfilter(tornado.web.RequestHandler):
    def initialize(self, redis_conn):
        self.redis_conn = redis_conn

    def post(self, project, spider):
        item = self.get_argument('item')
        timestamp = int(time.time())
        key = '%(project)s:%(spider)s:seen' % {'project': project, 'spider': spider}
        # score as the first found, do not replace when updating
        added = self.redis_conn.zadd(key, {item: timestamp}, nx=True)
        self.write(str(added))

class SpiderDuptfilterFlush(tornado.web.RequestHandler):
    def initialize(self, redis_conn):
        self.redis_conn = redis_conn

    def post(self, project, spider):
        key = '%(project)s:%(spider)s:seen' % {'project': project, 'spider': spider}
        # score as the first found, do not replace when updating
        ret = self.redis_conn.delete(key)
        self.write(str(ret))


class SpiderHandler(JSONBaseHandler):
    @api_request_validate
    def put(self, project, spider):
        with session_scope() as session:
            spider_obj = session.query(Spider)\
                .filter_by(project=project, spider_name=spider)\
                .first()

            if spider_obj is None:
                spider_obj = Spider()
                spider_obj.project = project
                spider_obj.spider_name = spider
                session.add(spider_obj)
                session.commit()
                session.refresh(spider_obj)
            self.set_header('Content-Type', 'application/json')
            self.write(json.dumps({'project': spider_obj.project, 'name': spider_obj.spider_name}))

    @api_request_validate
    def get(self, project, spider):
        with session_scope() as session:
            spider_obj = session.query(Spider) \
                .filter_by(project=project, spider_name=spider) \
                .first()

            if spider_obj is None:
                self.set_status(404, 'not found')
                return

            #response = {'spider': {'project': spider_obj.project, 'spider_name': spider_obj.spider_name},
            #            'settings': [{'key': setting.setting_key,'value':setting.setting_value } for setting in spider_obj.settings]}
            #=self.set_header('Content-Type', 'application/json')
            self.set_header('Content-Type', 'application/json')
            self.write(json.dumps({'project': spider_obj.project, 'name': spider_obj.spider_name}))



def init_ttl_clear_scheduler(redis_conn):
    ioloop = tornado.ioloop.IOLoop.current()
    scheduler = TornadoScheduler(io_loop=ioloop)
    job = scheduler.add_job(run_clear_tll, 'interval', minutes=1, max_instances=1, args=[redis_conn])
    scheduler.start()

def run_clear_tll(redis_conn):
    logger.info('clearing seen set')
    with session_scope() as session:
        for spider_obj in session.query(Spider).all():
            seen_key = '%(project)s:%(spider)s:seen' % {'project': spider_obj.project, 'spider': spider_obj.spider_name}
            expire_in = SpiderSettings.get_priders_setting(spider_obj.id, 'seen_expire', '7d')
            expire_in_seconds = 0
            if re.match('(\d+)\s*(d|days|day)$', expire_in):
                expire_in_seconds = datetime.timedelta(days=int(re.match('(\d+)\s*(d|days|day)$', expire_in).group(1))).total_seconds()
            elif re.match('(\d+)\s*(h|hours|hour)$', expire_in):
                expire_in_seconds = datetime.timedelta(hours=int(re.match('(\d+)\s*(h|hours|hour)$', expire_in).group(1))).total_seconds()
            elif re.match('(\d+)\s*(minutes|minute)$', expire_in):
                expire_in_seconds = datetime.timedelta(minutes=int(re.match('(\d+)\s*(minutes|minute)$', expire_in).group(1))).total_seconds()

            expire_before = time.time() - expire_in_seconds
            logger.info('clearing seen set, key:%s, expire_in: %s, expire_before:%s' % (seen_key, expire_in, expire_before))
            redis_conn.zremrangebyscore(seen_key, 0, expire_before)


class SpiderSettingsHandler(tornado.web.RequestHandler):
    def get(self, project, spider):
        with session_scope() as session:
            spider_obj = session.query(Spider) \
                .filter_by(project=project, spider_name=spider) \
                .first()

            if spider_obj is None:
                self.set_status(404, 'not found')
                return

            response = {
                'settings': {setting.setting_key: setting.setting_value for setting in
                             spider_obj.settings}
            }
            self.set_header('Content-Type', 'application/json')
            self.write(json.dumps(response))

    def patch(self, project, spider):
        patch_settings = json.loads(self.request.body)
        with session_scope() as session:
            spider_obj = session.query(Spider) \
                .filter_by(project=project, spider_name=spider) \
                .first()

            if spider_obj is None:
                self.set_status(404, 'not found')
                return

            for setting_key, setting_value in patch_settings.items():
                spider_setting = session.query(SpiderSettings).filter_by(spider_id = spider_obj.id, setting_key = setting_key).first()
                if spider_setting is None:
                    spider_setting = SpiderSettings()
                    spider_setting.spider_id = spider_obj.id
                    spider_setting.setting_key = setting_key
                spider_setting.setting_value = setting_value
                session.add(spider_setting)
                session.commit()

            #settings = session.query(SpiderSettings).filter_by(spider_id = spider_obj.id).all()
            response = {
                'settings': {setting.setting_key:setting.setting_value for setting in
                             spider_obj.settings}
            }
            self.set_header('Content-Type', 'application/json')
            self.write(json.dumps(response))


class SpiderSettingsInstanceHandler(tornado.web.RequestHandler):
    def put(self, project, spider, setting_key):
        with session_scope() as session:
            spider_obj = session.query(Spider) \
                .filter_by(project=project, spider_name=spider) \
                .first()

            if spider_obj is None:
                self.set_status(404, 'not found')
                return

            spider_setting = session.query(SpiderSettings).filter_by(spider_id = spider_obj.id, setting_key = setting_key).first()
            if spider_setting is None:
                spider_setting = SpiderSettings()
                spider_setting.spider_id = spider_obj.id
                spider_setting.setting_key = setting_key
            spider_setting.setting_value = self.request.body
            session.add(spider_setting)
            session.commit()


    def get(self, project, spider, setting_key):
        with session_scope() as session:
            spider_obj = session.query(Spider) \
                .filter_by(project=project, spider_name=spider) \
                .first()

            if spider_obj is None:
                self.set_status(404, 'not found')
                return

            spider_setting = session.query(SpiderSettings).filter_by(spider_id=spider_obj.id,
                                                                     setting_key=setting_key).first()
            if spider_setting is None:
                self.set_status(404, 'not found')
                return

            self.write(spider_setting.setting_value)


class SpiderRunHandler(tornado.web.RequestHandler):
    def initialize(self, redis_conn, id_worker):
        self.redis_conn = redis_conn
        self.id_worker = id_worker

    @api_request_validate
    def post(self, project_name, spider_name):
        spider_seen_key = '%(app_id)s:%(project)s:%(spider)s:seen' % {'project': project_name,
                                                                      'spider': spider_name,
                                                                      'app_id': self.app_id}
        run_id = self.id_worker.get_id('run')
        run_seen_key = '%(app_id)s:%(project)s:%(spider)s:%(run)d:seen' % {'project': project_name,
                                                                            'spider': spider_name,
                                                                            'run': run_id,
                                                                           'app_id': self.app_id}
        pipe = self.redis_conn.pipeline()
        pipe.zunionstore(run_seen_key, [spider_seen_key], aggregate='max')
        pipe.zadd(run_seen_key, {"": 0})
        run_set_ttl = 24 * 60 * 60 # run key keeps 1 day
        pipe.expire(run_seen_key, run_set_ttl)
        pipe.execute()
        self.write(str(run_id))


class SpiderRunDuptfilter(tornado.web.RequestHandler):
    def initialize(self, redis_conn):
        self.redis_conn = redis_conn

    @api_request_validate
    def post(self, project_name, spider_name, run_id):
        item = self.get_argument('item')
        assert item is not None
        timestamp = int(time.time())
        run_id = int(run_id)

        run_seen_key = '%(app_id)s:%(project)s:%(spider)s:%(run)d:seen' % {'project': project_name,
                                                                            'spider': spider_name,
                                                                            'run': run_id,
                                                                           'app_id': self.app_id}
        if not self.redis_conn.exists(run_seen_key):
            self.set_status(400)
            self.write('Run dose not exist.')
            return
        # score as the first found, do not replace when updating
        #added = self.redis_conn.zadd(key, {item: timestamp}, nx=True)
        added = self.redis_conn.zadd(run_seen_key, {item: timestamp}, nx=True)
        self.write(str(added))


class SpiderRunComplete(tornado.web.RequestHandler):
    def initialize(self, redis_conn):
        self.redis_conn = redis_conn

    @api_request_validate
    def post(self, project_name, spider_name, run_id):
        run_id = int(run_id)
        run_seen_key = '%(app_id)s:%(project)s:%(spider)s:%(run)d:seen' % {'project': project_name,
                                                                            'spider': spider_name,
                                                                            'run': run_id,
                                                                           'app_id': self.app_id}
        spider_seen_key = '%(app_id)s:%(project)s:%(spider)s:seen' % {'project': project_name,
                                                                      'spider': spider_name,
                                                                      'app_id': self.app_id}
        pipe = self.redis_conn.pipeline()
        # remove space holder
        pipe.zrem(run_seen_key, "")
        # when complete, merge it into the spider SEEN
        pipe.zunionstore(spider_seen_key, [run_seen_key], aggregate='min')
        # clear current run seen set
        pipe.delete(run_seen_key)
        pipe.execute()

        response = "OK"
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps(response))


def make_app(redis_conn, config, id_worker=None, app_context_provider=None):
    if app_context_provider is None:
        app_context_provider = ApplicationContextProvider()

    if id_worker is None:
        id_worker = IdWorker(1, 1)

    return tornado.web.Application([
        ('^/s/([\w_]+)/([\w_]+)$', SpiderHandler),
        ('^/s/([\w_]+)/([\w_]+)/settings$', SpiderSettingsHandler),
        ('^/s/([\w_]+)/([\w_]+)/settings/([\w_]+)$', SpiderSettingsInstanceHandler),
        ('^/s/([\w_]+)/([\w_]+)/run$', SpiderRunHandler, {'redis_conn': redis_conn, 'id_worker': id_worker}),
        ('^/s/([\w_]+)/([\w_]+)/run/(\d+)/seen$', SpiderRunDuptfilter, {'redis_conn': redis_conn}),
        ('^/s/([\w_]+)/([\w_]+)/run/(\d+)/complete$', SpiderRunComplete, {'redis_conn': redis_conn}),
        ('^/s/([\w_]+)/([\w_]+)/seen$', SpiderDuptfilter, {'redis_conn': redis_conn}),
        ('^/s/([\w_]+)/([\w_]+)/seen/flush$', SpiderDuptfilterFlush, {'redis_conn': redis_conn}),

        ('^/api/v1/s/([\w_]+)/([\w_]+)$', SpiderHandler),
        ('^/api/v1/s/([\w_]+)/([\w_]+)/settings$', SpiderSettingsHandler),
        ('^/api/v1/s/([\w_]+)/([\w_]+)/settings/([\w_]+)$', SpiderSettingsInstanceHandler),
        ('^/api/v1/s/([\w_]+)/([\w_]+)/run$', SpiderRunHandler, {'redis_conn': redis_conn, 'id_worker': id_worker}),
        ('^/api/v1/s/([\w_]+)/([\w_]+)/run/(\d+)/seen$', SpiderRunDuptfilter, {'redis_conn': redis_conn}),
        ('^/api/v1/s/([\w_]+)/([\w_]+)/run/(\d+)/complete$', SpiderRunComplete, {'redis_conn': redis_conn}),
        ('^/api/v1/s/([\w_]+)/([\w_]+)/seen$', SpiderDuptfilter, {'redis_conn': redis_conn}),
        ('^/api/v1/s/([\w_]+)/([\w_]+)/seen/flush$', SpiderDuptfilterFlush, {'redis_conn': redis_conn}),
    ], app_context_provider=app_context_provider)


def run():
    config = Config()
    init_logging()
    init_database(config)

    bind_address = config.get('bind_address')
    bind_port = config.getint('bind_port')

    sockets = tornado.netutil.bind_sockets(bind_port, bind_address)
    fork_count = 1

    task_id = 1
    if fork_count>1:
        task_id = fork_processes(fork_count)

    redis_conn = redis.StrictRedis.from_url(config.get('redis_url'), decode_responses=True)

    id_worker = IdWorker(1, task_id)
    app_context_provider = ApplicationContextProvider()
    init_ttl_clear_scheduler(redis_conn)
    app = make_app(redis_conn, config, id_worker, app_context_provider)
    server = tornado.httpserver.HTTPServer(app)
    server.add_sockets(sockets)
    logger.info('Listening on %s:%s' % (bind_address, bind_port))
    ioloop = tornado.ioloop.IOLoop.current()
    ioloop.start()

if __name__ == '__main__':
    run()