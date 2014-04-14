# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from google.appengine.api import users
from gaebusiness.gaeutil import ModelSearchCommand
from model import User


class FindOrCreateUserCmd(ModelSearchCommand):
    def __init__(self):
        g_user = users.get_current_user()
        google_id = g_user and g_user.user_id()
        query = User.query_by_google_id(google_id)
        super(FindOrCreateUserCmd, self).__init__(query, 1)
        self.__to_commit = None
        self.google_id = google_id

    def do_business(self, stop_on_error=True):
        super(FindOrCreateUserCmd, self).do_business(stop_on_error)
        if self.result:
            self.result = self.result[0]
        elif self.google_id:
            self.result = User(google_id=self.google_id)
            self.__to_commit = self.result

    def commit(self):
        return self.__to_commit