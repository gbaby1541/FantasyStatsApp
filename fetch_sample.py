import urllib.request
import urllib.error
import json
import ssl

league_id = "121269"
year = 2015

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/leagueHistory/{league_id}?seasonId={year}&view=mMatchup&view=mTeam"

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
    'Accept': 'application/json',
    'Accept-Language': 'en-US,en;q=0.9',
}

req = urllib.request.Request(url, headers=headers)

try:
    with urllib.request.urlopen(req, context=ctx) as response:
        content = response.read().decode('utf-8')
        data = json.loads(content)
        with open("sample_2015.json", "w") as f:
            json.dump(data, f, indent=2)
        print("Success 2015")
except urllib.error.HTTPError as e:
    if e.code == 302:
        redirect_url = e.headers.get('Location')
        # ensure query params are preserved if needed, but Location usually has them
        # ESPN API usually includes view=mMatchup in the redirect URL if it was in the original
        if 'view=' not in redirect_url:
            redirect_url += "&view=mMatchup&view=mTeam"
        req_redir = urllib.request.Request(
            redirect_url, 
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json'
            }
        )
        try:
            with urllib.request.urlopen(req_redir, context=ctx) as res_redir:
                content = res_redir.read().decode('utf-8')
                data = json.loads(content)
                with open("sample_2015.json", "w") as f:
                    json.dump(data, f, indent=2)
                print("Success on redirect 2015")
        except Exception as re:
            print("Redirect failed", re)
    else:
        print("HTTP Error", e.code)
except Exception as e:
    print("Error", e)
