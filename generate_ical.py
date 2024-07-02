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
outputType = sys.argv[2] if (len(sys.argv) > 2) else 'console'
year = sys.argv[3] if (len(sys.argv) > 3) else scheduleYear

res = requests.get(f'https://api.nhle.com/stats/rest/en/team')
teamsData = res.json()['data']
teamInfo = {}
teams = {}
for team in teamsData:
    teams[team['triCode']] = team
    if team['fullName'].endswith(teamName):
        teamInfo = team

if len(teamInfo.keys()) == 0:
    print('No team found, verify the name specified')
    sys.exit(1)

res = requests.get(f'https://api-web.nhle.com/v1/club-schedule-season/{teamInfo["triCode"]}/{year}')
games = res.json()['games']

# If available add promotion nights to the schedule
promotions = {}
promotionsFileName = f'{directory}/promotions-{teamInfo["triCode"]}-{year}.txt'
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

game_data = []
for game in games:
    if game['homeTeam']['id'] == teamInfo['id']:
        start = datetime.fromisoformat(game['startTimeUTC'][:-1])
        start = start.replace(tzinfo=tz.gettz('UTC'))
        start = start.astimezone(tz.gettz(game['venueTimezone']))
        sortable_date = start.strftime('%Y-%m-%d')
        pretty_date = start.strftime('%B %-d, %Y')
        weekday = start.strftime('%A')
        pretty_time = start.strftime('%I:%M %p')
        promotion = '' if sortable_date not in promotions.keys() else promotions[sortable_date]
        # game_type = 'Regular Season' if game['gameType']== 2 else ('Preseason' if game['gameType']== 1 else ('Playoff' if game['gameType'] == 3 else game['gameType']))
        game['gameType'] = 'Regular Season' if game['gameType']== 2 else ('Preseason' if game['gameType']== 1 else ('Playoff' if game['gameType'] == 3 else game['gameType']))

        game_data.append(f"{sortable_date},\"{pretty_date}\",{weekday},{pretty_time},{game['venue']['default']},{game['gameType']},{promotion},{teams[game['awayTeam']['abbrev']]['fullName']},\n")

if outputType == 'console':
    for game in game_data:
        print(game.strip())

if outputType == 'calendar':
    # Calendar sequence
    calendarSequnce = 0
    calendarSequnceFileName = f'{directory}/sequence-{teamInfo["triCode"]}-{scheduleYear}.txt'
    if os.path.exists(calendarSequnceFileName):
        f = open(calendarSequnceFileName)
        calendarSequnce = int(f.read().splitlines()[0].strip())
        f.close()
        calendarSequnce += 1
    f = open(calendarSequnceFileName, "w")
    f.write(str(calendarSequnce))
    f.close()


    cal = Calendar()
    cal['X-WR-CALNAME'] = f'{teamInfo["fullName"]} Home Schedule'
    cal['X-WR-RELCALID'] = f'{teamInfo["fullName"].replace(" ", "-")}-{scheduleYear}-Home-Schedule'.lower()
    cal['METHOD'] = 'PUBLISH'

    for gameList in game_data:
        event = Event()
        event['UID'] = game['id']
        event['SUMMARY'] = 'Preseason: ' if game['gameType']=='Preseason' else ''
        event['SUMMARY'] += f'{teamInfo["fullName"]} vs {teams[game['awayTeam']['abbrev']]['fullName']}'
        event['SUMMARY'] += f' - {promotion}' if promotion != '' else ''
        # if game['venue']['default'] not in locations:
        #     if (game['venue']['link'].endswith('/null')):
        #         locations[game['venue']['name']] = game['venue']['name']
        #     else:
        #         res = requests.get(f'https://statsapi.web.nhl.com/{game["venue"]["link"]}')
        #         venue = res.json()['venues'][0]
        #         locations[venue['name']] = venue['name']
        event['DESCRIPTION'] = promotion
        event['LOCATION'] = locations[game['venue']['default']]
        event['DTSTAMP'] = now
        event['LAST-MODIFIED'] = now
        event['SEQUENCE'] = calendarSequnce
        event.add('DTSTART', start)
        event.add('DTEND', start + gameLength)
        cal.add_component(event)

    # Output the schedule
    f = open(os.path.join(directory, f'{teamInfo["triCode"]}-schedule.ics'), 'wb')
    f.write(cal.to_ical())
    f.close()

if (outputType == 'csv'):
    # Output the CSV
    f = open(os.path.join(directory, f'{teamInfo["triCode"]}-games.csv'), 'w')
    f.write('Sortable Date,Date,Day,Time,Location,Type,Promotion,Opponent,Ticket Status\n')
    f.writelines(game_data)
    f.close()
