#!/usr/bin/env python3

import os, json, datetime
from http.client import HTTPSConnection
from collections import defaultdict

def utc_to_local(utc_dt):
    return utc_dt.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None)

def parse_iso_8601_utc_time(s):
    for format in ['%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ']:
        try:
            return datetime.datetime.strptime(s, format)
        except ValueError:
            pass
    raise ValueError('Failed to parse time: ' + s)

def get_apikey():
    path = os.path.expanduser('~/.clocked.io.apikey')
    if os.path.exists(path):
        return open(path).read().strip()
    assert False, 'API key file not found: ' + path

def get_raw_data():
    apikey = get_apikey()
    c = HTTPSConnection('clocked.io')
    c.request('GET', '/time', headers={'apikey': apikey})
    return c.getresponse().read().decode('utf8')

def get_json_data():
    return json.loads(get_raw_data())

class TimeEvent:
    def __init__(self, data):
        #print('----- ' + str(data))
        self.status = data['status']
        self.id = parse_iso_8601_utc_time(data['_id'])
        self.description = data.get('description')
        self.tags = data.get('tags', [])
    
    def __str__(self):
        return 'TimeEvent({0.status}, {0.id}, "{0.description}", {0.tags})'.format(self)

    def __repr__(self):
        return str(self)

class TimeTask:
    def __init__(self, startEvent, endEvent):
        self.startTime = utc_to_local(startEvent.id)
        self.endTime = utc_to_local(endEvent.id)
        self.description = startEvent.description
        self.tags = startEvent.tags

    def __str__(self):
        return 'TimeTask({0.startTime} - {0.endTime}, "{0.description}", {0.tags})'.format(self)

    def __repr__(self):
        return str(self)
    
    def date(self):
        return self.startTime.date()
    
    def hours(self):
        return (self.endTime - self.startTime).total_seconds() / 3600.0
    
    def summary(self):
        date = self.date().strftime('%Y-%m-%d')
        start = self.startTime.strftime('%H:%M')
        end = self.endTime.strftime('%H:%M')
        return '{1} {2} -- {3} ({4:.1f}h): {0.description} {0.tags}'.format(self, date, start, end, self.hours())

def generate_time_tasks(data):
    events = [TimeEvent(x) for x in data if 'status' in x]
    #print('Sorting %s events...' % len(events))
    events.sort(key=lambda x:x.id)
    #print('Done sorting')
    for e1, e2 in zip(events, events[1:]):
        if e1.status == 'in':
            yield TimeTask(e1, e2)

def get_and_parse():
    #print(get_json_data())
    return list(generate_time_tasks(get_json_data()))
    #return [TimeEvent(x) for x in get_json_data()]

def summarize(startDate):
    tasks = get_and_parse()
    if tasks:
        date = tasks[0].date()
    else:
        date = None
    day_hours = 0.0
    hours_per_tags = defaultdict(lambda: 0.0)
    def print_total():
        breakdown = ' | '.join('{0}: {1:.1f}'.format(tags, hours)
                               for tags, hours in sorted(hours_per_tags.items()))
        print('Total hours: {0:.1f} :: {1}'.format(day_hours, breakdown))
        print('')
    for task in tasks:
        if task.date() < startDate:
            date = task.date()
            continue
        if task.date() != date:
            print_total()
            day_hours = 0.0
            hours_per_tags.clear()
        day_hours += task.hours()
        hours_per_tags['/'.join(task.tags)] += task.hours()
        print(task.summary())
        date = task.date()
    print_total()

if __name__ == '__main__':
    startDate = datetime.date(2014, 1, 1)
    summarize(startDate)
