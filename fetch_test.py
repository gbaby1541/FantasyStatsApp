import requests
import json
import urllib3
import sys

urllib3.disable_warnings()

year = 2023
league_id = 121269
scoring_period = 1
url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/leagues/{league_id}?view=mMatchupScore&view=mTeam&view=mRoster&view=mMatchup&scoringPeriodId={scoring_period}"

cookies = {
    'swid': '{636B6316-72B6-405E-B9FC-0E40745FA8EF}',
    'espn_s2': 'AECwG0rogVBX6YYY0vWlihD3LGxmRiLakav%2BYKdfdC3bahHmZsV0IYgHivsJt3%2B00WYhn%2FuMoaBRnwrdvX2Y5ls9TnVwN8uKiVUnuD35pPNVjdfSa9ia10tOjH86%2FzPjcy03VBucihrSo6wViMFUp4CgCX8fH5kKkLakAi7UwnFhEBrQ6vEuNiKompIf9i9qgnM8pHi2rwBdtytzD%2B3thvBe79kskzvmeXOzhNxHbeBNL09zJ4QKDqEKkBa%2Fo5lDTNs5WE1S7LbGQtqf3W7uTElL'
}

res = requests.get(url, cookies=cookies, verify=False)
if res.status_code == 200:
    data = res.json()
    try:
        # find the schedule item for scoring period 1
        matchup = next((m for m in data['schedule'] if m['matchupPeriodId'] == 1), None)
        if matchup:
            print("Keys in home:", list(matchup['home'].keys()))
            if 'rosterForMatchupPeriod' in matchup['home']:
                player = matchup['home']['rosterForMatchupPeriod']['entries'][0]
                with open("sample_player.json", "w") as f:
                    json.dump(player, f, indent=2)
                print("Found rosterForMatchupPeriod!")
            else:
                print("No roster found in home!")
    except Exception as e:
        print("Error parsing:", e)
else:
    print("Failed", res.status_code)
