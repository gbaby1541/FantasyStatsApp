import urllib.request
import json
import ssl

league_id = "121269"
year = 2011

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/leagueHistory/{league_id}?seasonId={year}&view=mMatchupScore&view=mTeam&view=mRoster&view=mMatchup"

cookies = {
    'swid': '{636B6316-72B6-405E-B9FC-0E40745FA8EF}',
    'espn_s2': 'AECwG0rogVBX6YYY0vWlihD3LGxmRiLakav%2BYKdfdC3bahHmZsV0IYgHivsJt3%2B00WYhn%2FuMoaBRnwrdvX2Y5ls9TnVwN8uKiVUnuD35pPNVjdfSa9ia10tOjH86%2FzPjcy03VBucihrSo6wViMFUp4CgCX8fH5kKkLakAi7UwnFhEBrQ6vEuNiKompIf9i9qgnM8pHi2rwBdtytzD%2B3thvBe79kskzvmeXOzhNxHbeBNL09zJ4QKDqEKkBa%2Fo5lDTNs5WE1S7LbGQtqf3W7uTElL'
}

cookie_string = "; ".join([f"{k}={v}" for k,v in cookies.items()])
headers = {
    'User-Agent': 'Mozilla/5.0',
    'Cookie': cookie_string
}

req = urllib.request.Request(url, headers=headers)

try:
    with urllib.request.urlopen(req, context=ctx) as response:
        data = json.loads(response.read().decode('utf-8'))[0]
        matchup = data['schedule'][0]
        print("Keys in home:", matchup['home'].keys())
except urllib.error.HTTPError as e:
    if e.code == 302:
        redir = e.headers.get('Location')
        if 'view=' not in redir:
            redir += "&view=mMatchupScore&view=mTeam&view=mRoster&view=mMatchup"
        req_redir = urllib.request.Request(redir, headers=headers)
        try:
            with urllib.request.urlopen(req_redir, context=ctx) as res2:
                data = json.loads(res2.read().decode('utf-8'))[0]
                matchup = data['schedule'][0]
                print("Keys in home (redir):", matchup['home'].keys())
        except Exception as e2:
            print("Error on redir:", e2)
    else:
        print("Error:", e)
except Exception as e:
    print("Error:", e)
