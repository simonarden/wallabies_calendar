"""Publish MRC's public Caulfield race meetings as an iCalendar subscription."""
import concurrent.futures
import datetime as dt
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
SOURCE = 'https://mrc.racing.com/calendar'
ZONE = ZoneInfo('Australia/Melbourne')

def fetch(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read().decode('utf-8')

def public_config():
    html = fetch(SOURCE)
    scripts = re.findall(r'<script[^>]*src="([^"]+)"', html)
    app = next(u for u in scripts if '/pages/_app-' in u)
    script = fetch(app)
    # This is the public website's own client configuration, not account credentials.
    host = re.search(r'"appSyncGraphQLHost":"([^"]+)"', script)[1]
    key = re.search(r'"appSyncGraphQLAPIKey":"([^"]+)"', script)[1]
    if host != 'https://graphql.api.racing.com':
        raise ValueError('Unexpected upstream host; review before using it')
    return host, key

def month_items(year, month, host, key):
    query = ('query { getCalendarItems(year: %d, month: %d, '
             'raceClubs: ["10054","10720"], hideHiddenEvents: true) '
             '{ id name race_meet_id location_name event_start_time event_type '
             'race_meet_type event_page_url event_status race_meet_status } }') % (year, month)
    data = json.loads(fetch(host + '?query=' + urllib.parse.quote(query), {'x-api-key': key}))
    if data.get('errors') or not isinstance(data.get('data', {}).get('getCalendarItems'), list):
        raise ValueError('Upstream fixture query failed')
    return data['data']['getCalendarItems']

def normalise(item):
    venue = (item.get('location_name') or '').strip()
    if venue.casefold() not in {'caulfield', 'caulfield heath'}:
        return None
    if item.get('event_type') != 'Racing' or item.get('race_meet_type') not in {'Metro', 'Country'}:
        return None
    if not item.get('race_meet_id') or not item.get('name'):
        raise ValueError('Race meeting missing identity or title')
    stamp = dt.datetime.fromisoformat(item['event_start_time'].replace('Z', '+00:00'))
    if stamp.tzinfo is None:
        raise ValueError('Upstream date missing timezone')
    day = stamp.astimezone(ZONE).date()
    status = ' '.join(str(item.get(k) or '') for k in ('event_status','race_meet_status')).lower()
    return dict(uid=f"mrc-{item['race_meet_id']}@caulfield-racing", title=item['name'],
                date=day.isoformat(), venue=venue, url=item.get('event_page_url') or SOURCE,
                cancelled=any(s in status for s in ('cancel', 'abandon')))

def escape(value):
    return str(value).replace('\\','\\\\').replace('\n','\\n').replace(';','\\;').replace(',','\\,')

def fold(line):
    parts, current = [], ''
    for char in line:
        if len((current + char).encode('utf-8')) > 75:
            parts.append(current); current = ' '
        current += char
    return '\r\n'.join(parts + [current])

def utc_time(day, hour):
    return dt.datetime.combine(dt.date.fromisoformat(day), dt.time(hour), ZONE).astimezone(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')

def calendar(events):
    lines = ['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Caulfield Racing Calendar//EN',
             'CALSCALE:GREGORIAN','METHOD:PUBLISH','X-WR-CALNAME:Caulfield Racing',
             'X-WR-TIMEZONE:Australia/Melbourne','REFRESH-INTERVAL;VALUE=DURATION:PT12H',
             'X-PUBLISHED-TTL:PT12H']
    for e in sorted(events, key=lambda e:(e['date'],e['uid'])):
        lines += ['BEGIN:VEVENT','UID:'+e['uid'],'DTSTAMP:'+e['modified'],
                  'LAST-MODIFIED:'+e['modified'],'SEQUENCE:'+str(e['sequence']),
                  'DTSTART:'+utc_time(e['date'],12),'DTEND:'+utc_time(e['date'],18),
                  'SUMMARY:'+escape(e['title']), 'LOCATION:'+escape(e['venue']+' Racecourse, Victoria, Australia'),
                  'URL:'+e['url'], 'STATUS:'+('CANCELLED' if e['cancelled'] else 'CONFIRMED'),
                  'TRANSP:TRANSPARENT',
                  'DESCRIPTION:'+escape('Race meeting at '+e['venue']+'. Calendar window: 12 pm to 6 pm Australia/Melbourne; this is a planning window, not official race times. Source: '+e['url']),
                  'END:VEVENT']
    return '\r\n'.join(fold(line) for line in lines + ['END:VCALENDAR'])+'\r\n'

def main():
    today = dt.datetime.now(ZONE).date()
    first = today.replace(day=1)
    months = []
    for offset in range(13):
        total = first.year*12+first.month-1+offset
        year, month = divmod(total,12); months.append((year,month+1))
    host, key = public_config()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        batches = list(pool.map(lambda ym: month_items(*ym,host,key),months))
    current = {}
    for batch in batches:
        for item in batch:
            event = normalise(item)
            if event: current[event['uid']] = event
    if not any(e['date'] >= today.isoformat() for e in current.values()):
        raise ValueError('No future Caulfield meetings returned; preserving published feed')
    state_path = ROOT/'state.json'
    previous = json.loads(state_path.read_text()) if state_path.exists() else {}
    now = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    # Keep past meetings; mark missing future meetings cancelled only after two successful checks.
    result = dict(previous)
    for uid, event in current.items():
        old = previous.get(uid)
        changed = not old or any(old.get(k)!=v for k,v in event.items())
        result[uid] = dict(event, modified=now if changed else old['modified'],
                           sequence=(old['sequence']+1 if old else 0) if changed else old['sequence'], missing=0)
    for uid, old in previous.items():
        if uid not in current and old['date'] >= today.isoformat():
            missing = old.get('missing',0)+1
            result[uid] = dict(old, missing=missing)
            if missing >= 2 and not old['cancelled']:
                result[uid].update(cancelled=True, modified=now, sequence=old['sequence']+1)
    text = calendar(result.values())
    (ROOT/'caulfield.ics').write_bytes(text.encode())
    state_path.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    (ROOT/'last-checked.json').write_text(json.dumps({'checked':now,'source':SOURCE,'future_meetings':sum(e['date']>=today.isoformat() and not e['cancelled'] for e in result.values())})+'\n')
    print(f'Published {len(result)} meetings; checked {months[0]} through {months[-1]}')

if __name__ == '__main__':
    main()
