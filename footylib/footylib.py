#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytz
import logging
import locale
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
        self._front_page = None
        self._competitions = []

    @property
    def __front_page(self):
        if not self._front_page:
            page = self.session.get(self.site)
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
        output = None
        for competition in self.competitions:
            for team in competition.teams:
                if team.name == team_name:
                    self.logger.info("Team {} found".format(team_name))
                    output = team
                # TODO: exit from outter loop as soon as found
        return output

    def search_team(self, team_name):
        possible_teams = []
        for competition in self.competitions:
            for team in competition.teams:
                if team_name in team.name:
                    possible_teams.append(team.name)
        return possible_teams

    def get_team_season(self, team_name):
        team_calendar = []
        for competition in self.competitions:
            for match in competition.matches:
                if team_name in match.teams:
                    team_calendar.append(dict(match=match.teams,
                                              time=match.datetime))
        return team_calendar


class Competition(object):
    def __init__(self, footy_instance, location, url, name):
        self.logger = logging.getLogger('{base}.{suffix}'.format(
            base=LOGGER_BASENAME, suffix=self.__class__.__name__))
        self.session = footy_instance.session
        self._populate(location, url, name)
        self._teams = []
        self._matches = []
        self._calendar = ''

    def _populate(self, location, url, name):
        try:
            self.location = location
            self.url = url
            self.name = name.encode('utf-8')
        except KeyError:
            self.logger.exception("Got an exception in Competition")

    @property
    def teams(self):
        if not self._teams:
            team_page = self.session.get(self.url)
            soup = Bfs(team_page.text, "html.parser")
            standings = soup.find_all('table',
                                      {'class': 'leaguemanager standingstable'})
            for teams in standings:
                for row in teams.find_all('tr', {'class': ('alternate', '')}):
                    self._teams.append(Team(self, self.url, row))
        return self._teams

    @property
    def matches(self):
        if not self._matches:
            team_page = self.session.get(self.url)
            soup = Bfs(team_page.text, "html.parser")
            match_tables = soup.find_all('table',
                                         {'class': 'leaguemanager matchtable'})
            for match_table in match_tables:
                division = match_table.attrs['title']
                self._matches.extend([Match(row, division)
                                     for row in match_table.find_all('tr',
                                                                     {'class': ('alternate', '')})])
        return self._matches

    @property
    def calendar(self):
        if not self._calendar:
            for team in self.teams:
                self.logger.debug(team.calendar)
                self._calendar += team.calendar
        return self._calendar


class Team(object):
    def __init__(self, footy_instance, competition_page, info):
        self.logger = logging.getLogger('{base}.{suffix}'.format(
            base=LOGGER_BASENAME, suffix=self.__class__.__name__))
        self.session = footy_instance.session
        self.url = competition_page
        self._populate(info)
        self._matches = []
        self._calendar = ''

    def _populate(self, info):
        try:
            self.position = info.contents[1].text
            self.name = info.contents[5].text.encode('utf-8')
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
        if not self._matches:
            team_page = self.session.get(self.url)
            soup = Bfs(team_page.text, "html.parser")
            match_tables = soup.find_all('table',
                                         {'class': 'leaguemanager matchtable'})
            for match_table in match_tables:
                division = match_table.attrs['title']
                self._matches.extend([Match(row, division)
                                     for row in match_table.find_all('tr',
                                                                     {'class': ('alternate', '')})])
        return self._matches

    @property
    def calendar(self):
        if not self._calendar:
            for match in self.matches:
                self.logger.debug(match)
                self._calendar += match.calendar
        return self._calendar


class Match(object):
    def __init__(self, info, division=None):
        self.logger = logging.getLogger('{base}.{suffix}'.format(
            base=LOGGER_BASENAME, suffix=self.__class__.__name__))
        self._populate(info, division)
        self._calendar = ''

    def _populate(self, info, division):
        try:
            self.date = info.find('td', {'class': 'date1'}).text
            self.time = info.find('td', {'class': 'time'}).text
            self.location = info.find('td', {'class': 'location'}).text
            self.teams = info.find('td', {'class': 'match'}).text.encode('utf-8')
            self.score = info.find('td', {'class': 'score'}).text
            self.referee = info.find('td', {'class': 'ref'}).text
            self.motm = info.find('td', {'class': 'man'}).text
            self.datetime = self.__string_to_datetime(self.date, self.time)
            self.division = division or ''
        except KeyError:
            self.logger.exception("Got an exception on Matches.")

    @property
    def calendar(self):
        if not self._calendar:
            cal = FootyCalendar(self.datetime, self.teams, self.location)
            self._calendar = cal.generate()
            self.logger.debug(self._calendar)
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


class FootyCalendar(object):
    def __init__(self, datetime, teams, location):
        self.logger = logging.getLogger('{base}.{suffix}'.format(
            base=LOGGER_BASENAME, suffix=self.__class__.__name__))
        self.timezone = 'Europe/Amsterdam'
        self.calendar = Calendar()
        self.datetime = datetime
        self.teams = teams
        self.location = location

    def generate(self):
        event = Event(duration=timedelta(hours=1))
        try:
            event.begin = pytz.timezone(self.timezone).localize(self.datetime)
        except AttributeError:
            self.logger.exception('{} not valid datetime'.format(self.datetime))
        try:
            # ics module escapes strings. Needs decoding.
            event.name = self.teams.decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            self.logger.exception('Unicode Error. '
                                  'Got {event} {type}'.format(
                                                      event=event.name,
                                                      type=type(event.name)))
            event.name = self.teams
        except AttributeError:
            self.logger.exception("Got an exception in calendar")

        self.calendar.events.append(event)
        self.logger.debug(str(self.calendar))
        return str(self.calendar)

