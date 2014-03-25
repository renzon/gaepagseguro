# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from google.appengine.ext import ndb
from gaegraph.model import Node


class PagSeguroAccessData(Node):
    email = ndb.StringProperty(required=True, indexed=False)
    token = ndb.StringProperty(required=True, indexed=False)


