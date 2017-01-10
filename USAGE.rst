===========
Version 1.0
===========

.. code-block:: python

    >>> from footylib import Footy, FootyCalendar
    # division, game type, team
    >>> footy = Footy('div2', '6tue', 'Hangover')
    >>> calendar = FootyCalendar(footy.season)
    >>> calendar.generate_calendar_file('/your/path/season.ics')
    True


===========
Version 2.0
===========

Instantiate Footy
=================
.. code-block:: python

    >>> from footylib import Footy
    >>> footy = Footy()

Get a competition object
========================

.. code-block:: python

    >>> competitions = footy.competitions

Search for teams
================
.. code-block:: python

    >>> team = footy.search_team("Hangover")
    >>> team
    [<footylib.footylib.Team object at 0x10dffcad0>, <footylib.footylib.Team object at 0x10e8f7250>]

Get a team object
=================
.. code-block:: python

    >>> team = footy.get_team("Hangover 69")

Generate calendar season for a team
===================================
.. code-block:: python

    >>> team.calendar

Exporting calendar to a file
============================
.. code-block:: python

    with open('calendar.ics', 'w') as ics:
        ics.writelines(team.calendar.to_ical())

Get all attributes
==================

.. code-block:: python

    >>> for competition in competitions:
            print "Standings for {}".format(competition.name)
            for team in competition.teams:
                print '\t', 'Team: {}'.format(team.name)
                print '\t\t', 'Position: {}'.format(team.position)
                print '\t\t', 'Played games {}'.format(team.played_games)
                print '\t\t', 'Won games {}'.format(team.won_games)
                print '\t\t', 'Tie games {}'.format(team.tie_games)
                print '\t\t', 'Lost games {}'.format(team.lost_games)
                print '\t\t', 'Goals {}'.format(team.goals)
                print '\t\t', 'Division {}'.format(team.division)
                print '\t\t', 'Diff {}'.format(team.diff)
                print '\t\t', 'Points {}'.format(team.points)
            print "Calendar for {}".format(competition.name)
            for match in competition.matches:
                print '\t', 'Location: {}'.format(match.location)
                print '\t', 'Name: {}'.format(match.title)
                print '\t', 'Score: {}'.format(match.score)
                print '\t', 'Referee: {}'.format(match.referee)
                print '\t', 'Division: {}'.format(match.division)
                print '\t', 'Date: {}'.format(match.datetime)
                print '\t', 'MOTM: {}'.format(match.motm)
