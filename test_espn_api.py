import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/leagueHistory/121269?seasonId=2023&view=mMatchup"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, context=ctx) as response:
        data = json.loads(response.read().decode('utf-8'))
        payload = data[0] if isinstance(data, list) else data
        with open("sample_matchup.json", "w") as f:
            json.dump(payload['schedule'][0], f, indent=2)
        print("Success")
except Exception as e:
    print(e)
