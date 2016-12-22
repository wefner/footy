#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
import pytz
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
        soup = Bfs(page.text, 'html.parser')
        return soup

    def get_competitions(self):
        competitions = []
        locations = self.front_page.find_all('div',
                                             {'class': 'fusion-panel panel-default'})
        for location_data in locations:
            location = location_data.find('div',
                                          {'class': 'fusion-toggle-heading'}
                                          ).string
            for competition in location_data.find_all('a',
                                                      {'class': 'footycombut'}):
                url = competition.attrs['href']
                name = competition.string
                competitions.append(Competition(self, location, url, name))
        return competitions


class Competition(object):
    def __init__(self, footy_instance, location, url, name):
        self.logger = logging.getLogger('{base}.{suffix}'.format(
            base=LOGGER_BASENAME, suffix=self.__class__.__name__))
        self.session = footy_instance.session
        try:
            self.location = location
            self.url = url
            self.name = name
        except KeyError as e:
            self.logger.error(e)

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
        match_table = soup.find_all('table',
                                    {'class': 'leaguemanager matchtable'})
        matches_per_day = []
        for matches in match_table:
            division = matches.attrs['title']
            # self.logger.debug(matches)
            for match in matches.find_all('tr', {'class': ('alternate', '')}):
                matches_per_day.append(division)
                for date in match.find_all('td', {'class': 'date1'}):
                    matches_per_day.append(date.text)
                for time in match.find_all('td', {'class': 'time'}):
                    matches_per_day.append(time.text)
                for location in match.find_all('td', {'class': 'location'}):
                    matches_per_day.append(location.text)
                for match in match.find_all('td', {'class': 'match'}):
                    matches_per_day.append(match.text)
                for score in match.find_all('td', {'class': 'score'}):
                    matches_per_day.append(score.text)
                for ref in match.find_all('td', {'class': 'ref'}):
                    matches_per_day.append(ref.text)
                for motm in match.find_all('td', {'class': 'man'}):
                    matches_per_day.append(motm.text)
            return [Match(match) for match in matches_per_day]


class Team(object):
    def __init__(self, info):
        self.logger = logging.getLogger('{base}.{suffix}'.format(
            base=LOGGER_BASENAME, suffix=self.__class__.__name__))
        try:
            self.position = info.contents[1].text
            self.team_name = info.contents[5].text
            self.played_games = info.contents[7].text
            self.won_games = info.contents[9].text
            self.tie_games = info.contents[11].text
            self.lost_games = info.contents[13].text
            self.goals = info.contents[15].text
            self.diff = info.contents[16].text
            self.points = info.contents[18].text
            self.division = None
        except KeyError as e:
            self.logger.error(e)

    def get_team_division(self):
        pass


class Match(object):
    def __init__(self, info, division=None):
        self.logger = logging.getLogger('{base}.{suffix}'.format(
            base=LOGGER_BASENAME, suffix=self.__class__.__name__))
        self.logger.debug(info)
        try:
            self.division = division
            self.info = info
        except KeyError as e:
            self.logger.error(e)


if __name__ == '__main__':
    logger = logging.basicConfig(level="DEBUG")
    f = Footy()
    competitions = f.get_competitions()
    for c in competitions:
        print c.name
        for match in c.get_teams():
            print '\t', 'Position: {}'.format(match.position),
            print '\t', 'Team Name: {}'.format(match.team_name)
        try:
            for t in c.get_matches():
                print t.info
        except Exception as e:
            print e
