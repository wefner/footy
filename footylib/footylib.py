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
        page = self.session.get(self.site, headers=self.headers)
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
        self.teams = self.get_teams()
        try:
            self.location = location
            self.url = url
            self.name = name
        except KeyError as e:
            self.logger.error(e)

    def get_teams(self):
        self.logger.debug(self.url)
        team_page = self.session.get(self.url)
        soup = Bfs(team_page.text, "html.parser")
        standings = soup.find_all('table',
                                  {'class': 'leaguemanager standingstable'})
        # t_headers = [t.string for t in standing_table.find_all('th')]
        info = {}
        team = []
        for teams in standings:
            for row in teams.find_all('tr', {'class': ('alternate', '')}):
                info['position'] = row.contents[1].text
                info['team_name'] = row.contents[5].text
                info['played_games'] = row.contents[7].text
                info['won_games'] = row.contents[9].text
                info['tie_games'] = row.contents[11].text
                info['lost_games'] = row.contents[13].text
                info['goals'] = row.contents[15].text
                info['diff'] = row.contents[16].text
                info['points'] = row.contents[18].text
                team.append(Team(info))
            self.logger.debug(team)
        return team


class Team(object):
    def __init__(self, info):
        self.logger = logging.getLogger('{base}.{suffix}'.format(
            base=LOGGER_BASENAME, suffix=self.__class__.__name__))
        self.logger.debug(info)
        try:
            self.position = info.get('position')
            self.team_name = info.get('name')
            self.played_games = info.get('played_games')
            self.won_games = info.get('won_games')
            self.tie_games = info.get('tie_games')
            self.lost_games = info.get('lost_games')
            self.goals = info.get('goals')
            self.diff = info.get('diff')
            self.points = info.get('points')
        except KeyError as e:
            self.logger.error(e)


if __name__ == '__main__':
    logger = logging.basicConfig(level="DEBUG")
    f = Footy()
    competitions = f.get_competitions()
    # teams = [c.teams for c in competitions]

