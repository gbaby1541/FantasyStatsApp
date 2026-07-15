import json
with open('sample_matchup.json') as f:
    matchup = json.load(f)

for entry in matchup['home'].get('rosterForMatchupPeriod', {}).get('entries', []):
    player = entry['playerPoolEntry']['player']
    if player['defaultPositionId'] in [1, 2]: # QB or RB
        print(f"{player['fullName']} stats:")
        for stat_block in player.get('stats', []):
            if stat_block.get('statSourceId') == 0 and stat_block.get('statSplitTypeId') == 1:
                print("Period", stat_block.get('scoringPeriodId'), ":", stat_block.get('stats', {}))
