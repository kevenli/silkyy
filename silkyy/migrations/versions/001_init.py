from sqlalchemy import *
from migrate import *
from sqlalchemy.ext.declarative import declarative_base

metadata = schema.MetaData()
Base = declarative_base(metadata=metadata)

class Spider(Base):
    __tablename__ = 'spider'
    id = Column(Integer, primary_key=True, autoincrement=True)
    project = Column(String(length=50))
    spider_name = Column(String(length=50))
    create_time = Column(DateTime(timezone=True), server_default=func.now())

class SpiderSettings(Base):
    __tablename__ = 'spider_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    spider_id = Column(Integer, ForeignKey('spider.id'))
    setting_key = Column(String(length=50))
    setting_value = Column(String(length=500))
    create_time = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint('spider_id', 'setting_key', name='spider_settings_spider_id_setting_key'),)

def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.tables['spider'].create()
    metadata.tables['spider_settings'].create()


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.tables['spider'].drop()
    metadata.tables['spider_settings'].drop()
