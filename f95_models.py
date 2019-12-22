from sqlalchemy import Column, ForeignKey, Integer, Boolean, Float, Text, UniqueConstraint, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine

Base = declarative_base()


def db_connect():
    """
    Performs database connection using database settings from settings.py.
    Returns sqlalchemy engine instance
    """
    return create_engine(r'sqlite:///f95.db3')


def create_tables(engine):
    """"""
    Base.metadata.create_all(engine)


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    name = Column(Text)
    url = Column(Text)


class Prefix(Base):
    __tablename__ = 'prefix'
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True)
    url = Column(Text)


class Tag(Base):
    __tablename__ = 'tag'
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True)
    url = Column(Text)


class Image(Base):
    __tablename__ = 'image'
    id = Column(Integer, primary_key=True)
    name = Column(Text)
    url = Column(Text, unique=True)


class Developer(Base):
    __tablename__ = 'developer'
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True)
    url = Column(Text)


class Platform(Base):
    __tablename__ = 'platform'
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True)


class Link(Base):
    __tablename__ = 'link'
    id = Column(Integer, primary_key=True)
    url = Column(Text, unique=True)


class Language(Base):
    __tablename__ = 'language'
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True)


class Thread(Base):
    __tablename__ = 'thread'
    id = Column(Integer, primary_key=True)
    canonical = Column(Text)
    title = Column(Text)
    user_id = Column(Integer, ForeignKey('user.id'))
    rating = Column(Float)
    date = Column(Integer)
    edited = Column(Integer)
    overview = Column(Text)
    developer_id = Column(Integer, ForeignKey('developer.id'))
    platform_id = Column(Integer, ForeignKey('platform.id'))
    censorship = Column(Text)
    language_id = Column(Integer, ForeignKey('language.id'))
    version = Column(Text)
    views = Column(Integer)
    likes = Column(Integer)
    votes = Column(Integer)
    prefixes = Column(Text)
    pages = Column(Integer)
    image_cover = Column(Text)


class ThreadImage(Base):
    __tablename__ = 'threadimage'
    id = Column(Integer, primary_key=True)
    thread_id = Column(Integer, ForeignKey('thread.id'))
    image_id = Column(Integer, ForeignKey('image.id'))
    __table_args__ = (UniqueConstraint('thread_id', 'image_id', name='thread_image_key'),)


class ThreadLink(Base):
    __tablename__ = 'threadlink'
    id = Column(Integer, primary_key=True)
    thread_id = Column(Integer, ForeignKey('thread.id'))
    link_id = Column(Integer, ForeignKey('link.id'))
    __table_args__ = (UniqueConstraint('thread_id', 'link_id', name='thread_link_key'),)


class ThreadTag(Base):
    __tablename__ = 'threadtag'
    id = Column(Integer, primary_key=True)
    thread_id = Column(Integer, ForeignKey('thread.id'))
    tag_id = Column(Integer, ForeignKey('tag.id'))
    __table_args__ = (UniqueConstraint('thread_id', 'tag_id', name='thread_tag_key'),)


class ThreadPrefix(Base):
    __tablename__ = 'threadprefix'
    id = Column(Integer, primary_key=True)
    thread_id = Column(Integer, ForeignKey('thread.id'))
    prefix_id = Column(Integer, ForeignKey('prefix.id'))
    __table_args__ = (UniqueConstraint('thread_id', 'prefix_id', name='thread_prefix_key'),)


class Downloaded(Base):
    __tablename__ = 'downloaded'
    id = Column(Integer, primary_key=True)
    path = Column(Text, unique=True)
    version = Column(Text)
