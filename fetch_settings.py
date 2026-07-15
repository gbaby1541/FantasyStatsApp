import requests
import json
import urllib3

urllib3.disable_warnings()

league_id = 121269
year = 2023
url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/leagues/{league_id}?view=mSettings"

cookies = {
    'swid': '{636B6316-72B6-405E-B9FC-0E40745FA8EF}',
    'espn_s2': 'AECwG0rogVBX6YYY0vWlihD3LGxmRiLakav%2BYKdfdC3bahHmZsV0IYgHivsJt3%2B00WYhn%2FuMoaBRnwrdvX2Y5ls9TnVwN8uKiVUnuD35pPNVjdfSa9ia10tOjH86%2FzPjcy03VBucihrSo6wViMFUp4CgCX8fH5kKkLakAi7UwnFhEBrQ6vEuNiKompIf9i9qgnM8pHi2rwBdtytzD%2B3thvBe79kskzvmeXOzhNxHbeBNL09zJ4QKDqEKkBa%2Fo5lDTNs5WE1S7LbGQtqf3W7uTElL'
}

res = requests.get(url, cookies=cookies, verify=False)
if res.status_code == 200:
    data = res.json()
    items = data['settings']['scoringSettings']['scoringItems']
    for item in items:
        if item.get('points', 0) != 0:
            print(f"ID: {item['statId']}, Pts: {item['points']}")
else:
    print("Failed")
