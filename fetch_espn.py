import urllib.request
import urllib.error
import json
import ssl

import os

league_id = "121269"

SWID = os.environ.get("ESPN_SWID", "")
ESPN_S2 = os.environ.get("ESPN_S2", "")

# Create unverified context to bypass local cert issues
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

with open("data.js", "w") as f:
    f.write("const localLeagueData = {\n")
    
    for idx, year in enumerate(range(2011, 2026)):
        url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/leagueHistory/{league_id}?seasonId={year}&view=mMatchupScore&view=mTeam"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        if SWID or ESPN_S2:
            cookie_parts = []
            if SWID: cookie_parts.append(f"swid={SWID}")
            if ESPN_S2: cookie_parts.append(f"espn_s2={ESPN_S2}")
            headers['Cookie'] = "; ".join(cookie_parts)

        req = urllib.request.Request(
            url, 
            headers=headers
        )
        
        try:
            with urllib.request.urlopen(req, context=ctx) as response:
                content = response.read().decode('utf-8')
                data = json.loads(content)
                payload = data[0] if isinstance(data, list) and len(data) > 0 else data
                
                f.write(f'"{year}": {json.dumps(payload)}')
                if idx != 14:
                    f.write(",\n")
                print(f"Success {year}")
        except urllib.error.HTTPError as e:
            if e.code == 302:
                # Handle redirect manually
                redirect_url = e.headers.get('Location')
                if redirect_url:
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
                            
                            # if it's returning html, ESPN is blocking us.
                            if "<html" in content.lower():
                                print(f"Blocked by ESPN HTML page on {year}")
                                f.write(f'"{year}": {{}}')
                                if idx != 14:
                                    f.write(",\n")
                                continue

                            data = json.loads(content)
                            payload = data[0] if isinstance(data, list) and len(data) > 0 else data
                            f.write(f'"{year}": {json.dumps(payload)}')
                            if idx != 14:
                                f.write(",\n")
                            print(f"Success on redirect {year}")
                    except Exception as re:
                        print(f"Redirect failed {year}:", re)
                        f.write(f'"{year}": {{}}')
                        if idx != 14:
                            f.write(",\n")
                else:
                    f.write(f'"{year}": {{}}')
                    if idx != 14:
                        f.write(",\n")
            else:
                print(f"HTTP Error {year}:", e.code)
                f.write(f'"{year}": {{}}')
                if idx != 14:
                    f.write(",\n")
        except Exception as e:
            print(f"Error {year}:", e)
            f.write(f'"{year}": {{}}')
            if idx != 14:
                f.write(",\n")
                
    f.write("\n};\n")
print("Done writing data.js")
