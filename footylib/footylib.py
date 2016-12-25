#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from requests import Session
from footylibExceptions import *
from bs4 import BeautifulSoup as Bfs
from datetime import datetime, timedelta
from ics import Calendar, Event


LOGGER_BASENAME = '''footylib'''
LOGGER = logging.getLogger(LOGGER_BASENAME)
LOGGER.setLevel(logging.DEBUG)
LOGGER.addHandler(logging.NullHandler())


class Footy(object):
    def __init__(self):
        self.logger = logging.getLogger('{base}.{suffix}'.format(
            base=LOGGER_BASENAME, suffix=self.__class__.__name__))
        self.site = "http://www.footy.eu/"
        self.headers = {'User-Agent': 'Mozilla/5.0'}
        self.session = Session()
        self.session.headers.update(self.headers)
        self.front_page = self.__get_footy_front_page()
        self.competitions = self.get_competitions()

    def __get_footy_front_page(self):
        page = self.session.get(self.site)
        try:
            soup = Bfs(page.text, 'html.parser')
            return soup
        except Bfs.HTMLParser.HTMLParseError:
            self.logger.exception("Error while parsing Footy front page")

    def get_competitions(self):
        competitions = []
        locations = self.front_page.find_all('div',
                                             {'class': 'fusion-panel panel-default'})
        for location_data in locations:
            location = location_data.find('div',
                                          {'class': 'fusion-toggle-heading'}
                                          ).text
            for competition in location_data.find_all('a',
                                                      {'class': 'footycombut'}):
                url = competition.attrs['href']
                name = competition.text
                competitions.append(Competition(self, location, url, name))
        return competitions


class Competition(object):
    def __init__(self, footy_instance, location, url, name):
        self.logger = logging.getLogger('{base}.{suffix}'.format(
            base=LOGGER_BASENAME, suffix=self.__class__.__name__))
        self.session = footy_instance.session
        self._populate(location, url, name)

    def _populate(self, location, url, name):
        try:
            self.location = location
            self.url = url
            self.name = name
        except KeyError:
            self.logger.exception("Got an exception in Competition")

    def get_teams(self):
        team_page = self.session.get(self.url)
        soup = Bfs(team_page.text, "html.parser")
        standings = soup.find_all('table',
                                  {'class': 'leaguemanager standingstable'})
        team = []
        for teams in standings:
            for row in teams.find_all('tr', {'class': ('alternate', '')}):
                team.append(Team(row))
        return team

    def get_matches(self):
        team_page = self.session.get(self.url)
        soup = Bfs(team_page.text, "html.parser")
        match_tables = soup.find_all('table',
                                     {'class': 'leaguemanager matchtable'})
        all_matches = []
        for match_table in match_tables:
            division = match_table.attrs['title']
            all_matches.extend([Match(row, division)
                                for row in match_table.find_all('tr',
                                                                {'class': ('alternate', '')})])
        return all_matches


class Team(object):
    def __init__(self, info):
        self.logger = logging.getLogger('{base}.{suffix}'.format(
            base=LOGGER_BASENAME, suffix=self.__class__.__name__))
        self._populate(info)

    def _populate(self, info):
        try:
            self.position = info.contents[1].text
            self.team_name = info.contents[5].text.encode("utf-8")
            self.played_games = info.contents[7].text
            self.won_games = info.contents[9].text
            self.tie_games = info.contents[11].text
            self.lost_games = info.contents[13].text
            self.goals = info.contents[15].text
            self.diff = info.contents[16].text
            self.points = info.contents[18].text
        except KeyError:
            self.logger.exception("Got an exception while populating teams")


class Match(object):
    def __init__(self, info, division=None):
        self.logger = logging.getLogger('{base}.{suffix}'.format(
            base=LOGGER_BASENAME, suffix=self.__class__.__name__))
        self._populate(info, division)

    def _populate(self, info, division):
        try:
            self.date = info.find('td', {'class': 'date1'}).text
            self.time = info.find('td', {'class': 'time'}).text
            self.location = info.find('td', {'class': 'location'}).text
            self.match = info.find('td', {'class': 'match'}).text
            self.score = info.find('td', {'class': 'score'}).text
            self.referee = info.find('td', {'class': 'ref'}).text
            self.motm = info.find('td', {'class': 'man'}).text
            self.datetime = self.string_to_datetime(self.date, self.time)
            self.division = division or ''
        except KeyError:
            self.logger.exception("Got an exception on Matches.")

    def string_to_datetime(self, date, time):
        dutch_datetime = '{} {}'.format(date, time).split()
        english_datetime = self.dutch_to_english_reference(dutch_datetime[0])
        dutch_datetime[0] = english_datetime
        english_datetime = " ".join(dutch_datetime)
        datetime_object = datetime.strptime(english_datetime,
                                            '%B %d, %Y %I:%M %p')
        return datetime_object

    @staticmethod
    def dutch_to_english_reference(dutch_month):
        """
        Replace Dutch month for English name. Used for datetime objects
        :param dutch_month: dutch month string
        :return: month in English
        """
        months = {"januari": "January", "februari": "February",
                  "maart": "March", "april": "April",
                  "mei": "May", "juni": "June",
                  "juli": "July", "augustus": "August",
                  "september": "September", "oktober": "October",
                  "november": "November", "december": "December"}
        return months[dutch_month]
