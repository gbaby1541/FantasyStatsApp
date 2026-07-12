import os
import json
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

def get_env_var(name, default_val):
    val = os.getenv(name)
    return val if val else default_val

LEAGUE_ID = get_env_var("LEAGUE_ID", "121269")
SEASON = get_env_var("SEASON", "2026")
ESPN_S2 = os.getenv("ESPN_S2")
SWID = os.getenv("SWID")
TEST_WEEK = os.getenv("TEST_WEEK")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SMTP_SERVER = get_env_var("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(get_env_var("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
RECIPIENT_EMAILS = os.getenv("RECIPIENT_EMAILS", "")
TEST_EMAIL = os.getenv("TEST_EMAIL")

if TEST_EMAIL:
    RECIPIENT_EMAILS = TEST_EMAIL

def get_espn_data():
    url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{SEASON}/segments/0/leagues/{LEAGUE_ID}?view=mMatchupScore&view=mTeam&view=mRoster&view=mSettings&view=mMatchup"
    if TEST_WEEK:
        url += f"&scoringPeriodId={TEST_WEEK}"
    headers = {}
    cookies = {}
    if ESPN_S2:
        cookies['espn_s2'] = ESPN_S2
    if SWID:
        cookies['swid'] = SWID
        
    response = requests.get(url, headers=headers, cookies=cookies)
    if response.status_code != 200:
        raise Exception(f"Error fetching data from ESPN: {response.status_code}\nResponse: {response.text}")
    return response.json()

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
    for p in players:
        sorted_slots = sorted(p['slots'], key=lambda s: (s >= 20, s)) 
        for slot in sorted_slots:
            if slot in active_slots and filled_slots[slot] < active_slots[slot]:
                filled_slots[slot] += 1
                total_score += p['points']
                break
    return total_score

def process_data(data):
    # Determine the week that just finished
    if TEST_WEEK:
        matchup_period = int(TEST_WEEK)
    else:
        # ESPN scoringPeriodId is usually the current/upcoming week
        scoring_period = data.get('scoringPeriodId', 1)
        matchup_period = scoring_period - 1
        
        if matchup_period < 1:
            matchup_period = 1 # Edge case

    # Extract teams
    teams = {}
    for team in data.get('teams', []):
        teams[team['id']] = {
            'name': team.get('name', team.get('location', 'Unknown') + ' ' + team.get('nickname', '')).strip(),
            'wins': team.get('record', {}).get('overall', {}).get('wins', 0),
            'losses': team.get('record', {}).get('overall', {}).get('losses', 0),
            'ties': team.get('record', {}).get('overall', {}).get('ties', 0),
            'points_for': team.get('record', {}).get('overall', {}).get('pointsFor', 0),
            'roster': team.get('roster', {})
        }

    # Process matchups for the selected week
    matchups = []
    week_high_score = 0
    high_scorer_team = "None"
    top_player = "None"
    top_player_score = 0
    
    biggest_margin = -1
    biggest_winner = "None"
    closest_margin = float('inf')
    closest_winner = "None"
    best_waiver_player = "None"
    best_waiver_score = 0
    
    slot_limits = data.get('settings', {}).get('rosterSettings', {}).get('lineupSlotCounts', {})
    
    for game in data.get('schedule', []):
        if game.get('matchupPeriodId') == matchup_period:
            home = game.get('home', {})
            away = game.get('away', {})
            
            home_team_id = home.get('teamId')
            away_team_id = away.get('teamId')
            
            home_score = home.get('totalPoints', 0)
            away_score = away.get('totalPoints', 0)
            
            if home_score > week_high_score:
                week_high_score = home_score
                high_scorer_team = teams.get(home_team_id, {}).get('name', 'Unknown')
                
            if away_score > week_high_score:
                week_high_score = away_score
                high_scorer_team = teams.get(away_team_id, {}).get('name', 'Unknown')
                
            winner_id = game.get('winner')
            if winner_id == 'HOME':
                winner = teams.get(home_team_id, {}).get('name', 'Unknown')
            elif winner_id == 'AWAY':
                winner = teams.get(away_team_id, {}).get('name', 'Unknown')
            else:
                winner = 'Tie'
                
            margin = abs(home_score - away_score)
            if margin > biggest_margin:
                biggest_margin = margin
                biggest_winner = winner if winner != 'Tie' else "Tie"
            if margin < closest_margin:
                closest_margin = margin
                closest_winner = winner if winner != 'Tie' else "Tie"
                
            home_roster = teams.get(home_team_id, {}).get('roster', {}).get('entries', [])
            away_roster = teams.get(away_team_id, {}).get('roster', {}).get('entries', [])
            
            home_optimal = get_optimal_score(home_roster, slot_limits)
            away_optimal = get_optimal_score(away_roster, slot_limits)
                
            matchups.append({
                'home_team': teams.get(home_team_id, {}).get('name', 'Unknown'),
                'home_score': home_score,
                'home_optimal': home_optimal,
                'away_team': teams.get(away_team_id, {}).get('name', 'Unknown'),
                'away_score': away_score,
                'away_optimal': away_optimal,
                'winner': winner
            })
            
            # Find the top player and best waiver
            for side_roster in [home_roster, away_roster]:
                for entry in side_roster:
                    player_name = entry.get('playerPoolEntry', {}).get('player', {}).get('fullName', 'Unknown')
                    points = entry.get('playerPoolEntry', {}).get('appliedStatTotal', 0)
                    acq_type = entry.get('acquisitionType')
                    
                    if acq_type in ['WAIVER', 'FREEAGENT']:
                        if points > best_waiver_score:
                            best_waiver_score = points
                            best_waiver_player = player_name
                            
                    # Slot 20 is Bench, 21 is IR. We only care about starters for Top Player.
                    if entry.get('lineupSlotId') not in [20, 21, 24]:
                        if points > top_player_score:
                            top_player_score = points
                            top_player = player_name
                            
    # Calculate standings
    standings = sorted(teams.values(), key=lambda x: (x['wins'], x['points_for']), reverse=True)
    
    return {
        'week': matchup_period,
        'matchups': matchups,
        'standings': standings,
        'high_scorer_team': high_scorer_team,
        'high_score': week_high_score,
        'top_player': top_player,
        'top_player_score': top_player_score,
        'biggest_winner': biggest_winner,
        'biggest_margin': biggest_margin,
        'closest_winner': closest_winner,
        'closest_margin': closest_margin,
        'best_waiver_player': best_waiver_player,
        'best_waiver_score': best_waiver_score
    }

def generate_summary_with_ai(stats):
    if not GEMINI_API_KEY:
        print("Warning: GEMINI_API_KEY not found. Skipping AI summary.")
        return "<p><em>AI Summary unavailable (No API Key).</em></p>"
        
    genai.configure(api_key=GEMINI_API_KEY)
    
    prompt = f"""
    You are a fantasy football commissioner writing a fun, engaging, and slightly competitive weekly recap email to your league.
    It is currently Week {stats['week']} of the fantasy season.
    
    Here is the data for this week's matchups:
    {json.dumps(stats['matchups'], indent=2)}
    
    The highest scoring team this week was {stats['high_scorer_team']} with {stats['high_score']} points.
    The top scoring starting player in the league was {stats['top_player']} with {stats['top_player_score']} points.
    
    Please write:
    1. A custom, fun introduction (1-2 paragraphs).
    2. A short (2-3 sentences) witty and entertaining summary for EACH matchup, roasting the loser slightly or praising a close win.
    
    Format the output as clean HTML (without markdown codeblock wrappers like ```html). Use <h2>, <h3>, <p>, and <strong> tags where appropriate. Do NOT include the current standings or the raw stats at the bottom, I will append those myself.
    """
    
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        text = response.text
        if text.startswith("```html"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return "<p><em>Error generating AI summary.</em></p>"

def build_email_html(stats, ai_html):
    scoreboard_html = f"""
        <div style="text-align: center; margin-bottom: 20px;">
            <a href="https://gbaby1541.github.io/FantasyStatsApp/" style="display: inline-block; padding: 12px 24px; background-color: #238636; color: white; text-decoration: none; font-weight: bold; border-radius: 6px; font-size: 16px;">Click Here for the Fantasy companion app</a>
        </div>
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
            <h2 style="margin-top: 0; color: #1a5f7a;">🏈 Week {stats['week']} Scoreboard 🏈</h2>
            <ul style="list-style-type: none; padding-left: 0; margin-bottom: 0;">
    """
    for m in stats['matchups']:
        home_bold = "<strong>" if m['winner'] == m['home_team'] else ""
        home_end = "</strong>" if m['winner'] == m['home_team'] else ""
        away_bold = "<strong>" if m['winner'] == m['away_team'] else ""
        away_end = "</strong>" if m['winner'] == m['away_team'] else ""
        
        # Only show optimal if it would have changed a loss/tie to a win
        home_opt_str = f" | Opt: {m['home_optimal']:.2f}" if m['home_optimal'] > m['away_score'] and m['home_score'] <= m['away_score'] else ""
        away_opt_str = f" | Opt: {m['away_optimal']:.2f}" if m['away_optimal'] > m['home_score'] and m['away_score'] <= m['home_score'] else ""
        
        scoreboard_html += f"""
                <li style="margin-bottom: 10px; border-bottom: 1px solid #dee2e6; padding-bottom: 10px;">
                    {away_bold}{m['away_team']}{away_end} ({m['away_score']:.2f} pts{away_opt_str}) 
                    <br>vs<br> 
                    {home_bold}{m['home_team']}{home_end} ({m['home_score']:.2f} pts{home_opt_str})
                </li>
        """
    scoreboard_html += """
            </ul>
        </div>
    """

    waiver_text = f"{stats['best_waiver_player']} ({stats['best_waiver_score']:.2f} pts)" if stats['best_waiver_score'] > 0 else "None (No recent transaction data)"

    changed_matchups = []
    for m in stats['matchups']:
        actual_winner = "Home" if m['home_score'] > m['away_score'] else ("Away" if m['away_score'] > m['home_score'] else "Tie")
        optimal_winner = "Home" if m['home_optimal'] > m['away_optimal'] else ("Away" if m['away_optimal'] > m['home_optimal'] else "Tie")
        
        if actual_winner != optimal_winner:
            winner_team = m['home_team'] if optimal_winner == "Home" else (m['away_team'] if optimal_winner == "Away" else "Tie")
            loser_team = m['away_team'] if optimal_winner == "Home" else (m['home_team'] if optimal_winner == "Away" else "Tie")
            winner_score = m['home_optimal'] if optimal_winner == "Home" else m['away_optimal']
            loser_score = m['away_optimal'] if optimal_winner == "Home" else m['home_optimal']
            
            if optimal_winner != "Tie":
                changed_matchups.append(f"<li style='margin-bottom: 5px;'><strong>{winner_team}</strong> would have beaten {loser_team} (<strong>{winner_score:.2f}</strong> to {loser_score:.2f})</li>")
            else:
                changed_matchups.append(f"<li style='margin-bottom: 5px;'><strong>{winner_team}</strong> and {loser_team} would have tied ({winner_score:.2f} to {loser_score:.2f})</li>")

    if changed_matchups:
        optimal_html = f"""
        <div style="background-color: #fff3cd; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 5px solid #ffc107;">
            <h2 style="margin-top: 0; color: #856404; font-size: 18px;">🤔 Would any matchups be different if each team set their optimal lineup? 🤔</h2>
            <ul style="margin-bottom: 0;">
                {''.join(changed_matchups)}
            </ul>
        </div>
        """
    else:
        optimal_html = f"""
        <div style="background-color: #fff3cd; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 5px solid #ffc107;">
            <h2 style="margin-top: 0; color: #856404; font-size: 18px;">🤔 Would any matchups be different if each team set their optimal lineup? 🤔</h2>
            <p style="margin-bottom: 0; color: #856404;">Not this week!</p>
        </div>
        """

    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px;">
        <h1 style="color: #1a5f7a; text-align: center;">Fantasy Football Recap: Week {stats['week']}</h1>
        
        {scoreboard_html}
        
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
            <h2 style="margin-top: 0; color: #d32f2f;">🌟 Weekly Superlatives 🌟</h2>
            <p><strong>Team of the Week:</strong> {stats['high_scorer_team']} ({stats['high_score']:.2f} pts)</p>
            <p><strong>Player of the Week:</strong> {stats['top_player']} ({stats['top_player_score']:.2f} pts)</p>
            <p><strong>Biggest Winner:</strong> {stats['biggest_winner']} (Won by {stats['biggest_margin']:.2f} pts)</p>
            <p><strong>Closest Nail-biter:</strong> {stats['closest_winner']} (Won by {stats['closest_margin']:.2f} pts)</p>
            <p><strong>Best Waiver Wire Pickup:</strong> {waiver_text}</p>
        </div>

        <div style="margin-bottom: 30px;">
            {ai_html}
        </div>
        
        {optimal_html}
        
        <div style="background-color: #e9ecef; padding: 20px; border-radius: 8px;">
            <h2 style="margin-top: 0; color: #1a5f7a;">🏆 Current Standings 🏆</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr style="background-color: #dee2e6; text-align: left;">
                    <th style="padding: 10px; border-bottom: 2px solid #ccc;">Rank</th>
                    <th style="padding: 10px; border-bottom: 2px solid #ccc;">Team</th>
                    <th style="padding: 10px; border-bottom: 2px solid #ccc;">Record</th>
                    <th style="padding: 10px; border-bottom: 2px solid #ccc;">PF</th>
                </tr>
    """
    
    for idx, team in enumerate(stats['standings']):
        record_str = f"{team['wins']}-{team['losses']}-{team['ties']}"
        row_bg = "#ffffff" if idx % 2 == 0 else "#f8f9fa"
        html += f"""
                <tr style="background-color: {row_bg};">
                    <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>{idx + 1}</strong></td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee;">{team['name']}</td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee;">{record_str}</td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee;">{team['points_for']:.2f}</td>
                </tr>
        """
        
    html += """
            </table>
        </div>
        <p style="text-align: center; font-size: 12px; color: #777; margin-top: 30px;">
            Automated via AntiGravity App
        </p>
      </body>
    </html>
    """
    return html

def send_email(subject, html_content):
    if not all([SMTP_SERVER, SMTP_USERNAME, SMTP_PASSWORD, SENDER_EMAIL, RECIPIENT_EMAILS]):
        print("Missing email configuration. Cannot send email.")
        print("--- Email Content Preview ---")
        print(html_content)
        return
        
    recipients = [email.strip() for email in RECIPIENT_EMAILS.split(',') if email.strip()]
    
    msg = MIMEMultipart("alternative")
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = ", ".join(recipients)
    
    msg.attach(MIMEText(html_content, "html"))
    
    try:
        print(f"Connecting to SMTP server {SMTP_SERVER}:{SMTP_PORT}...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SENDER_EMAIL, recipients, msg.as_string())
        server.quit()
        print(f"Successfully sent email to {len(recipients)} recipients!")
    except Exception as e:
        print(f"Failed to send email: {e}")

def main():
    try:
        print("Fetching data from ESPN...")
        raw_data = get_espn_data()
        
        print("Processing stats...")
        stats = process_data(raw_data)
        
        if not stats.get('matchups'):
            print("No completed matchups found. The season hasn't started yet. Exiting gracefully.")
            return
        
        print(f"Generating AI recap for Week {stats['week']}...")
        ai_html = generate_summary_with_ai(stats)
        
        print("Building email HTML...")
        email_html = build_email_html(stats, ai_html)
        
        subject = f"Fantasy Football Recap: Week {stats['week']}"
        
        print("Dispatching email...")
        send_email(subject, email_html)
        print("Done!")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
