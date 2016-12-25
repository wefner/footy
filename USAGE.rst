=====
Usage
=====

To use footylib in a project:

From ``master`` branch

.. code-block:: python

    >>> from footylib import Footy, FootyCalendar
    # division, game type, team
    >>> footy = Footy('div2', '6tue', 'Hangover')
    >>> calendar = FootyCalendar(footy.season)
    >>> calendar.generate_calendar_file('/your/path/season.ics')
    True


From ``develop`` branch:

.. code-block:: python

    from footylib import Footy
    import logging

    logger = logging.basicConfig(level="DEBUG")

    f = Footy()
    competitions = f.get_competitions()

    for c in competitions:
        print c.name
        print 'Grid:'
        for match in c.get_teams():
            print '\t', 'Position: {}'.format(match.position)
            print '\t\t', 'Team: {}'.format(match.team_name)
            print '\t\t', 'Played games {}'.format(match.played_games)
            print '\t\t', 'Won games {}'.format(match.won_games)
            print '\t\t', 'Tie games {}'.format(match.tie_games)
            print '\t\t', 'Lost games {}'.format(match.lost_games)
            print '\t\t', 'Goals {}'.format(match.goals)
            print '\t\t', 'Diff {}'.format(match.diff)
            print '\t\t', 'Points {}'.format(match.points)
        try:
            print "Calendar:"
            for t in c.get_matches():
                print t.location
                print t.match
                print t.score
                print t.referee
                print t.division
                print t.datetime
                print t.motm
        except AttributeError:
            print "Got an error while getting matches"


