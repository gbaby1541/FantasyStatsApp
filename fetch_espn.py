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

def get_optimal_score(roster_entries, slot_limits):
    players = []
    for entry in roster_entries:
        player_info = entry.get('playerPoolEntry', {})
        points = player_info.get('appliedStatTotal', 0)
        eligible_slots = player_info.get('player', {}).get('eligibleSlots', [])
        players.append({'points': points, 'slots': eligible_slots})
    
    players.sort(key=lambda x: x['points'], reverse=True)
    
    filled_slots = {}
    active_slots = {}
    for slot_id_str, limit in slot_limits.items():
        slot_id = int(slot_id_str)
        if slot_id not in [20, 21, 24] and limit > 0:
            active_slots[slot_id] = limit
            filled_slots[slot_id] = 0
            
    total_score = 0
    for p in players:
        sorted_slots = sorted(p['slots'], key=lambda s: (s >= 20, s)) 
        for slot in sorted_slots:
            if slot in active_slots and filled_slots[slot] < active_slots[slot]:
                filled_slots[slot] += 1
                total_score += p['points']
                break
    return total_score

print("Fetching optimal scores for 2025...")
optimal_scores = {}
try:
    # Get settings to find current week and slot limits
    url_settings = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/2025/segments/0/leagues/{league_id}?view=mSettings"
    req_settings = urllib.request.Request(url_settings, headers=headers)
    with urllib.request.urlopen(req_settings, context=ctx) as res:
        settings_data = json.loads(res.read().decode('utf-8'))
        current_week = settings_data.get('status', {}).get('latestScoringPeriod', 1)
        slot_limits = settings_data.get('settings', {}).get('rosterSettings', {}).get('lineupSlotCounts', {})

    for week in range(1, current_week + 1):
        optimal_scores[week] = {}
        url_roster = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/2025/segments/0/leagues/{league_id}?view=mRoster&scoringPeriodId={week}"
        req_roster = urllib.request.Request(url_roster, headers=headers)
        with urllib.request.urlopen(req_roster, context=ctx) as res:
            roster_data = json.loads(res.read().decode('utf-8'))
            for team in roster_data.get('teams', []):
                roster = team.get('roster', {}).get('entries', [])
                opt_score = get_optimal_score(roster, slot_limits)
                optimal_scores[week][team['id']] = opt_score
        print(f"Optimal scores for week {week} calculated.")
except Exception as e:
    print("Error fetching optimal scores:", e)

with open("data.js", "a") as f:
    f.write(f"\nconst currentSeasonOptimal = {json.dumps(optimal_scores)};\n")

print("Done appending optimal scores.")
