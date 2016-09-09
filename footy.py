#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import logging
import re
import pytz
from footyExceptions import *
from bs4 import BeautifulSoup as bfs
from datetime import datetime, timedelta
from ics import Calendar, Event

LOGGER_BASENAME = '''footy'''
LOGGER = logging.getLogger(LOGGER_BASENAME)
LOGGER.setLevel(logging.DEBUG)
LOGGER.addHandler(logging.NullHandler())


class Footy(object):
    def __init__(self, division, day, team):
        """
        Instantiates Footy object.

        :param division: where the team is playing in
        :param day: kind of league and day. See 'match_table' below
        :param team: the team to look for matches
        """
        self.logger = logging.getLogger('{base}.{suffix}'.format(
            base=LOGGER_BASENAME, suffix=self.__class__.__name__))
        self.site = 'http://www.footy.eu'
        self.division = self.__get_match_plan(division)
        self.day = self.__get_day_page(day)
        self.team = team
        self.timezone = 'Europe/Amsterdam'
        self.season = []
        self._get_match_page()

    def _get_match_page(self):
        """
        Collect site data of matches and results.

        Needs headers because website always redirects
        to mainpage if not set.

        If succeeds, will parse match table.

        :return: bool
        """
        headers = {'User-Agent': 'Mozilla/5.0',
                   'Referer': self.site}
        url = "{site}/{day}".format(site=self.site,
                                    day=self.day)
        try:
            match_page = requests.get(url, headers=headers)
            if match_page.ok:
                self._parse_match_table(match_page)
                return True
        except requests.RequestException as e:
            self.logger.error("Connection error", (str(e)))
            return False

    def _parse_match_table(self, match_page):
        """
        Get the interesting fields of the results table

        :param match_page: the HTML of the results page
        :return: False if failed. If succeeds will get the season's calendar
        """
        matchtable = None
        try:
            soup = bfs(match_page.text, "html.parser")
            matchtable = soup.findAll('table', {'title': self.division})
        except bfs.HTMLParser.HTMLParseError as e:
            self.logger.error("Error parsing the page", (str(e)))

        soup_dates = None
        soup_times = None
        soup_teams = None
        try:
            soup_dates = [match.find('td', {'class': 'date1'}) for match in matchtable]
        except AttributeError:
            self.logger.info("Couldn't find the dates of the results")
        try:
            soup_times = [match.findAll('td', {'class': 'time'}) for match in matchtable]
        except AttributeError:
            self.logger.info("Couldn't find the times of the results")
        try:
            soup_teams = [match.findAll('td', {'class': 'match'}) for match in matchtable]
        except AttributeError:
            self.logger.info("Couldn't find results of the teams")

        result = False
        try:
            dates = [date.children.next() for date in soup_dates]
            time_set = [[time.text for time in times] for times in soup_times]
            team_set = [[team.text for team in teams] for teams in soup_teams]
            result = True
            return self.get_calendar_by_team(dates, time_set, team_set)
        except TypeError as e:
            self.logger.error("Error while getting text information from results", str(e))
            return result

    def get_calendar_by_team(self, dates, time_set, team_set):
        """
        Will get the calendar of the season for the specified team

        List of dictionaries of the form:
                [{'date': date_object, 'match': 'Team A - Team B'}, {...}]

        :param dates: list of matches dates
        :param time_set: list of matches times
        :param team_set: list of matches teams
        :return: list of dictionaries
        """
        for date, times, teams in zip(dates, time_set, team_set):
            for time, team in zip(times, teams):
                if self.team in team:
                    season_matches = {}
                    team = team.encode('utf-8').strip()
                    match_date = "{date} {time}".format(date=self.__convert_dutch_month_to_english(date),
                                                        time=time.upper())
                    season_matches['date'] = self.__add_timezone_to_date(match_date)
                    season_matches['match'] = team.replace('\xe2\x80\x93', '-')
                    self.season.append(season_matches)
        return self.season

    def __add_timezone_to_date(self, match_date):
        """
        Convert string date to datetime object

        If wrong timezone, pytz module will raise an Exception

        :param match_date: string date
        :return: datetime object
        """
        datetime_object = datetime.strptime(match_date, '%B %d, %Y %I:%M %p')
        timezone_object = pytz.timezone(self.timezone)
        date_with_timezone = timezone_object.localize(datetime_object)
        return date_with_timezone

    @staticmethod
    def __convert_dutch_month_to_english(dutch_date):
        """
        Replace Dutch month for English name. Used for datetime objects

        :param dutch_date: '<Month> <Day>, <Year>
        :return: month in English
        """
        months = {"oktober": "October",
                  "augustus": "August",
                  "september": "September",
                  "november": "November"}
        pattern = re.compile("|".join(months.keys()))
        try:
            english_date = pattern.sub(lambda m: months[re.escape(m.group(0))], dutch_date)
            return str(english_date)
        except re.error as e:
            raise MonthTranslationError(e)

    @staticmethod
    def __get_match_plan(div):
        """
        Division where the team is playing in

        :param div: string
        :return: legacy name to look for at the website
        """
        division_table = {'div2': 'Match Plan Wednesday 6v6 Div 2 Autumn 2016',
                          'div1': 'Match Plan Wednesday 6v6 Div 1 Autumn 2016'}
        try:
            return division_table[div]
        except KeyError:
            raise ErrorGettingDivision

    @staticmethod
    def __get_day_page(day):
        """
        Type of Footy or league where the team is signed up for.

        :param day: string
        :return: legacy name of the results page from the website
        """
        match_table = {'6mon': 'footy-park-mandaag-6v6',
                       '6tue': 'footy-park-tuesday-6v6',
                       '6wed': 'footy-park-woensdag-6v6',
                       '6thu': 'footy-park-donderdag-6v6'}
        try:
            return match_table[day]
        except KeyError:
            raise ErrorGettingLeague


class FootyCalendar(object):
    def __init__(self, season):
        """
        Instantiates FootyCalendar object

        :param season: list of dictionaries from Footy object
        """
        self.season = season
        self.calendar = Calendar()

    def generate_calendar_file(self, path):
        """
        Season calendar for the specified team.

        Create the calendar file and save it to disk
        Alongside with the information collected. Match is 1h

        :param path: absolute path of the file to be saved in
        :return:
        """
        for match in self.season:
            event = Event(timedelta(hours=1))
            event.name = match['match']
            event.begin = match['date']
            self.calendar.events.append(event)

        with open(path, 'w') as ics_file:
            ics_file.writelines(self.calendar)
        return True

