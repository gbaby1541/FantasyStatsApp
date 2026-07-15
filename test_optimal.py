def get_optimal_score(roster_entries, slot_limits):
    players = []
    for entry in roster_entries:
        player_info = entry.get('playerPoolEntry', {})
        points = player_info.get('appliedStatTotal', 0)
        eligible_slots = player_info.get('player', {}).get('eligibleSlots', [])
        players.append({'points': points, 'slots': eligible_slots, 'name': player_info.get('player', {}).get('fullName')})
    
    players.sort(key=lambda x: x['points'], reverse=True)
    
    filled_slots = {}
    active_slots = {}
    for slot_id_str, limit in slot_limits.items():
        slot_id = int(slot_id_str)
        if slot_id not in [20, 21, 24] and limit > 0:
            active_slots[slot_id] = limit
            filled_slots[slot_id] = 0
            
    total_score = 0
    assigned_players = []
    for p in players:
        # Prefer specific slots over FLEX (23), OP (33), etc.
        # Specific slots are usually < 20
        sorted_slots = sorted(p['slots'], key=lambda s: (s >= 20, s)) 
        for slot in sorted_slots:
            if slot in active_slots and filled_slots[slot] < active_slots[slot]:
                filled_slots[slot] += 1
                total_score += p['points']
                assigned_players.append(f"{p['name']} ({p['points']}) -> Slot {slot}")
                break
    return total_score, assigned_players

# Test data
slot_limits = {'0': 1, '1': 0, '2': 2, '3': 0, '4': 2, '5': 0, '6': 1, '7': 0, '20': 4, '21': 1, '23': 2}
roster = [
    {'playerPoolEntry': {'appliedStatTotal': 20.0, 'player': {'fullName': 'QB1', 'eligibleSlots': [0, 7, 20]}}},
    {'playerPoolEntry': {'appliedStatTotal': 15.0, 'player': {'fullName': 'RB1', 'eligibleSlots': [2, 23, 20]}}},
    {'playerPoolEntry': {'appliedStatTotal': 10.0, 'player': {'fullName': 'RB2', 'eligibleSlots': [2, 23, 20]}}},
    {'playerPoolEntry': {'appliedStatTotal': 18.0, 'player': {'fullName': 'WR1', 'eligibleSlots': [4, 23, 20]}}},
    {'playerPoolEntry': {'appliedStatTotal': 12.0, 'player': {'fullName': 'WR2', 'eligibleSlots': [4, 23, 20]}}},
    {'playerPoolEntry': {'appliedStatTotal': 14.0, 'player': {'fullName': 'WR3', 'eligibleSlots': [4, 23, 20]}}},
    {'playerPoolEntry': {'appliedStatTotal': 8.0, 'player': {'fullName': 'TE1', 'eligibleSlots': [6, 23, 20]}}},
    {'playerPoolEntry': {'appliedStatTotal': 16.0, 'player': {'fullName': 'TE2', 'eligibleSlots': [6, 23, 20]}}},
]

score, assignments = get_optimal_score(roster, slot_limits)
print("Optimal Score:", score)
for a in assignments:
    print(a)
