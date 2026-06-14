const fs = require('fs');
const https = require('https');

const leagueId = "121269";
const years = Array.from({length: 15}, (_, i) => 2010 + i);

let dataContent = "const localLeagueData = {\n";
let completed = 0;

function fetchYear(year, isLast) {
    const url = `https://fantasy.espn.com/apis/v3/games/ffl/leagueHistory/${leagueId}?seasonId=${year}&view=mMatchupScore&view=mTeam`;
    
    https.get(url, { headers: { 'User-Agent': 'Mozilla/5.0' } }, (res) => {
        let body = '';
        res.on('data', chunk => body += chunk);
        res.on('end', () => {
            try {
                const json = JSON.parse(body);
                const payload = Array.isArray(json) ? json[0] : json;
                
                dataContent += `"${year}": ${JSON.stringify(payload)}`;
                if (!isLast) dataContent += ",\n";
                
                console.log(`Successfully fetched ${year}`);
            } catch (e) {
                console.log(`Failed parsing ${year}:`, e.message);
            }
            
            completed++;
            if (completed === years.length) {
                dataContent += "\n};\n";
                fs.writeFileSync('data.js', dataContent);
                console.log("Saved data.js");
            }
        });
    }).on('error', (e) => {
        console.log(`Failed request ${year}:`, e.message);
        completed++;
    });
}

years.forEach((year, index) => fetchYear(year, index === years.length - 1));
