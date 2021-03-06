# -*- coding: UTF-8 -*-
import json
import random
import string
from sqlalchemy import Column, Integer, String, Text, TypeDecorator
from sqlalchemy.ext.declarative import declarative_base

BaseModel = declarative_base()


class JSONEncodedDict(TypeDecorator):
    """Represents an immutable structure as a json-encoded string.
    Usage::
            JSONEncodedDict(255)
    """
    impl = String

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


class Tracer(BaseModel):
    """Tracer model
    """
    __tablename__ = 'tracers'

    id = Column(String(255), primary_key=True)
    title = Column(String(255), default='')
    content = Column(Text(1024 * 4), default='')
    clicked = Column(Integer, default=0)
    posted = Column(Integer, default=0)
    qr = Column(String(255), default='')
    url = Column(String(255), default='')

    @classmethod
    def gen_id(cls, bit):
        return ''.join(random.sample(string.ascii_letters + string.digits, bit))
