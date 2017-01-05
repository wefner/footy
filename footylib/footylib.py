#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytz
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
        self._front_page = None
        self._competitions = []

    @property
    def front_page(self):
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
                    self._competitions.append(Competition(self,
                                                          location,
                                                          url,
                                                          name))
        return self._competitions

    def get_team(self, team):
        for competition in self.competitions:
            for teams in competition.teams:
                if team == teams.name:
                    self.logger.info("Team {} found".format(team))
                    return teams

    def search_team(self, team):
        possible_teams = []
        for competition in self.competitions:
            for teams in competition.teams:
                if team in teams.name:
                    possible_teams.append(teams.name)
        return "Found team(s): {}".format(possible_teams)

    def get_team_season(self, team):
        team_calendar = []
        for competition in self.competitions:
            for match in competition.matches:
                if team in match.teams:
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
                    self._teams.append(Team(row))
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


class Team(object):
    def __init__(self, info):
        self.logger = logging.getLogger('{base}.{suffix}'.format(
            base=LOGGER_BASENAME, suffix=self.__class__.__name__))
        self._populate(info)

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
            self.teams = info.find('td', {'class': 'match'}).text.encode('utf-8')
            self.score = info.find('td', {'class': 'score'}).text
            self.referee = info.find('td', {'class': 'ref'}).text
            self.motm = info.find('td', {'class': 'man'}).text
            self.datetime = self.__string_to_datetime(self.date, self.time)
            self.division = division or ''
        except KeyError:
            self.logger.exception("Got an exception on Matches.")

    def __string_to_datetime(self, date, time):
        dutch_datetime = '{} {}'.format(date, time).split()
        english_datetime = self.__dutch_to_english_reference(dutch_datetime[0])
        dutch_datetime[0] = english_datetime
        english_datetime = " ".join(dutch_datetime)
        try:
            datetime_object = datetime.strptime(english_datetime,
                                                '%B %d, %Y %I:%M %p')
            return datetime_object
        except ValueError:
            self.logger.exception("Couldn't parse this datetime.")

    def __dutch_to_english_reference(self, dutch_month):
        """
        Replace Dutch month for English name. Used for datetime objects
        :param dutch_month: dutch month string
        :return: month in English
        """
        months = {"januari": "January",
                  "februari": "February",
                  "maart": "March",
                  "april": "April",
                  "mei": "May",
                  "juni": "June",
                  "juli": "July",
                  "augustus": "August",
                  "september": "September",
                  "oktober": "October",
                  "november": "November",
                  "december": "December"}
        return months[dutch_month]


class FootyCalendar(object):
    def __init__(self, season):
        self.logger = logging.getLogger('{base}.{suffix}'.format(
            base=LOGGER_BASENAME, suffix=self.__class__.__name__))
        self.timezone = 'Europe/Amsterdam'
        self.calendar = Calendar()
        self.season = season

    def generate_calendar(self):
        for match in self.season:
            event = Event(duration=timedelta(hours=1))
            event.begin = pytz.timezone(self.timezone).localize(
                                                match.get('time'))
            try:
                # ics module escapes strings. Needs decoding.
                event.name = match.get('match').decode('utf-8')
            except (UnicodeEncodeError, UnicodeDecodeError):
                event.name = match.get('match')
                self.logger.exception('Unicode Error. '
                                      'Got {event} {type}'.format(
                                                          event=event.name,
                                                          type=type(event.name)))
            except AttributeError:
                self.logger.exception("Got an exception in calendar")

            self.calendar.events.append(event)
        return str(self.calendar)

