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
from collections import namedtuple


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
        self._site = 'https://www.footy.eu/schemas-standen/'
        headers = {'User-Agent': 'Mozilla/5.0'}
        self.session = Session()
        self.session.headers.update(headers)
        self._front_page = None
        self._competitions = []
        self._urls = set()

    @property
    def __league_page(self):
        """
        Gets Footy.eu competitions page and scrapes its HTML

        :return: footy front page as BFS object
        """
        if not self._front_page:
            page = self.session.get(self._site)
            try:
                self._front_page = Bfs(page.text, 'html.parser')
            except Bfs.HTMLParser.HTMLParseError:
                self.logger.exception("Error while parsing Footy front page")
        return self._front_page

    @property
    def competitions(self):
        """
        Gets all competition URLs from the league page

        :return: list of Competition objects
        """
        if not self._competitions:
            league_page = self.__league_page.find('div',
                                                  {'id': 'league-page'})
            competitions = league_page.find_all('ul', {'class': 'sub-menu'})
            for competition in competitions:
                for competition_url in competition.find_all({'a': 'href'}):
                    url = competition_url.attrs.get('href')
                    if url not in self._urls and '#' not in url:
                        self._competitions.append(Competition(self, url))
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

    def __init__(self, footy_instance, url):
        self._logger = logging.getLogger('{base}.{suffix}'.format(
            base=LOGGER_BASENAME, suffix=self.__class__.__name__))
        self.session = footy_instance.session
        self._populate(url)
        self._teams = []
        self._matches = []
        self._calendar = None
        self._soup = None

    def _populate(self, url):
        """
        Fills class variables that are passed from the main page
        """
        try:
            self.url = url
        except KeyError:
            self._logger.exception("Got an exception in Competition")

    @property
    def teams(self):
        """
        Gets all teams that are in a competition.

        The teams are retrieved from each row in the standings table
        :return: list of Team objects
        """
        if not self._teams:
            standings = self._get_table('banner')
            division = standings.h2.text
            for teams in standings.find_all('tr'):
                team = teams.find_all('td')
                if team:
                    self._teams.append(Team(self, team, division))
        return self._teams

    @property
    def matches(self):
        """
        Gets all matches that are in a competition

        The matches are retrieved from all the Rounds
        :return: list of Match objects
        """
        if not self._matches:
            match_tables = self._get_table('previous-matches')
            for matches in match_tables.find_all('tr'):
                match = matches.find_all('td')
                if match:
                    self._matches.append(Match(self, match))
        return self._matches

    def _get_table(self, section_attr):
        """
        Gets according section tag

        This is used for teams and matches
        :param section_attr: name of the section id attribute
        :return: BFS object
        """
        if not self._soup:
            competition_page = self.session.get(self.url)
            self._soup = Bfs(competition_page.text, "html.parser")
        return self._soup.find('section', {'id': '{}'.format(section_attr)})

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
    Row = namedtuple('Row', ['position',
                             'name',
                             'played_games',
                             'won_games',
                             'tie_games',
                             'lost_games',
                             'goals',
                             'diff',
                             'points'])

    def __init__(self, competition_instance, team_details, division):
        self.logger = logging.getLogger('{base}.{suffix}'.format(
            base=LOGGER_BASENAME, suffix=self.__class__.__name__))
        self.session = competition_instance.session
        self.competition = competition_instance
        self._populate(Team.Row(*[info.text for info in team_details]))
        self._calendar = None
        self.division = division

    def _populate(self, team_details):
        """
        It gets the row from standingstable for the requested Team
        and then it gets the index accordingly to every column.
        :param team_details: BFS object
        """
        try:
            self.position = team_details.position
            self.name = team_details.name.encode('utf-8').strip()
            self.played_games = team_details.played_games
            self.won_games = team_details.won_games
            self.tie_games = team_details.tie_games
            self.lost_games = team_details.lost_games
            self.goals = team_details.goals
            self.diff = team_details.diff
            self.points = team_details.points
        except AttributeError:
            self.logger.exception("Got an exception while populating a team")

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
    Row = namedtuple('Row', ['datetime',
                             'location',
                             'title',
                             'score',
                             'referee',
                             'motm'])

    def __init__(self, competition_instance, match_details):
        self.logger = logging.getLogger('{base}.{suffix}'.format(
            base=LOGGER_BASENAME, suffix=self.__class__.__name__))
        self._populate(Match.Row(*[info.text for info in match_details]))
        self.competitions = competition_instance
        self._calendar = None
        self._visiting_team = None
        self._visiting_team_goals = None
        self._home_team = None
        self._home_team_goals = None
        self.event = FootyEvent(self.datetime, self.title, self.location)

    def _populate(self, match_details):
        """
        It gets the row from matchtable for the requested Team
        and then it gets the value accordingly to every column.

        :param info: BFS object
        """
        try:
            self.datetime = self.__string_to_datetime(match_details.datetime)
            self.location = match_details.location
            self.title = match_details.title
            self.score = match_details.score
            self.referee = match_details.referee
            self.motm = match_details.motm
        except AttributeError:
            self.logger.exception("Got an exception while populating a match")

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
    def __string_to_datetime(datetime_string):
        """
        Converts date and time string into a datetime object
        :param datetime_string: 05.09.2017 21:30
        :return: datetime object
        """
        datetime_object = None
        try:
            datetime_object = parse(date_string=datetime_string,
                                    date_formats=['%d.%m.%Y %H:%M'],
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
            event.add('duration', timedelta(minutes=50))
            event.add('location', vText(location))
        except AttributeError:
            LOGGER.exception('{} not valid datetime'.format(match_date))
        return event
