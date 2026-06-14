#!/bin/bash
echo "const localLeagueData = {" > data.js
first=true
for year in 2023 2024; do
  if [ -f "data/${year}.json" ]; then
    if [ "$first" = true ]; then
      first=false
    else
      echo "," >> data.js
    fi
    content=$(cat "data/${year}.json")
    if [[ "$content" == [* ]]; then
      echo "\"$year\": $(echo "$content" | sed 's/^\[//;s/\]$//')" >> data.js
    else
      echo "\"$year\": $content" >> data.js
    fi
  fi
done
echo "};" >> data.js
