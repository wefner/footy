#!/usr/bin/env python
# -*- coding: utf-8 -*-
# File: footylib.py

"""footylib"""

import logging
from requests import Session
from dateparser import parse
from bs4 import BeautifulSoup as Bfs
from datetime import timedelta
from icalendar import Calendar, Event, vText


LOGGER_BASENAME = '''footylib'''
LOGGER = logging.getLogger(LOGGER_BASENAME)
LOGGER.setLevel(logging.DEBUG)
LOGGER.addHandler(logging.NullHandler())


class Footy(object):
    """
    Main Footy class

    An object that can retrieve competitions from Footy.eu
    or get a team directly.
    """

    def __init__(self):
        self.logger = logging.getLogger('{base}.{suffix}'.format(
            base=LOGGER_BASENAME, suffix=self.__class__.__name__))
        self._site = "http://www.footy.eu/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        self.session = Session()
        self.session.headers.update(headers)
        self._front_page = None
        self._competitions = []
        self._urls = set()

    @property
    def __front_page(self):
        """
        Gets footy.eu index and parses it in HTML for Beautiful Sop.

        :return: footy front page as BFS object
        """
        if not self._front_page:
            page = self.session.get(self._site)
            try:
                self._front_page = Bfs(page.text,'html.parser')
            except Bfs.HTMLParser.HTMLParseError:
                self.logger.exception("Error while parsing Footy front page")
        return self._front_page

    @property
    def competitions(self):
        """
        It retrieves location, URL and name for every competition found in the front page.

        :return: list of Competition objects
        """
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
                    if url not in self._urls:
                        name = competition.text
                        self._competitions.append(Competition(self,
                                                              location,
                                                              url,
                                                              name))
                        self._urls.add(url)
        return self._competitions

    def get_team(self, team_name):
        """
        Gets a team object from input name. It stops iterating when found.

        :param team_name: string of team name to look for.
        :return: Team object
        """
        team = None
        for competition in self.competitions:
            team = next((team for team in competition.teams
                         if team.name == team_name), None)
            if team:
                break
        return team

    def search_team(self, team_name):
        """
        Looks for a team by a given name.

        :param team_name: string of team name to look for.
        :return: list of Team object(s)
        """
        possible_teams = []
        for competition in self.competitions:
            for team in competition.teams:
                if team_name in team.name:
                    possible_teams.append(team)
        return possible_teams


class Competition(object):
    """
    Gets competitions from location, url and name.

    Object that has all attributes for a competition

    """

    def __init__(self, footy_instance, location, url, name):
        self._logger = logging.getLogger('{base}.{suffix}'.format(
            base=LOGGER_BASENAME, suffix=self.__class__.__name__))
        self.session = footy_instance.session
        self._populate(location, url, name)
        self._teams = []
        self._matches = []
        self._divisions = None
        self._calendar = None
        self._soup = None

    def _populate(self, location, url, name):
        """
        Fills class variables that are passed from the main page
        """
        try:
            self.location = location
            self.url = url
            self.name = name.encode('utf-8').strip()
        except KeyError:
            self._logger.exception("Got an exception in Competition")

    @property
    def divisions(self):
        """
        Gets all divisions that are in a competition.
        :return: set of unique divisions
        """
        if not self._divisions:
            self._divisions = set([match.division for match in self.matches])
        return self._divisions

    @property
    def teams(self):
        """
        Gets all teams that are in a competition.

        The teams are retrieved from each row in the standings table
        :return: list of Team objects
        """
        if not self._teams:
            standings = self._get_table('standingstable')
            for teams in standings:
                for row in teams.find_all('tr', {'class': ('alternate', '')}):
                    self._teams.append(Team(self, row))
        return self._teams

    @property
    def matches(self):
        """
        Gets all matches that are in a competition

        The matches are retrieved from all the Rounds
        :return: list of Match objects
        """
        if not self._matches:
            match_tables = self._get_table('matchtable')
            for match_table in match_tables:
                for row in match_table.find_all('tr',
                                                {'class': ('alternate', '')}):
                    division = match_table.attrs['title']
                    self._matches.append(Match(self,
                                               row,
                                               self.location,
                                               division))
        return self._matches

    def _get_table(self, class_attribute):
        """
        Method that parses the HTML from a 'leaguemanager' class in a table.

        This is used for teams and matches
        :param class_attribute: name of the table class attribute
        :return: BFS object
        """
        if not self._soup:
            competition_page = self.session.get(self.url)
            self._soup = Bfs(competition_page.text, "html.parser")
        return self._soup.find_all('table',
                                   {'class': 'leaguemanager {}'.format(class_attribute)})

    @property
    def calendar(self):
        """
        Generates a RFC2445 (iCalendar) for all the matches
        in a competition
        :return: Calendar string
        """
        if not self._calendar:
            self._calendar = Calendar()
            for team in self.teams:
                for event in team.events:
                    self._calendar.add_component(event)
        return self._calendar


class Team(object):
    """
    Object that has all team attributes.

    The information is sent from Competition where it
    has the visibility of the Standings table. It parses
    every row and it gets the data per each column.
    """

    def __init__(self, competition_instance, info):
        self.logger = logging.getLogger('{base}.{suffix}'.format(
            base=LOGGER_BASENAME, suffix=self.__class__.__name__))
        self.session = competition_instance.session
        self.competition = competition_instance
        self.url = competition_instance.url
        self._populate(info)
        self._calendar = None
        self._division = None

    def _populate(self, info):
        """
        It gets the row from standingstable for the requested Team
        and then it gets the index accordingly to every column.
        :param info: BFS object
        """
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
    def division(self):
        """
        Gets the division for a team from the latest Match in the division.
        In order to get it, the Team has to be in a Match.
        :return: division attribute
        """
        if not self._division:
            try:
                self._division = self.matches[-1].division
            except IndexError:
                self.logger.warn("Can't get the division for {team}. "
                                 "Doesn't have match".format(team=self.name))
        return self._division

    @property
    def matches(self):
        """
        Gets all matches for a Team
        :return: list of Match objects
        """
        return [match for match in self.competition.matches
                if self.name in match.title]

    @property
    def events(self):
        """
        :return: list of Event objects for all the matches
                 that a Team is part of
        """
        return [match.event for match in self.matches]

    @property
    def calendar(self):
        """
        Generates a RFC2445 (iCalendar) for all the Events that a Team has
        :return: Calendar string
        """
        if not self._calendar:
            self._calendar = Calendar()
            for event in self.events:
                self._calendar.add_component(event)
        return self._calendar


class Match(object):
    """
    Object that has all attributes for a given match

    The information is sent from Competition where it
    has the visibility of the Matches table. It parses
    every row and it gets the data per each column.
    """
    def __init__(self, competition_instance, info, location, division=None):
        self.logger = logging.getLogger('{base}.{suffix}'.format(
            base=LOGGER_BASENAME, suffix=self.__class__.__name__))
        self._populate(info, location, division)
        self.competitions = competition_instance
        self._calendar = None
        self._visiting_team = None
        self._visiting_team_goals = None
        self._home_team = None
        self._home_team_goals = None
        self.event = FootyEvent(self.datetime, self.title, location)

    def _populate(self, info, location, division):
        """
        It gets the row from matchtable for the requested Team
        and then it gets the value accordingly to every column.
        :param info: BFS object
        """
        try:
            self._date = info.find('td', {'class': 'date1'}).text
            self._time = info.find('td', {'class': 'time'}).text
            self.location = location
            self.title = self.__normalize_title(info.find('td', {'class': 'match'}).text)
            self.score = info.find('td', {'class': 'score'}).text
            self.referee = info.find('td', {'class': 'ref'}).text
            self.motm = info.find('td', {'class': 'man'}).text
            self.datetime = self.__string_to_datetime(self._date, self._time)
            self.division = division or ''
        except KeyError:
            self.logger.exception("Got an exception on Matches.")

    @staticmethod
    def __normalize_title(title):
        """
        Replaces \xe2\x80\x93 character to an ASCII dash
        :param title: match title with Unicode character
        :return: ASCII match title
        """
        encoded_title = title.encode('utf-8')
        normalized_title = encoded_title.replace('–', '-').strip()
        return normalized_title

    @property
    def visiting_team(self):
        """
        :return: Visiting team name in a match
        """
        if not self._visiting_team:
            self._visiting_team = self._get_team(home_team=False)
        return self._visiting_team

    @property
    def home_team(self):
        """
        :return: Home team name in a match
        """
        if not self._home_team:
            self._home_team = self._get_team()
        return self._home_team

    def _get_team(self, home_team=True):
        """
        Method that gets the teams in a match and
        it determines whether it is the home or visiting one.
        - True: Home team
        - False: Visiting team
        :param home_team: Boolean
        :return: home/visiting team name
        """
        home, visiting = self.title.split(' - ')
        match = home.strip()
        if not home_team:
            match = visiting.strip()
        team = next((team for team in self.competitions.teams
                     if team.name == match), None)
        return team

    def _get_match_goals(self, home_team_goals=True):
        """
        Method that gets the score in a match and
        it determines whether result is for the home or
        visiting team.
        - True: Home team goals
        - False: Visiting team goals
        :param home_team_goals: Boolean
        :return: home/visiting goals for a team
        """
        try:
            # Match not started (-:-)
            home, visiting = self.score.split(':')
        except ValueError:
            # Played match (0 - 0)
            home, visiting = self.score.split('-')
        score = home.strip()
        if not home_team_goals:
            score = visiting.strip()
        return score

    @property
    def home_team_goals(self):
        """
        :return: home team goals in a match
        """
        if not self._home_team_goals:
            self._home_team_goals = self._get_match_goals()
        return self._home_team_goals

    @property
    def visiting_team_goals(self):
        """
        :return: visiting team goals in a match
        """
        if not self._visiting_team_goals:
            self._visiting_team_goals = self._get_match_goals(
                                                        home_team_goals=False)
        return self._visiting_team_goals

    @property
    def calendar(self):
        """
        Generates a RFC2445 (iCalendar) for a match
        :return: Calendar string
        """
        if not self._calendar:
            self._calendar = Calendar()
            self._calendar.add_component(self.event)
        return self._calendar

    @staticmethod
    def __string_to_datetime(date, time):
        """
        It joins a Dutch date string and a time string for a match and it
        converts it to a datetime object. 'Datetime parser' module
        automatically detects datetime string whether it's incomplete or not.
        :param date: Dutch date (maart 7, 2017)
        :param time: 12h time (6:30) + pm/am
        :return: datetime object
        """
        dutch_datetime = '{} {}'.format(date.capitalize(), time).strip()
        datetime_object = None
        try:
            datetime_object = parse(dutch_datetime,
                                    settings={'TIMEZONE': 'Europe/Amsterdam'})
        except AttributeError:
            LOGGER.exception("Couldn't parse this datetime.")
        return datetime_object


class FootyEvent(object):
    """
    Object that creates an Event for a match
    """

    def __new__(cls, match_date, match, location):
        """
        :param match_date: datetime object
        :param match: match title
        :param location: location field for the match
        :return: event object
        """
        event = Event()
        try:
            event.add('dtstart', match_date)
            event.add('summary', match)
            event.add('duration', timedelta(hours=1))
            event.add('location', vText(location))
        except AttributeError:
            LOGGER.exception('{} not valid datetime'.format(match_date))
        return event
