#!/usr/bin/env python3

import os, json, time
from datetime import datetime, date, timedelta
from http.client import HTTPSConnection

def parse_iso_8601_utc_time(s):
    for format in ['%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ']:
        try:
            return datetime.strptime(s, format)
        except ValueError:
            pass
    raise ValueError('Failed to parse time: ' + s)

def format_timestamp(d):
    return d.strftime('%Y-%m-%dT%H:%M:%SZ')

def get_apikey():
    path = os.path.expanduser('~/.clocked.io.apikey')
    if os.path.exists(path):
        return open(path).read().strip()
    assert False, 'API key file not found: ' + path

def raw_request(method, path, body=None):
    apikey = get_apikey()
    c = HTTPSConnection('clocked.io')
    c.request(method, path, headers={'apikey': apikey, 'Content-Type': 'application/json'}, body=body)
    return c.getresponse().read().decode('utf8')

def json_request(method, path):
    return json.loads(raw_request(method, path))

class Entry:
    def __init__(self, timestamp, status, description, tags):
        self._id = format_timestamp(timestamp)
        self.status = status
        self.description = description
        self.tags = tags
    
    def to_json(self):
        return json.dumps({
            '_id': self._id,
            'status': self.status,
            'description': self.description,
            'tags': self.tags,
        })

def get_time(args):
    utcnow = datetime.utcnow()
    #print('UTC: ' + str(utcnow))
    if args.time == 'NOW':
        assert args.date == 'TODAY'
        return utcnow
    x = datetime.strptime(args.time, '%H:%M')
    #print(t.hour)
    if args.date == 'TODAY':
        t = datetime.now()
    else:
        t = datetime.strptime(args.date, '%Y-%m-%d')
    t = t.replace(hour=x.hour, minute=x.minute, second=0, microsecond=0)
    # Convert to UTC in a really ugly way... have not found a better API
    if time.daylight and time.localtime().tm_isdst:
        t += timedelta(seconds=time.altzone)
    else:
        t += timedelta(seconds=time.timezone)
    t = t.replace(tzinfo=utcnow.tzinfo)
    if t > utcnow:
        # time is in the future, subtract a day
        #print('IN THE FUTURE')
        t -= timedelta(days=1)
    return t

def parse_message(message):
    words = message.split()
    return message.replace('#', ''), [tag[1:] for tag in words if tag.startswith('#')]

def post(entry):
    #print('Posting: ' + entry.to_json())
    res = raw_request('POST', '/time', entry.to_json())
    print(res)

def stamp_in(args):
    time = get_time(args)
    #print('STAMP IN: ' + args.message + ' at ' + str(time))
    desc, tags = parse_message(args.message)
    entry = Entry(time, 'in', desc, tags)
    post(entry)
    print('Stamped IN at ' + str(time) + ' UTC: ' + desc + " " + str(tags))

def stamp_out(args):
    time = get_time(args)
    #print('STAMP OUT at ' + str(time))
    entry = Entry(time, 'out', '', [])
    post(entry)
    print('Stamped OUT at ' + str(time) + ' UTC')

def delete_entry(args):
    time = get_time(args)
    path = '/time/' + format_timestamp(time)
    res = raw_request('DELETE', path)
    if res.strip():
        print(res)
        

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    #parser.set_defaults(func=None)
    sub = parser.add_subparsers(help='command', dest='cmd')
    cmd_in = sub.add_parser('in', help='stamp in')
    cmd_in.add_argument('--message', '-m', type=str, help='Status message (with #hashtags)', required=True)
    cmd_in.add_argument('--time', '-t', type=str, default='NOW',
                        help='clock to use instead of the current time (HH:mm)')
    cmd_in.add_argument('--date', '-d', type=str, default='TODAY',
                        help='date to use instead of today (YYYY-MM-dd)')
    cmd_in.set_defaults(func=stamp_in)
    cmd_out = sub.add_parser('out', help='stamp out')
    cmd_out.set_defaults(func=stamp_out)
    cmd_out.add_argument('--time', '-t', type=str, default='NOW',
                         help='clock to use instead of the current time (HH:mm)')
    cmd_out.add_argument('--date', '-d', type=str, default='TODAY',
                         help='date to use instead of today (yyyy-mm-dd)')
    cmd_delete = sub.add_parser('delete', help='delete entry')
    cmd_delete.set_defaults(func=delete_entry)
    cmd_delete.add_argument('--time', '-t', type=str, required=True,
                            help='time of day (HH:mm)')
    cmd_delete.add_argument('--date', '-d', type=str, default='TODAY',
                            help='date to use instead of today (yyyy-mm-dd)')

    args = parser.parse_args()
    if args.cmd is None:
        parser.print_help()
    else:
        args.func(args)
