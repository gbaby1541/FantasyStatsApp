import requests
import json
import urllib3

urllib3.disable_warnings()

league_id = "121269"
cookies = {
    'swid': '{636B6316-72B6-405E-B9FC-0E40745FA8EF}',
    'espn_s2': 'AECwG0rogVBX6YYY0vWlihD3LGxmRiLakav%2BYKdfdC3bahHmZsV0IYgHivsJt3%2B00WYhn%2FuMoaBRnwrdvX2Y5ls9TnVwN8uKiVUnuD35pPNVjdfSa9ia10tOjH86%2FzPjcy03VBucihrSo6wViMFUp4CgCX8fH5kKkLakAi7UwnFhEBrQ6vEuNiKompIf9i9qgnM8pHi2rwBdtytzD%2B3thvBe79kskzvmeXOzhNxHbeBNL09zJ4QKDqEKkBa%2Fo5lDTNs5WE1S7LbGQtqf3W7uTElL'
}

td_stat_ids = ['4', '25', '43', '63', '101', '102', '104']
results = {}

session = requests.Session()
session.cookies.update(cookies)
session.verify = False
session.headers.update({'User-Agent': 'Mozilla/5.0'})

with open('data.js', 'r') as f:
    js_content = f.read().replace('const localLeagueData = ', '')[:-2]
    local_data = json.loads(js_content)

year = 2025
year_str = "2025"
if year_str in local_data:
    teams_info = local_data[year_str].get('teams', [])
    team_tds = {t['id']: 0 for t in teams_info}
    team_names = {t['id']: t.get('name', 'Unknown') for t in teams_info}
    team_ranks = {t['id']: t.get('rankCalculatedFinal', 99) for t in teams_info}
    
    final_scoring_period = local_data[year_str].get('status', {}).get('finalScoringPeriod', 16)
    
    for period in range(1, final_scoring_period + 1):
        url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/leagues/{league_id}?view=mMatchup&view=mMatchupScore&scoringPeriodId={period}"
            
        res = session.get(url, allow_redirects=False)
        if res.status_code == 302:
            redir = res.headers.get('Location')
            if '?' not in redir:
                redir += f"?seasonId={year}&view=mMatchup&view=mMatchupScore&scoringPeriodId={period}"
            elif 'view=mMatchup' not in redir:
                redir += f"&view=mMatchup&view=mMatchupScore&scoringPeriodId={period}"
            res = session.get(redir)
            
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list): data = data[0]
            schedule = data.get('schedule', [])
            for matchup in schedule:
                if matchup.get('matchupPeriodId', period) != period:
                    continue
                
                for side in ['home', 'away']:
                    if side in matchup:
                        team_id = matchup[side].get('teamId')
                        roster = matchup[side].get('rosterForCurrentScoringPeriod', {}).get('entries', [])
                        if not roster:
                            roster = matchup[side].get('rosterForMatchupPeriod', {}).get('entries', [])
                            
                        for entry in roster:
                            slot = entry.get('lineupSlotId')
                            if slot not in [20, 21]: # Active roster
                                stats_array = entry.get('playerPoolEntry', {}).get('player', {}).get('stats', [])
                                for stat_block in stats_array:
                                    if str(stat_block.get('scoringPeriodId')) == str(period) and stat_block.get('statSourceId') == 0:
                                        applied = stat_block.get('stats', {})
                                        for td_id in td_stat_ids:
                                            if td_id in applied:
                                                team_tds[team_id] += applied[td_id]
                                
    if team_tds:
        max_tds = -1
        max_team = None
        for tid, tds in team_tds.items():
            if tds > max_tds:
                max_tds = tds
                max_team = tid
        if max_team:
            results[year] = {
                'team_name': team_names[max_team],
                'touchdowns': max_tds,
                'final_rank': team_ranks[max_team]
            }

print("FINAL RESULTS:")
for y, info in results.items():
    if info['touchdowns'] > 0:
        print(f"Season {y}: {info['team_name']} had {int(info['touchdowns'])} TDs and finished rank {info['final_rank']}")
    else:
        print(f"Season {y}: (No matchup-level stats available)")
