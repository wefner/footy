=====
Usage
=====

To use footylib in a project:

.. code-block:: python

    >>> from footylib import Footy, FootyCalendar
    # division, game type, team
    >>> footy = Footy('div2', '6tue', 'Hangover')
    >>> calendar = FootyCalendar(footy.season)
    >>> calendar.generate_calendar_file('/your/path/season.ics')
    True


