#!/usr/bin/env python3

import os, json, datetime
from http.client import HTTPConnection

# Ex: 2011-11-07T10:20:48.775Z
DATE_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'

def get_apikey():
    path = os.path.expanduser('~/.time.qpgc.org.apikey')
    if os.path.exists(path):
        return open(path).read().strip()
    assert False, 'API key file not found: ' + path

def get_json_data():
    apikey = get_apikey()
    c = HTTPConnection('time.qpgc.org')
    c.request('GET', '/time', headers={'Cookie': 'apikey=' + apikey})
    rawdata = c.getresponse().read().decode('utf8')
    return json.loads(rawdata)

class TimeEvent:
    def __init__(self, data):
        self.status = data['status']
        self.id = datetime.datetime.strptime(data['id'], DATE_FORMAT)
        self.description = data.get('description')
        self.tags = data.get('tags', [])
    
    def __str__(self):
        return 'TimeEvent({0.status}, {0.id}, "{0.description}", {0.tags})'.format(self)

    def __repr__(self):
        return str(self)

class TimeTask:
    def __init__(self, startEvent, endEvent):
        self.startTime = startEvent.id
        self.endTime = endEvent.id
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
    events = [TimeEvent(x) for x in data]
    for e1, e2 in zip(events, events[1:]):
        if e1.status == 'in':
            yield TimeTask(e1, e2)

def get_and_parse():
    return list(generate_time_tasks(get_json_data()))
    #return [TimeEvent(x) for x in get_json_data()]

def summarize():
    tasks = get_and_parse()
    if tasks:
        date = tasks[0].date()
    else:
        date = None
    day_hours = 0.0
    def print_total():
        print('Total hours: {0:.1f}'.format(day_hours))
        print('')
    for task in tasks:
        if task.date() != date:
            print_total()
            day_hours = 0.0
        day_hours += task.hours()
        print(task.summary())
        date = task.date()
    print_total()

if __name__ == '__main__':
    summarize()
