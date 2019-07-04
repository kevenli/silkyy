from six.moves.urllib import parse as urlparse
import datetime
import hashlib
import logging

def build_storage(db_url):
    urlparts = urlparse.urlparse(db_url)
    if urlparts.scheme == 'redis':
        return RedisStorage(db_url)
    else:
        return KidaStorage(db_url)

class RedisStorage(object):
    def __init__(self, db_url):
        import redis
        urlparts = urlparse.urlparse(db_url)
        self.r = redis.StrictRedis(host=urlparts.hostname, port=urlparts.port, db=0)

    def _get_visited_key(self, project, request_key, spider):
        redis_key = '%s:%s:%s' % (project, spider, request_key)
        return redis_key

    def get_visited(self, project, request_key, spider=None):
        redis_key = self._get_visited_key(project, request_key, spider)
        return self.r.get(redis_key)

    def set_visited(self, project, request_key, spider=None):
        visited_timestamp = datetime.datetime.now()
        redis_key = self._get_visited_key(project, request_key, spider)
        self.r.set(redis_key, visited_timestamp)


class KidaStorage(object):
    table_name = 'T_BM_PAGES'
    def __init__(self, db_url):
        import kida
        self.meta = kida.Meta()
        self.context = kida.connect(db_url, self.meta)

    def set_visited(self, project, request_key, spider=None):
        target_url = request_key
        url_hash = hashlib.md5(request_key.encode('utf8')).hexdigest()
        context = self.context
        existing = self.context.get(KidaStorage.table_name, {'url': target_url, 'url_hash': url_hash})
        if not existing:
            page_obj = {
                'url_hash': url_hash,
                'url': target_url,
                'status': 3,
                'update_time': datetime.datetime.now(),
                'create_time': datetime.datetime.now(),
            }
            context.save(KidaStorage.table_name, page_obj)
            context.commit()

    def get_visited(self, project, request_key, spider=None):
        pass
