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

    from footylib import Footy
    import logging

    logger = logging.basicConfig(level="DEBUG")

    f = Footy()

Get competition objects
=======================

.. code-block:: python

    competitions = f.get_competitions()

    for competition in competitions:
        print "Standings for {}".format(competition.name)
        for team in competition.teams:
            print '\t', 'Team: {}'.format(team.name)
            print '\t\t', 'Position: {}'.format(team.position)
            print '\t\t', 'Played games {}'.format(team.played_games)
            print '\t\t', 'Won games {}'.format(team.won_games)
            print '\t\t', 'Tie games {}'.format(team.tie_games)
            print '\t\t', 'Lost games {}'.format(team.lost_games)
            print '\t\t', 'Goals {}'.format(team.goals)
            print '\t\t', 'Diff {}'.format(team.diff)
            print '\t\t', 'Points {}'.format(team.points)
        try:
            print "Calendar for {}".format(competition.name)
            for match in competition.matches:
                print '\t', 'Location: {}'.format(match.location)
                print '\t', 'Name: {}'.format(match.teams)
                print '\t', 'Score: {}'.format(match.score)
                print '\t', 'Referee: {}'.format(match.referee)
                print '\t', 'Division: {}'.format(match.division)
                print '\t', 'Date: {}'.format(match.datetime)
                print '\t', 'MOTM: {}'.format(match.motm)
        except AttributeError:
            print "Got an error while getting matches"

Search for teams
================
.. code-block:: python

    team = f.search_team("Hangover")
    Found team(s): ['Hangover 96', 'Hangover 69']

Get a team object
=================
.. code-block:: python

    team = f.get_team("Hangover 69")
    print team.name
