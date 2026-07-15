import urllib.request
import urllib.error
import json
import ssl

league_id = "121269"
year = 2023

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/leagues/{league_id}?view=mMatchupScore&view=mTeam&view=mRoster&view=mMatchup"

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
    'Accept': 'application/json',
}

req = urllib.request.Request(url, headers=headers)

try:
    with urllib.request.urlopen(req, context=ctx) as response:
        content = response.read().decode('utf-8')
        data = json.loads(content)
        with open("sample_2023.json", "w") as f:
            json.dump(data, f, indent=2)
        print("Success 2023")
except Exception as e:
    print("Error", e)
