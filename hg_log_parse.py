#!/usr/bin/env python

import subprocess, datetime, os

LOG_TEMPLATE='''---+++---
date:{date}
desc:{desc}
files:{files}
'''

def parse_raw_date(raw_date):
    # parse: timestamp-tz_offset (and ignore timezone)
    if '-' in raw_date:
        i = raw_date.index('-')
        timestamp = float(raw_date[:i])
    else:
        timestamp = float(raw_date)
    return datetime.datetime.fromtimestamp(timestamp)

class LogEntry:
    def __init__(self, repos_name, raw_entry):
        self.repos_name = repos_name
        fields = dict()
        for line in raw_entry.splitlines():
            if ':' not in line:
                continue
            i = line.index(':')
            key = line[:i]
            value = line[i+1:]
            fields[key] = value
        self.desc = fields['desc']
        self.files = fields['files']
        self.datetime = parse_raw_date(fields['date'])

    def date(self):
        if self.datetime.hour < 5:
            # someone is working at night, assume this work belongs to the previous day :)
            #print(self.datetime, "->", (self.datetime - datetime.timedelta(days=1)).date())
            return (self.datetime - datetime.timedelta(days=1)).date()
        return self.datetime.date()

    def __str__(self):
        return 'LogEntry(datetime="{0.datetime}", repos="{0.repos_name}", files="{0.files}", desc="{0.desc}")'.format(self)
    
    def __cmp__(self, other):
        return cmp(self.datetime, other.datetime)

def hg(*args):
    cmd = ['hg'] + list(args)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    out, err = p.communicate()
    return out.strip()

def parse_hg_log(repos, user):
    repos_name = hg('showconfig', '-R', repos, 'paths.default')
    repos_name = repos_name.split('/')[-1]
    out = hg('log', '-R', repos, '-u', user, '--template', LOG_TEMPLATE)
    entries = out.split('---+++---')
    result = list()
    for entry in entries:
        if len(entry.strip()) == 0:
            continue
        result.append(LogEntry(repos_name, entry))
    return result

# Per-repos file matching rules: these should be tuned per user, and maybe per month...
CATEGORY_RULES = {
    'joker': [('', 'A2')],
    'kolibrifx': [('releng', 'A2'), ('TimeNavigator', 'A2'), ('Plot', 'A2'), ('', 'IDE')],
    'snowcap': [('releng', 'A2'), ('', 'IDE')],
    'nectar': [('', 'Kompilator')],
    'quantility': [('', 'Kompilator')],
    'joker-wiki': [('', 'A2')],
}

def log_entry_category(entry):
    for search, cat in CATEGORY_RULES[entry.repos_name]:
        if search in entry.files:
            return cat

def enumerate_entries_per_date(entries):
    current_date = entries[0].date()
    block = []
    for entry in entries:
        if entry.date() == current_date:
            block.append(entry)
        else:
            yield current_date, block
            block = [entry]
            current_date = entry.date()
    yield current_date, block

def count_categories(entries):
    categories = dict()
    for entry in entries:
        cat = log_entry_category(entry)
        categories[cat] = categories.get(cat, 0) + 1
    return categories

def format_categories(block):
    c = count_categories(block)
    total = float(len(block))
    return ', '.join('{0} ({1:.0%})'.format(cat, count/total) for cat, count in sorted(c.items()))

def clamp(n, min, max):
    if n < min:
        return min
    if n > max:
        return max
    return n

def estimate_hours_worked(day_block):
    # This is a very rough estimate... adds an hour before and after the first and last commit,
    # and clamps the result. Does not attempt to apply smart logic for people coding after dinner. :)
    start = day_block[0].datetime - datetime.timedelta(hours=1)
    end = day_block[-1].datetime + datetime.timedelta(hours=1)
    hours = round((end - start).seconds / 3600.0)
    return clamp(hours, 6.0, 12.0)

def detect_repositories(dir='.'):
    result = []
    if os.path.isdir(os.path.join(dir, '.hg')):
        result.append(dir)
    import glob
    result.extend(os.path.normpath(os.path.dirname(x))
                  for x in glob.glob(os.path.join(dir, '*', '.hg'))
                  if os.path.isdir(x))
    return result

def main():
    import optparse
    p = optparse.OptionParser('%prog [options]')
    p.add_option('-u', '--user', action='store', type='string', dest='user')
    p.add_option('-v', '--verbose', action='store_true', dest='verbose', default=False)
    opts, args = p.parse_args()
    if not opts.user:
        print('Missing required user argument')
        p.print_help()
        return
    r = []
    user = opts.user
    for repos in detect_repositories():
        log = parse_hg_log(repos, user)
        r.extend(log)
        print('{0}: {1} entries'.format(repos, len(log)))
    r.sort()
    for date, block in enumerate_entries_per_date(r):
        hours = estimate_hours_worked(block)
        print('{0:%d.%m.%Y}: {1:2} commits -- {2:4} hours -- {3}'.format(date, len(block), hours, format_categories(block)))
        if opts.verbose:
            for entry in block:
                print('    {0:%H:%M} {1} ({2})'.format(entry.datetime, entry.desc, entry.repos_name))
    print('Total: {0} commits -- {1}'.format(len(r), format_categories(r)))

if __name__ == '__main__':
    main()
