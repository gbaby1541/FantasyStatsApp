#!/bin/bash
echo "const localLeagueData = {" > data.js
first=true
for year in 2022 2023 2024; do
  echo "Fetching $year..."
  content=$(curl -s "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/$year/segments/0/leagues/121269?view=mMatchupScore&view=mTeam")
  
  if [[ "$content" == \{* ]]; then
    if [ "$first" = true ]; then
      first=false
    else
      echo "," >> data.js
    fi
    echo "\"$year\": $content" >> data.js
  fi
done
echo "};" >> data.js
