import json

with open('data.js', 'r') as f:
    text = f.read()

# remove 'const localLeagueData = ' and ';\n'
text = text.replace('const localLeagueData = ', '').strip()
if text.endswith(';'):
    text = text[:-1]

data = json.loads(text)
year = list(data.keys())[0]
print("Keys in a team's record:", list(data[year]['teams'][0]['record'].keys()))
print("Matchup playoff types:", set([m.get('playoffTierType', 'NONE') for m in data[year]['schedule']]))
