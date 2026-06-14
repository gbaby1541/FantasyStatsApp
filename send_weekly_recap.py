import os
import json
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

LEAGUE_ID = os.getenv("LEAGUE_ID", "121269")
SEASON = os.getenv("SEASON", "2026")
ESPN_S2 = os.getenv("ESPN_S2")
SWID = os.getenv("SWID")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
RECIPIENT_EMAILS = os.getenv("RECIPIENT_EMAILS", "")

def get_espn_data():
    url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{SEASON}/segments/0/leagues/{LEAGUE_ID}?view=mMatchupScore&view=mTeam&view=mRoster&view=mSettings"
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

def process_data(data):
    # Determine the week that just finished
    # ESPN scoringPeriodId is usually the current/upcoming week
    scoring_period = data.get('scoringPeriodId', 1)
    matchup_period = scoring_period - 1
    
    if matchup_period < 1:
        matchup_period = 1 # Edge case

    # Extract teams
    teams = {}
    for team in data.get('teams', []):
        team_id = team['id']
        name = f"{team.get('location', '')} {team.get('nickname', '')}".strip()
        record = team.get('record', {}).get('overall', {})
        teams[team_id] = {
            'name': name,
            'wins': record.get('wins', 0),
            'losses': record.get('losses', 0),
            'ties': record.get('ties', 0),
            'points_for': record.get('pointsFor', 0.0),
        }

    # Process matchups for the selected week
    matchups = []
    week_high_score = 0
    high_scorer_team = "None"
    top_player = "None"
    top_player_score = 0
    
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
                
            matchups.append({
                'home_team': teams.get(home_team_id, {}).get('name', 'Unknown'),
                'home_score': home_score,
                'away_team': teams.get(away_team_id, {}).get('name', 'Unknown'),
                'away_score': away_score,
                'winner': winner
            })
            
            # Find the top player
            for side in [home, away]:
                roster = side.get('rosterForMatchupPeriod', {}).get('entries', [])
                for entry in roster:
                    # Slot 20 is Bench, 21 is IR. We only care about starters.
                    if entry.get('lineupSlotId') not in [20, 21]:
                        player_name = entry.get('playerPoolEntry', {}).get('player', {}).get('fullName', 'Unknown')
                        points = entry.get('playerPoolEntry', {}).get('appliedStatTotal', 0)
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
        'top_player_score': top_player_score
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
        model = genai.GenerativeModel('gemini-1.5-pro')
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
    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px;">
        <h1 style="color: #1a5f7a; text-align: center;">Fantasy Football Recap: Week {stats['week']}</h1>
        
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
            <h2 style="margin-top: 0; color: #d32f2f;">🌟 Weekly Superlatives 🌟</h2>
            <p><strong>Team of the Week:</strong> {stats['high_scorer_team']} ({stats['high_score']:.2f} pts)</p>
            <p><strong>Player of the Week:</strong> {stats['top_player']} ({stats['top_player_score']:.2f} pts)</p>
        </div>

        <div style="margin-bottom: 30px;">
            {ai_html}
        </div>
        
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
