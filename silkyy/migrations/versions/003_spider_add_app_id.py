from sqlalchemy import *
from migrate import *


def upgrade(migrate_engine):
    meta = MetaData(bind=migrate_engine)
    table = Table('spider', meta, autoload=True)
    spider_app_id = Column('app_id', Integer, default=0)
    spider_app_id.create(table)


def downgrade(migrate_engine):
    meta = MetaData(bind=migrate_engine)
    table = Table('spider', meta, autoload=True)
    table.c['app_id'].drop()
