import json
with open('data.js') as f:
    js_content = f.read().replace('const localLeagueData = ', '')[:-2]
    local_data = json.loads(js_content)

for matchup in local_data['2023']['schedule']:
    for side in ['home', 'away']:
        if side in matchup:
            roster = matchup[side].get('rosterForCurrentScoringPeriod', {}).get('entries', [])
            if not roster:
                roster = matchup[side].get('rosterForMatchupPeriod', {}).get('entries', [])
            for entry in roster[:5]:
                player = entry['playerPoolEntry']['player']
                print(player['fullName'])
                for stat_block in player.get('stats', []):
                    if stat_block.get('statSourceId') == 0:
                        print("  scoringPeriodId:", stat_block.get('scoringPeriodId'), "stats:", stat_block.get('stats', {}))
    break
