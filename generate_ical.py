import requests
from icalendar import Calendar, Event
from datetime import datetime, timedelta
from dateutil import tz
import os, sys

directory = '.'
gameLength = timedelta(hours=3)
now = datetime.now().strftime('%Y%m%dT%H%M%SZ')

# Assume we are running this for the upcoming season or at least in the year the season starts
currentYear = datetime.now().year
scheduleYear = str(currentYear) + str(currentYear+1)

teamName = sys.argv[1] if (len(sys.argv) > 1) else 'Hurricanes'

res = requests.get('https://statsapi.web.nhl.com/api/v1/teams')
teams = res.json()['teams']
teamInfo = {}
for team in teams:
    if team['name'].endswith(teamName):
        teamInfo = team
        break

if len(teamInfo.keys()) == 0:
    print('No team found, verify the name specified')
    sys.exit(1)

res = requests.get(f'https://statsapi.web.nhl.com/api/v1/schedule?site=en_nhl&teamId={teamInfo["id"]}&season={scheduleYear}&gameType=PR,R')
games = res.json()['dates']

# If available add promotion nights to the schedule
promotions = {}
promotionsFileName = f'{directory}/promotions-{teamInfo["teamName"]}-{scheduleYear}.txt'
if os.path.exists(promotionsFileName):
    f = open(promotionsFileName)
    lines = f.readlines()
    for line in lines:
        [date, label] = line.strip().split(':')
        promotions[date] = label

# Really wish the API had addresses instead of storing them
locations = {}
locationsFileName = f'{directory}/locations.txt'
if os.path.exists(locationsFileName):
    f = open(locationsFileName)
    lines = f.readlines()
    for line in lines:
        [name, address] = line.strip().split(':')
        locations[name] = address


# Calendar sequence
calendarSequnce = 0
calendarSequnceFileName = f'{directory}/sequence-{teamInfo["teamName"]}-{scheduleYear}.txt'
if os.path.exists(calendarSequnceFileName):
    f = open(calendarSequnceFileName)
    calendarSequnce = int(f.read().splitlines()[0].strip())
    f.close()
    calendarSequnce += 1
f = open(calendarSequnceFileName, "w")
f.write(str(calendarSequnce))
f.close()


cal = Calendar()
cal['X-WR-CALNAME'] = f'{teamInfo["name"]} Home Schedule'
cal['X-WR-RELCALID'] = f'{teamInfo["name"].replace(" ", "-")}-{scheduleYear}-Home-Schedule'.lower()
cal['METHOD'] = 'PUBLISH'

game_data = []
for gameList in games:
    game = gameList['games'][0]
    if game['teams']['home']['team']['id'] == teamInfo['id']:
        start = datetime.fromisoformat(game['gameDate'][:-1])
        start = start.replace(tzinfo=tz.gettz('UTC'))
        start = start.astimezone(tz.gettz(teamInfo['venue']['timeZone']['tz']))
        sortable_date = start.strftime('%Y-%m-%d')
        pretty_date = start.strftime('%B %-d, %Y')
        weekday = start.strftime('%A')
        pretty_time = start.strftime('%I:%M %p')
        promotion = '' if sortable_date not in promotions.keys() else promotions[sortable_date]
        game_type = 'Regular Season' if game['gameType']== 'R' else ('Preseason' if game['gameType']== 'PR' else game['gameType'])

        event = Event()
        event['UID'] = game['gamePk']
        event['SUMMARY'] = 'Preseason: ' if game['gameType']=='PR' else ''
        event['SUMMARY'] += f'{teamInfo["teamName"]} vs {game["teams"]["away"]["team"]["name"]}'
        event['SUMMARY'] += f' - {promotion}' if promotion != '' else ''
        if game['venue']['name'] not in locations:
            if (game['venue']['link'].endswith('/null')):
                locations[game['venue']['name']] = game['venue']['name']
            else:
                res = requests.get(f'https://statsapi.web.nhl.com/{game["venue"]["link"]}')
                venue = res.json()['venues'][0]
                locations[venue['name']] = venue['name']
        event['DESCRIPTION'] = promotion
        event['LOCATION'] = locations[game['venue']['name']]
        event['DTSTAMP'] = now
        event['LAST-MODIFIED'] = now
        event['SEQUENCE'] = calendarSequnce
        event.add('DTSTART', start)
        event.add('DTEND', start + gameLength)
        cal.add_component(event)

        game_data.append(f"{sortable_date},\"{pretty_date}\",{weekday},{pretty_time},{game['venue']['name']},{game_type},{promotion},{game['teams']['away']['team']['name']},\n")


# Output the schedule
f = open(os.path.join(directory, f'{teamInfo["teamName"]}-schedule.ics'), 'wb')
f.write(cal.to_ical())
f.close()

# Output the CSV
f = open(os.path.join(directory, f'{teamInfo["teamName"]}-games.csv'), 'w')
f.write('Sortable Date,Date,Day,Time,Location,Type,Promotion,Opponent,Ticket Status\n')
f.writelines(game_data)
f.close()
