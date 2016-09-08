#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import logging
import re
import pytz
from bs4 import BeautifulSoup as bfs
from datetime import datetime
from ics import Calendar, Event

LOGGER_BASENAME = '''footy'''
LOGGER = logging.getLogger(LOGGER_BASENAME)
LOGGER.setLevel(logging.DEBUG)
LOGGER.addHandler(logging.NullHandler())


class Footy(object):
    def __init__(self, division, day, team):
        self.logger = logging.getLogger('{base}.{suffix}'.format(
            base=LOGGER_BASENAME, suffix=self.__class__.__name__))
        self.site = 'http://www.footy.eu'
        self.division = self.__get_match_plan(division)
        self.day = self.__get_day_page(day)
        self.team = team
        self.season = []
        self._get_match_page()

    def _get_match_page(self):
        headers = {'User-Agent': 'Mozilla/5.0',
                   'Referer': 'http://www.footy.eu/en/'}
        url = "{site}/{day}".format(site=self.site,
                                    day=self.day)
        try:
            match_page = requests.get(url, headers=headers)
            return self._parse_match_table(match_page)
        except requests.RequestException as e:
            self.logger.error('Connection error {}'.format(str(e)))

    def _parse_match_table(self, match_page):
        soup = bfs(match_page.text, "html.parser")

        matchtable = soup.findAll('table', {'title': self.division})

        soup_dates = [match.find('td', {'class': 'date1'}) for match in matchtable]
        soup_times = [match.findAll('td', {'class': 'time'}) for match in matchtable]
        soup_teams = [match.findAll('td', {'class': 'match'}) for match in matchtable]

        dates = [date.children.next() for date in soup_dates]
        time_set = [[s.text for s in times] for times in soup_times]
        team_set = [[s.text for s in teams] for teams in soup_teams]

        return self.get_calendar_by_team(dates, time_set, team_set)

    def get_calendar_by_team(self, dates, time_set, team_set):
        for date, times, teams in zip(dates, time_set, team_set):
            for time, team in zip(times, teams):
                if self.team in team:
                    season_matches = {}
                    team = team.encode('utf-8').strip()
                    match_date = "{date} {time}".format(date=self.__convert_dutch_month_to_english(date),
                                                        time=time.upper())
                    date_obj = datetime.strptime(match_date, '%B %d, %Y %I:%M %p')
                    amsterdam = pytz.timezone('Europe/Amsterdam')
                    date_ams = amsterdam.localize(date_obj)
                    season_matches['date'] = date_ams
                    season_matches['match'] = team.replace('\xe2\x80\x93', '-')
                    self.season.append(season_matches)

        return self.season

    @staticmethod
    def __convert_dutch_month_to_english(month):
        months = {"oktober": "October",
                  "augustus": "August",
                  "september": "September",
                  "november": "November"}

        months = dict((re.escape(k), v) for k, v in months.iteritems())
        pattern = re.compile("|".join(months.keys()))
        translated_month = pattern.sub(lambda m: months[re.escape(m.group(0))], month)

        return str(translated_month)

    @staticmethod
    def __get_match_plan(div):
        division_table = {'div2': 'Match Plan Wednesday 6v6 Div 2 Autumn 2016',
                          'div1': 'Match Plan Wednesday 6v6 Div 1 Autumn 2016'}
        return division_table[div]

    @staticmethod
    def __get_day_page(day):
        match_table = {'6mon': 'footy-park-mandaag-6v6',
                       '6tue': 'footy-park-tuesday-6v6',
                       '6wed': 'footy-park-woensdag-6v6',
                       '6thu': 'footy-park-donderdag-6v6'}
        return match_table[day]


class FootyCalendar(object):
    def __init__(self, season):
        self.season = season
        self.c = Calendar()

    def generate_calendar_file(self):
        for match in self.season:
            e = Event(duration={"hours": 1})
            e.name = match['match']
            e.begin = match['date']
            self.c.events.append(e)

        with open('/Users/oriolfb/season.ics', 'w') as file:
            file.writelines(self.c)
        return True

if __name__ == '__main__':
    logging.basicConfig(level='DEBUG')
    footy = Footy('div2', '6wed', 'Hangover')
    calendar = FootyCalendar(footy.season).generate_calendar_file()

