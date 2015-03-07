# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from gaebusiness.gaeutil import ModelSearchCommand
from google.appengine.api import memcache
from gaepagseguro.model import PagSegAccessData


class FindAccessDataCmd(ModelSearchCommand):
    def __init__(self):
        super(FindAccessDataCmd, self).__init__(PagSegAccessData.query(), 1)

    def do_business(self, stop_on_error=True):
        super(FindAccessDataCmd, self).do_business(stop_on_error)
        self.result = self.result[0] if self.result else None


class CreateOrUpdateAccessData(FindAccessDataCmd):
    def __init__(self, email, token):
        super(CreateOrUpdateAccessData, self).__init__()
        self.token = token
        self.email = email

    def do_business(self, stop_on_error=True):
        super(CreateOrUpdateAccessData, self).do_business(stop_on_error)
        if self.result:
            self.result.email = self.email
            self.result.token = self.token
        else:
            self.result = PagSegAccessData(email=self.email, token=self.token)

    def commit(self):
        return self.result