# footy
Python library for footy.eu
Get calendar for Footy season and export it to a file.
It is hard to mantain because match table names change at every season.
Several vocabulary in Dutch and website doesn't follow a pattern.
Not sure it does work for other leagues, probably HTML Tag changes.

# Usage
```bash
$ mkvirtualenv footy
$ pip install -r requirements.txt
```


```python
>>> from footy import Footy, FootyCalendar
# division, game type, team
>>> footy = Footy('div2', '6wed', 'Hangover')
>>> calendar = FootyCalendar(footy.season)
>>> calendar.generate_calendar_file('/your/path/season.ics')
True
```

