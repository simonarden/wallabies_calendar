# Caulfield Racing subscription

A separate subscription for race meetings at Caulfield and Caulfield Heath from the [MRC calendar](https://mrc.racing.com/calendar). Sandown, Mornington, trials, jump outs, breakfasts and other non-race events are excluded.

Every event uses **12 pm–6 pm Australia/Melbourne**, converted to UTC with daylight saving handled automatically. These are planning windows, not official race times. There are no alarms; entries show as free.

Subscribe using:

https://raw.githubusercontent.com/simonarden/wallabies_calendar/main/caulfield/caulfield.ics

In Outlook on the web, choose **Add calendar → Subscribe from web**, paste that URL and name it **Caulfield Racing**. Subscribe rather than importing a file. Select the account in which you want the subscription. Your calendar provider controls how quickly updates appear.

## Updates

The GitHub workflow checks daily at 19:23 UTC and can be run manually from Actions. It reads the same public GraphQL feed used by MRC's calendar, querying the current month and 12 months ahead. Publication depends on what MRC has released. The browser's public API configuration is discovered on each run; no account credentials or API keys are stored here.

Stable meeting IDs preserve event identity as names or dates change. Missing future events are marked cancelled after two successful checks. Any failed query or an empty future fixture set stops publication, preserving the previous calendar. `last-checked.json` records successful checks; daily updates to that file also keep repository activity current. Check GitHub Actions if the timestamp stops advancing. The MRC data schema may require maintenance if their website changes.

The existing Wallabies feed remains independent. This folder contains only public racing fixtures and code, with no personal calendar data.

Run locally with Python 3.11+:

```
python3 -m unittest discover -s caulfield -p 'test_*.py'
python3 caulfield/update.py
```
