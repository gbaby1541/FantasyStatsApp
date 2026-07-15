import requests
import json
import urllib3

urllib3.disable_warnings()

year = 2022
league_id = 121269
url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/leagueHistory/{league_id}?seasonId={year}&view=mMatchup&view=mTeam"

res = requests.get(url, verify=False, allow_redirects=True)
if res.status_code == 200:
    data = res.json()
    payload = data[0] if isinstance(data, list) else data
    with open("sample_matchup.json", "w") as f:
        json.dump(payload['schedule'][0], f, indent=2)
    print("Success")
else:
    print(f"Failed with {res.status_code}")
