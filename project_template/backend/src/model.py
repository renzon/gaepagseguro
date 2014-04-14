# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from google.appengine.ext import ndb
from gaegraph.model import Node


class User(Node):
    google_id=ndb.StringProperty()

    @classmethod
    def query_by_google_id(cls, google_id):
        return cls.query(cls.google_id==google_id)


class OrderItem(Node):
    pass

