from sqlalchemy import *
from migrate import *
from sqlalchemy.ext.declarative import declarative_base

metadata = schema.MetaData()
Base = declarative_base(metadata=metadata)

spider_run = Table(
    'spider_run', metadata,
    Column('id', BIGINT, primary_key=True),
    Column('spider_id', Integer),
    Column('create_time', DateTime(timezone=True), server_default=func.now())
)

def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    spider_run.create()


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    spider_run.drop()
