#!/usr/bin/env python
# -*- coding: utf-8 -*-


class MonthTranslationError(Exception):
    def __init__(self, error_msg):
        self.error_msg = error_msg

    def __str__(self):
        return "Cannot translate Dutch time to English " \
               "for datetime object. {}".format(self.error_msg)


class ErrorGettingDivision(Exception):
    def __init__(self):
        pass

    def __str__(self):
        return "Specified division doesn't exist"


class ErrorGettingLeague(Exception):
    def __init__(self):
        pass

    def __str__(self):
        return "Specified league doesn't exist"

