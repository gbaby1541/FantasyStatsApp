import requests
import json
import urllib3

urllib3.disable_warnings()

year = 2022
league_id = 121269
url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/leagueHistory/{league_id}?seasonId={year}&view=mMatchupScore&view=mTeam"

res = requests.get(url, verify=False, allow_redirects=True)
if res.status_code == 200:
    print("Success without cookies!")
else:
    print(f"Failed with {res.status_code}")
