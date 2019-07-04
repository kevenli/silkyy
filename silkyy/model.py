from sqlalchemy import create_engine, schema, Column, ForeignKey, UniqueConstraint
from sqlalchemy.types import Integer, String, DateTime, Text, Boolean, DECIMAL, DATE, BIGINT
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import text
from .config import Config
import logging
from migrate.versioning.api import version_control, upgrade
from contextlib import contextmanager
from migrate.exceptions import DatabaseAlreadyControlledError
from sqlalchemy.sql import func
import datetime
import os

metadata = schema.MetaData()
Base = declarative_base(metadata=metadata)

@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = Session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()

def init_database(config=None):
    global database_url
    global engine
    global _Session
    #engine = create_mysql_engine(config)
    engine = create_engine(config.get('database_url'))
    _Session = sessionmaker(bind=engine, expire_on_commit=False)
    db_repository = os.path.join(os.path.dirname(__file__), 'migrations')
    try:
        version_control(url=engine, repository=db_repository)
    except DatabaseAlreadyControlledError:
        pass
    upgrade(engine, db_repository)

def _make_session():
    global _Session
    return _Session()

Session = _make_session

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
    spider = relationship("Spider", backref="settings")

    __table_args__ = (UniqueConstraint('spider_id', 'setting_key', name='spider_settings_spider_id_setting_key'),)

    @staticmethod
    def get_priders_setting(spider_id, setting_key, default_value=None):
        with session_scope() as session:
            existing_setting = session.query(SpiderSettings).filter_by(spider_id=spider_id, setting_key = setting_key).first()
            if existing_setting:
                return existing_setting.setting_value
            else:
                return default_value

class SpiderRun(Base):
    __tablename__ = 'spider_run'
    id = Column(BIGINT, primary_key=True)
    spider_id = Column(Integer, ForeignKey('spider.id'))
    create_time = Column(DateTime(timezone=True), server_default=func.now())