import requests
import json
import urllib3
urllib3.disable_warnings()

year = 2011
league_id = 121269
url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/leagueHistory/{league_id}?seasonId={year}&view=mMatchup&view=mMatchupScore&scoringPeriodId=1"

cookies = {
    'swid': '{636B6316-72B6-405E-B9FC-0E40745FA8EF}',
    'espn_s2': 'AECwG0rogVBX6YYY0vWlihD3LGxmRiLakav%2BYKdfdC3bahHmZsV0IYgHivsJt3%2B00WYhn%2FuMoaBRnwrdvX2Y5ls9TnVwN8uKiVUnuD35pPNVjdfSa9ia10tOjH86%2FzPjcy03VBucihrSo6wViMFUp4CgCX8fH5kKkLakAi7UwnFhEBrQ6vEuNiKompIf9i9qgnM8pHi2rwBdtytzD%2B3thvBe79kskzvmeXOzhNxHbeBNL09zJ4QKDqEKkBa%2Fo5lDTNs5WE1S7LbGQtqf3W7uTElL'
}

res = requests.get(url, cookies=cookies, verify=False, allow_redirects=True)
if res.status_code == 200:
    data = res.json()[0]
    matchup = data['schedule'][0]
    print("Keys in home:", list(matchup['home'].keys()))
    if 'rosterForMatchupPeriod' in matchup['home']:
        print("Found roster!")
        player = matchup['home']['rosterForMatchupPeriod']['entries'][0]
        stats = player['playerPoolEntry']['player'].get('stats', [])
        print("Player stats array length:", len(stats))
        for stat_block in stats:
            print("Stat block keys:", list(stat_block.keys()), "scoringPeriodId:", stat_block.get('scoringPeriodId'))
            print("Applied stats:", stat_block.get('stats'))
    else:
        print("No roster found.")
else:
    print("Status:", res.status_code)
