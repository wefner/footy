#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytz
import logging
import locale
from requests import Session
from footylibExceptions import *
from bs4 import BeautifulSoup as Bfs
from datetime import datetime, timedelta
from icalendar import Calendar, Event


LOGGER_BASENAME = '''footylib'''
LOGGER = logging.getLogger(LOGGER_BASENAME)
LOGGER.setLevel(logging.DEBUG)
LOGGER.addHandler(logging.NullHandler())


class Footy(object):
    def __init__(self):
        self.logger = logging.getLogger('{base}.{suffix}'.format(
            base=LOGGER_BASENAME, suffix=self.__class__.__name__))
        self._site = "http://www.footy.eu/"
        self._headers = {'User-Agent': 'Mozilla/5.0'}
        self.session = Session()
        self.session.headers.update(self._headers)
        self._front_page = None
        self._competitions = []

    @property
    def __front_page(self):
        if not self._front_page:
            page = self.session.get(self._site)
            try:
                self._front_page = Bfs(page.text,'html.parser')
            except Bfs.HTMLParser.HTMLParseError:
                self.logger.exception("Error while parsing Footy front page")
        return self._front_page

    @property
    def competitions(self):
        if not self._competitions:
            locations = self.__front_page.find_all('div',
                                                 {'class': 'fusion-panel panel-default'})
            for location_data in locations:
                location = location_data.find('div',
                                              {'class': 'fusion-toggle-heading'}
                                              ).text
                for competition in location_data.find_all('a',
                                                          {'class': 'footycombut'}):
                    url = competition.attrs['href']
                    name = competition.text
                    self._competitions.append(Competition(self,
                                                          location,
                                                          url,
                                                          name))
        return self._competitions

    def get_team(self, team_name):
        team = None
        for competition in self.competitions:
            team = next((team for team in competition.teams
                         if team.name == team_name), None)
            if team:
                break
        return team

    def search_team(self, team_name):
        possible_teams = []
        for competition in self.competitions:
            for team in competition.teams:
                if team_name in team.name:
                    possible_teams.append(team)
        return possible_teams


class Competition(object):
    def __init__(self, footy_instance, location, url, name):
        self._logger = logging.getLogger('{base}.{suffix}'.format(
            base=LOGGER_BASENAME, suffix=self.__class__.__name__))
        self.session = footy_instance.session
        self._populate(location, url, name)
        self._teams = []
        self._matches = []
        self._calendar = None
        self._soup = None

    def _populate(self, location, url, name):
        try:
            self.location = location
            self.url = url
            self.name = name.encode('utf-8').strip()
        except KeyError:
            self._logger.exception("Got an exception in Competition")

    @property
    def teams(self):
        if not self._teams:
            standings = self._get_table('standingstable')
            for teams in standings:
                for row in teams.find_all('tr', {'class': ('alternate', '')}):
                    self._teams.append(Team(self, row))
        return self._teams

    @property
    def matches(self):
        if not self._matches:
            match_tables = self._get_table('matchtable')
            for match_table in match_tables:
                for row in match_table.find_all('tr',
                                                {'class': ('alternate', '')}):
                    division = match_table.attrs['title']
                    self._matches.append(Match(self, row, division))
        return self._matches

    def _get_table(self, class_attribute):
        if not self._soup:
            competition_page = self.session.get(self.url)
            self._soup = Bfs(competition_page.text, "html.parser")
        return self._soup.find_all('table',
                                    {'class': 'leaguemanager {}'.format(class_attribute)})

    @property
    def calendar(self):
        if not self._calendar:
            self._calendar = Calendar()
            for team in self.teams:
                for event in team.events:
                    self._calendar.add_component(event)
        return self._calendar


class Team(object):
    def __init__(self, competition_instance, info):
        self.logger = logging.getLogger('{base}.{suffix}'.format(
            base=LOGGER_BASENAME, suffix=self.__class__.__name__))
        self.session = competition_instance.session
        self.competition = competition_instance
        self.url = competition_instance.url
        self._populate(info)
        self._calendar = None

    def _populate(self, info):
        try:
            self.position = info.contents[1].text
            self.name = info.contents[5].text.encode('utf-8').strip()
            self.played_games = info.contents[7].text
            self.won_games = info.contents[9].text
            self.tie_games = info.contents[11].text
            self.lost_games = info.contents[13].text
            self.goals = info.contents[15].text
            self.diff = info.contents[16].text
            self.points = info.contents[18].text
        except KeyError:
            self.logger.exception("Got an exception while populating teams")

    @property
    def matches(self):
        return [match for match in self.competition.matches
                if self.name in match.title]

    @property
    def events(self):
        return [match.event for match in self.matches]

    @property
    def calendar(self):
        if not self._calendar:
            self._calendar = Calendar()
            for event in self.events:
                self._calendar.add_component(event)
        return self._calendar


class Match(object):
    def __init__(self, competition_instance, info, division=None):
        self.logger = logging.getLogger('{base}.{suffix}'.format(
            base=LOGGER_BASENAME, suffix=self.__class__.__name__))
        self._populate(info, division)
        self.competitions = competition_instance
        self._calendar = None
        self.event = FootyEvent(self.datetime, self.title, self.location)

    def _populate(self, info, division):
        try:
            self._date = info.find('td', {'class': 'date1'}).text
            self._time = info.find('td', {'class': 'time'}).text
            self.location = info.find('td', {'class': 'location'}).text
            self.title = info.find('td', {'class': 'match'}).text.encode('utf-8').strip()
            self.score = info.find('td', {'class': 'score'}).text
            self.referee = info.find('td', {'class': 'ref'}).text
            self.motm = info.find('td', {'class': 'man'}).text
            self.datetime = self.__string_to_datetime(self._date, self._time)
            self.division = division or ''
        except KeyError:
            self.logger.exception("Got an exception on Matches.")

    @property
    def visiting_team(self):
        return self._get_team(home_team=False)

    @property
    def home_team(self):
        return self._get_team()

    def _get_team(self, home_team=True):
        home, visiting = self.title.split(' – ')
        match = home.strip()
        if not home_team:
            match = visiting.strip()
        team = next((team for team in self.competitions.teams
                     if team.name == match), None)
        return team

    @property
    def calendar(self):
        if not self._calendar:
            self._calendar = Calendar()
            self._calendar.add_component(self.event)
        return self._calendar

    @staticmethod
    def __string_to_datetime(date, time):
        locale.setlocale(locale.LC_TIME, 'nl_NL')
        dutch_datetime = '{} {}'.format(date.capitalize(), time)
        try:
            datetime_object = datetime.strptime(dutch_datetime,
                                                '%B %d, %Y %I:%M %p')
            return datetime_object
        except ValueError:
            LOGGER.exception("Couldn't parse this datetime.")


class FootyEvent(object):
    def __new__(self, match_date, match, location):
        self.logger = logging.getLogger('{base}.{suffix}'.format(
            base=LOGGER_BASENAME, suffix=self.__class__.__name__))
        self.timezone = 'Europe/Amsterdam'
        event = Event(duration=timedelta(hours=1))
        try:
            event.add('dtstart',
                      pytz.timezone(self.timezone).localize(match_date))
            event.add('summary', match)
        except AttributeError:
            self.logger.exception('{} not valid datetime'.format(match_date))
        return event
