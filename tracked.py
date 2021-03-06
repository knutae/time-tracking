#!/usr/bin/env python3

import argparse
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

    def date(self):
        return self.id.date()

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

def generate_time_tasks(data, startDate, endDate):
    events = [TimeEvent(x) for x in data if 'status' in x]
    events = [x for x in events if x.date() >= startDate and x.date() <= endDate]
    #print('Sorting %s events...' % len(events))
    events.sort(key=lambda x:x.id)
    #print('Done sorting')
    for e1, e2 in zip(events, events[1:]):
        if e1.status == 'in':
            yield TimeTask(e1, e2)

def get_and_parse(startDate, endDate):
    #print(get_json_data())
    return list(generate_time_tasks(get_json_data(), startDate, endDate))
    #return [TimeEvent(x) for x in get_json_data()]

def summarize(startDate, endDate):
    tasks = get_and_parse(startDate, endDate)
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
        if task.date() != date:
            print_total()
            day_hours = 0.0
            hours_per_tags.clear()
        day_hours += task.hours()
        hours_per_tags['/'.join(task.tags)] += task.hours()
        print(task.summary())
        date = task.date()
    print_total()

def dump_csv(startDate, endDate):
    import csv, sys
    tasks = get_and_parse(startDate, endDate)
    w = csv.writer(sys.stdout)
    w.writerow(['Date', 'StartTime', 'EndTime', 'Hours', 'Tags', 'Description'])
    for task in tasks:
        date = task.date().strftime('%Y-%m-%d')
        startTime = task.startTime.strftime('%H:%M')
        endTime = task.endTime.strftime('%H:%M')
        hours = '{:.1f}'.format(task.hours())
        w.writerow([date, startTime, endTime, hours, ' '.join(task.tags), task.description])

def valid_date(s):
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--start-date', '-s', type=valid_date, default='2017-01-01')
    parser.add_argument('--end-date', '-e', type=valid_date, default='2018-01-01')
    parser.add_argument('--csv', action='store_true')
    args = parser.parse_args()
    #print(args)
    #startDate = datetime.date(2017, 1, 1)
    if args.csv:
        dump_csv(args.start_date, args.end_date)
    else:
        summarize(args.start_date, args.end_date)
