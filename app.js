// --- CONFIGURATION ---
const LEAGUE_ID = "121269"; // Your ESPN League ID
const currentYear = new Date().getFullYear();

// --- STATE CONTAINERS ---
let leagueData = {}; // Store raw data mapped by year
let allTeams = new Map(); // Store distinct team profiles (teams often change names, map by teamId)
let allMembers = new Map(); // Store distinct member profiles
let allTimeRecords = {}; // Aggregate W/L/T
let headToHeadRecords = {}; // Matchups Map -> teamId -> opponentId -> stats
let champions = []; // Array of championship objects
let highestWeeklyScores = [];
let highestMargins = [];
let regularSeasonWins = [];
let highestSeasonPoints = [];

let currentSortColumn = 'winPct';
let currentSortDirection = 'desc';
let csSortColumn = 'w';
let csSortDirection = 'desc';

// --- DOM ELEMENTS ---
const loadingOverlay = document.getElementById('loading-overlay');
const recordsTableBody = document.getElementById('records-body');
const yearSelect = document.getElementById('year-select');
const startYearDisplay = document.getElementById('start-year-display');
const team1Select = document.getElementById('team1-select');
const team2Select = document.getElementById('team2-select');
const currentSeasonBody = document.getElementById('current-season-body');
const currentSeasonChartCanvas = document.getElementById('current-season-chart');
let currentSeasonChart = null;
const h2hResults = document.getElementById('h2h-results');
const championsGrid = document.getElementById('champions-grid');
const tabButtons = document.querySelectorAll('.tab-btn');
const tabContents = document.querySelectorAll('.tab-content');
const ownerList = document.getElementById('owner-list');
const ownerProfileSection = document.getElementById('owner-profile');
const ownerProfileName = document.getElementById('owner-profile-name');

// --- INITIALIZATION ---
function initApp() {
    const availableYears = Object.keys(localLeagueData).sort();
    const START_YEAR = availableYears.length > 0 ? availableYears[0] : 2024;
    if (startYearDisplay) {
        startYearDisplay.textContent = START_YEAR;
    }

    try {
        // Map native object to expected leagueData structure
        for (const [year, data] of Object.entries(localLeagueData)) {
            const yearData = Array.isArray(data) ? data[0] : data;
            if (yearData && yearData.teams) {
                leagueData[year] = yearData;
            }
        }

        processAggregates();
        populateUI();
        renderSidebar();
        
        // Handle URL Hash for default page load
        const hash = window.location.hash.replace('#', '');
        if (hash.startsWith('owner-')) {
            const teamId = hash.replace('owner-', '');
            // Highlight the sidebar item
            setTimeout(() => {
                const listItems = Array.from(document.querySelectorAll('.owner-list li'));
                const matchedLi = listItems.find(li => {
                    const t = allTeams.get(teamId);
                    return t && li.textContent === t.displayName;
                });
                showOwnerPage(teamId, matchedLi);
            }, 50);
        } else if (hash) {
            switchTab(hash);
        } else {
            // Default page if no hash
            switchTab('current-season');
        }

        // Hide loading and show modal
        setTimeout(() => {
            loadingOverlay.classList.add('hidden');
            
            // Show welcome modal if not shown this session
            if (!sessionStorage.getItem('welcomeShown')) {
                const welcomeOverlay = document.getElementById('welcome-modal-overlay');
                if (welcomeOverlay) {
                    welcomeOverlay.classList.add('active');
                    sessionStorage.setItem('welcomeShown', 'true');
                }
            }
        }, 500);

    } catch (e) {
        console.error("Error processing data:", e);
        loadingOverlay.innerHTML = `
            <div style="text-align:center;">
                <h2 style="color:var(--danger);margin-bottom:1rem;">Failed to Load Data</h2>
                <p>An error occurred processing the data payload.</p>
                <p style="font-size:0.8rem;margin-top:1rem;color:var(--text-secondary)">${e.message}</p>
                 <button onclick="location.reload()" style="margin-top:2rem;padding:0.5rem 1rem;background:var(--card-bg);color:#fff;border:1px solid var(--border-color);border-radius:4px;cursor:pointer;">Retry</button>
            </div>
        `;
    }
}

// --- MODAL LOGIC ---
document.addEventListener('DOMContentLoaded', () => {
    const welcomeOverlay = document.getElementById('welcome-modal-overlay');
    const welcomeClose = document.getElementById('welcome-modal-close');
    
    if (welcomeClose && welcomeOverlay) {
        welcomeClose.addEventListener('click', () => {
            welcomeOverlay.classList.remove('active');
        });
        
        // Also close if they click outside the modal box
        welcomeOverlay.addEventListener('click', (e) => {
            if (e.target === welcomeOverlay) {
                welcomeOverlay.classList.remove('active');
            }
        });
    }
});

// --- TAB SWITCHING LOGIC ---
function switchTab(tabId) {
    const targetBtn = Array.from(tabButtons).find(b => b.dataset.tab === tabId);
    if (!targetBtn) return;
    
    tabButtons.forEach(b => b.classList.remove('active'));
    tabContents.forEach(c => c.classList.remove('active'));
    document.querySelectorAll('.owner-list li').forEach(li => li.classList.remove('active'));

    targetBtn.classList.add('active');
    const content = document.getElementById(tabId);
    if (content) content.classList.add('active');
    
    const ownerProfile = document.getElementById('owner-profile');
    if (ownerProfile && tabId !== 'owner-profile') {
        ownerProfile.classList.remove('active');
    }
}

tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        const tabId = btn.dataset.tab;
        switchTab(tabId);
        window.location.hash = tabId;
    });
});

window.addEventListener('hashchange', () => {
    const hash = window.location.hash.replace('#', '');
    if (hash.startsWith('owner-')) {
        const teamId = hash.replace('owner-', '');
        const listItems = Array.from(document.querySelectorAll('.owner-list li'));
        const matchedLi = listItems.find(li => {
            const t = allTeams.get(teamId);
            return t && li.textContent === t.displayName;
        });
        showOwnerPage(teamId, matchedLi);
    } else if (hash) {
        switchTab(hash);
    }
});

// --- SIDEBAR TOGGLE LOGIC ---
const ownersToggle = document.getElementById('owners-toggle');
const ownersContent = document.getElementById('owners-content');
const ownersToggleIcon = document.getElementById('owners-toggle-icon');

if (ownersToggle && ownersContent && ownersToggleIcon) {
    ownersToggle.addEventListener('click', () => {
        if (ownersContent.style.display === 'none') {
            ownersContent.style.display = 'block';
            ownersToggleIcon.textContent = '−';
        } else {
            ownersContent.style.display = 'none';
            ownersToggleIcon.textContent = '+';
        }
    });
}

// --- SIDEBAR & ROUTING ---
function renderSidebar() {
    if(!ownerList) return;
    ownerList.innerHTML = '';
    const teamArray = Array.from(allTeams.values()).sort((a, b) => a.displayName.localeCompare(b.displayName));
    
    teamArray.forEach(team => {
        const li = document.createElement('li');
        li.textContent = team.displayName;
        li.addEventListener('click', () => showOwnerPage(team.id, li));
        ownerList.appendChild(li);
    });
}

function showOwnerPage(teamId, clickedLi) {
    // Hide standard tabs
    tabButtons.forEach(b => b.classList.remove('active'));
    tabContents.forEach(c => c.classList.remove('active'));
    
    // Highlight sidebar
    document.querySelectorAll('.owner-list li').forEach(li => li.classList.remove('active'));
    if(clickedLi) clickedLi.classList.add('active');

    // Show owner profile section
    if(ownerProfileSection) ownerProfileSection.classList.add('active');
    
    // Update URL hash without triggering endless loop
    if (window.location.hash !== `#owner-${teamId}`) {
        window.history.pushState(null, null, `#owner-${teamId}`);
    }
    
    // Populate basic info
    const team = allTeams.get(teamId);
    if(!team) return;
    if(ownerProfileName) {
        ownerProfileName.textContent = team.displayName;
    }

    // --- Current Season Data ---
    const sortedYears = Object.keys(leagueData).sort().reverse();
    const currentYear = sortedYears[0];
    const currentData = leagueData[currentYear];
    const currentYearSpan = document.getElementById('owner-current-year');
    if(currentYearSpan) currentYearSpan.textContent = currentYear;

    let cW=0, cL=0, cT=0, cPF=0, cPA=0;
    if(currentData && currentData.teams) {
        const cTeam = currentData.teams.find(t => t.franchiseId === teamId);
        if(cTeam && cTeam.record && cTeam.record.overall) {
            cW = cTeam.record.overall.wins;
            cL = cTeam.record.overall.losses;
            cT = cTeam.record.overall.ties;
            cPF = cTeam.record.overall.pointsFor;
            cPA = cTeam.record.overall.pointsAgainst;
        }
    }
    const cGames = cW + cL + cT;
    const cMargin = cGames > 0 ? (cPF - cPA) / cGames : 0;

    const el = (id) => document.getElementById(id);
    if(el('owner-current-record')) el('owner-current-record').textContent = `${cW}-${cL}-${cT}`;
    if(el('owner-current-pf')) el('owner-current-pf').textContent = cPF.toFixed(1);
    if(el('owner-current-pa')) el('owner-current-pa').textContent = cPA.toFixed(1);
    
    const currentMarginEl = el('owner-current-margin');
    if (currentMarginEl) {
        if (cMargin > 0) {
            currentMarginEl.textContent = `+${cMargin.toFixed(1)}`;
            currentMarginEl.className = 'text-green';
        } else if (cMargin < 0) {
            currentMarginEl.textContent = `${cMargin.toFixed(1)}`;
            currentMarginEl.className = 'text-red';
        } else {
            currentMarginEl.textContent = '0.0';
            currentMarginEl.className = '';
        }
    }

    // --- Historical Data ---
    const stats = allTimeRecords[teamId] || { w:0, l:0, t:0, pf:0, pa:0, playoffW:0, playoffL:0, playoffPF:0, playoffPA:0 };
    const hGames = stats.w + stats.l + stats.t;
    const hMargin = hGames > 0 ? (stats.pf - stats.pa) / hGames : 0;

    if(el('owner-all-record')) el('owner-all-record').textContent = `${stats.w}-${stats.l}-${stats.t}`;
    if(el('owner-all-pf')) el('owner-all-pf').textContent = stats.pf.toFixed(1);
    if(el('owner-all-pa')) el('owner-all-pa').textContent = stats.pa.toFixed(1);
    
    const allMarginEl = el('owner-all-margin');
    if (allMarginEl) {
        if (hMargin > 0) {
            allMarginEl.textContent = `+${hMargin.toFixed(1)}`;
            allMarginEl.className = 'text-green';
        } else if (hMargin < 0) {
            allMarginEl.textContent = `${hMargin.toFixed(1)}`;
            allMarginEl.className = 'text-red';
        } else {
            allMarginEl.textContent = '0.0';
            allMarginEl.className = '';
        }
    }

    // Playoff Data
    const pGames = stats.playoffW + stats.playoffL;
    const pMargin = pGames > 0 ? (stats.playoffPF - stats.playoffPA) / pGames : 0;
    
    if(el('owner-playoff-record')) el('owner-playoff-record').textContent = `${stats.playoffW}-${stats.playoffL}`;
    if(el('owner-playoff-points')) el('owner-playoff-points').textContent = `${stats.playoffPF.toFixed(1)} / ${stats.playoffPA.toFixed(1)}`;
    
    const playoffMarginEl = el('owner-playoff-margin');
    if (playoffMarginEl) {
        if (pMargin > 0) {
            playoffMarginEl.textContent = `+${pMargin.toFixed(1)}`;
            playoffMarginEl.className = 'text-green';
        } else if (pMargin < 0) {
            playoffMarginEl.textContent = `${pMargin.toFixed(1)}`;
            playoffMarginEl.className = 'text-red';
        } else {
            playoffMarginEl.textContent = '0.0';
            playoffMarginEl.className = '';
        }
    }
}

// --- DATA PROCESSING ---
function processAggregates() {
    const years = Object.keys(leagueData).sort();

    years.forEach(year => {
        const data = leagueData[year];
        const { teams, schedule, members } = data;

        // 0. Store/Update Member Profiles
        if (members) {
            members.forEach(member => {
                allMembers.set(member.id, `${member.firstName} ${member.lastName}`.trim());
            });
        }

        const yearFranchiseMap = new Map();
        let seasonWinsTracker = {}; // track per-season regular wins
        let seasonPointsTracker = {}; // track per-season regular points
        let seasonPlayoffWinsTracker = {};
        let seasonPlayoffLossTracker = {};

        // 1. Store/Update Team Profiles (Teams change names, use most recent)
        teams.forEach(team => {
            const ownerId = team.owners?.[0];
            let ownerName = ownerId ? (allMembers.get(ownerId) || 'Unknown') : 'Unknown';

            // Identity Normalizations
            const lowerName = ownerName.toLowerCase();
            if (lowerName === "b a") ownerName = "Blair Adams";
            if (lowerName === "t balkus" || lowerName === "tim balkus") ownerName = "Tim Balkus";
            if (lowerName === "chuck hutson" || lowerName === "charles hutson") ownerName = "Charles Hutson";

            const franchiseId = ownerName !== 'Unknown' ? ownerName : `team-${team.id}`;
            const displayName = ownerName; // Per user request, strip team names entirely!

            team.franchiseId = franchiseId;
            yearFranchiseMap.set(team.id, franchiseId);

            allTeams.set(franchiseId, {
                id: franchiseId,
                name: ownerName,
                displayName: displayName,
                abbrev: team.abbrev,
                logo: team.logo || 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/default-team-logo-500.png',
                owners: team.owners // Array of owner IDs
            });

            // Initialize allTime records
            if (!allTimeRecords[franchiseId]) {
                allTimeRecords[franchiseId] = { w: 0, l: 0, t: 0, pf: 0, pa: 0, playoffs: 0, finals: 0, playoffW: 0, playoffL: 0, playoffPF: 0, playoffPA: 0 };
            }
            if (team.rankCalculatedFinal <= 6) allTimeRecords[franchiseId].playoffs += 1;
            if (team.rankCalculatedFinal <= 2) allTimeRecords[franchiseId].finals += 1;
            if (!headToHeadRecords[franchiseId]) {
                headToHeadRecords[franchiseId] = {};
            }
        });

        // 2. Process All-Time and H2H from Schedule
        if (schedule) {
            schedule.forEach(matchup => {
                // Regular season or playoff games with scores
                if (matchup.away && matchup.home && matchup.winner !== "UNDECIDED") {
                    const homeId = yearFranchiseMap.get(matchup.home.teamId);
                    const awayId = yearFranchiseMap.get(matchup.away.teamId);

                    const homeScore = matchup.home.totalPoints;
                    const awayScore = matchup.away.totalPoints;

                    // Identify winner
                    const homeWon = matchup.winner === "HOME";
                    const awayWon = matchup.winner === "AWAY";
                    const isTie = matchup.winner === "TIE";

                    // REGULAR SEASON TRACKER
                    if (matchup.playoffTierType === "NONE") {
                        if (homeWon) {
                            seasonWinsTracker[homeId] = (seasonWinsTracker[homeId] || 0) + 1;
                        } else if (awayWon) {
                            seasonWinsTracker[awayId] = (seasonWinsTracker[awayId] || 0) + 1;
                        }
                        seasonPointsTracker[homeId] = (seasonPointsTracker[homeId] || 0) + homeScore;
                        seasonPointsTracker[awayId] = (seasonPointsTracker[awayId] || 0) + awayScore;
                    }

                    // WEEKLY SCORES
                    highestWeeklyScores.push({ teamId: homeId, year: year, score: homeScore, opponentId: awayId });
                    highestWeeklyScores.push({ teamId: awayId, year: year, score: awayScore, opponentId: homeId });

                    // MARGINS
                    const margin = Math.abs(homeScore - awayScore);
                    const winnerScore = homeWon ? homeScore : awayScore;
                    const loserScore = homeWon ? awayScore : homeScore;
                    const winningTeamId = homeWon ? homeId : awayId;
                    const losingTeamId = homeWon ? awayId : homeId;

                    if (homeWon || awayWon) {
                        highestMargins.push({
                            winnerId: winningTeamId,
                            loserId: losingTeamId,
                            year: year,
                            margin: margin,
                            winnerScore: winnerScore,
                            loserScore: loserScore
                        });
                    }

                    // Update All Time Stats
                    allTimeRecords[homeId].pf += homeScore;
                    allTimeRecords[homeId].pa += awayScore;
                    allTimeRecords[awayId].pf += awayScore;
                    allTimeRecords[awayId].pa += homeScore;

                    if (homeWon) {
                        allTimeRecords[homeId].w += 1;
                        allTimeRecords[awayId].l += 1;
                        recordH2H(homeId, awayId, true, false, homeScore, awayScore);
                    } else if (awayWon) {
                        allTimeRecords[awayId].w += 1;
                        allTimeRecords[homeId].l += 1;
                        recordH2H(awayId, homeId, true, false, awayScore, homeScore);
                    } else if (isTie) {
                        allTimeRecords[homeId].t += 1;
                        allTimeRecords[awayId].t += 1;
                        recordH2H(homeId, awayId, false, true, homeScore, awayScore);
                        recordH2H(awayId, homeId, false, true, awayScore, homeScore);
                    }

                    if (matchup.playoffTierType === "WINNERS_BRACKET") {
                        allTimeRecords[homeId].playoffPF += homeScore;
                        allTimeRecords[homeId].playoffPA += awayScore;
                        allTimeRecords[awayId].playoffPF += awayScore;
                        allTimeRecords[awayId].playoffPA += homeScore;

                        if (homeWon) {
                            seasonPlayoffWinsTracker[homeId] = (seasonPlayoffWinsTracker[homeId] || 0) + 1;
                            seasonPlayoffLossTracker[awayId] = (seasonPlayoffLossTracker[awayId] || 0) + 1;
                            allTimeRecords[homeId].playoffW += 1;
                            allTimeRecords[awayId].playoffL += 1;
                        } else if (awayWon) {
                            seasonPlayoffWinsTracker[awayId] = (seasonPlayoffWinsTracker[awayId] || 0) + 1;
                            seasonPlayoffLossTracker[homeId] = (seasonPlayoffLossTracker[homeId] || 0) + 1;
                            allTimeRecords[awayId].playoffW += 1;
                            allTimeRecords[homeId].playoffL += 1;
                        }
                    }

                    // Special Case: Playoff Championship Game
                    if (matchup.playoffTierType === "WINNERS_BRACKET" && matchup.matchupPeriodId === data.status?.finalScoringPeriod) {
                        // Some logic identifies the exact championship game based on matchup characteristics
                        // In ESPN, the final winner bracket game between the last two remaining is the championship.
                    }
                }
            });
        }

        // STORE SEASON WINS & POINTS
        Object.keys(seasonWinsTracker).forEach(teamId => {
            regularSeasonWins.push({
                year: year,
                teamId: teamId,
                wins: seasonWinsTracker[teamId]
            });
            if (seasonPointsTracker[teamId]) {
                highestSeasonPoints.push({
                    year: year,
                    teamId: teamId,
                    points: seasonPointsTracker[teamId]
                });
            }
        });

        data.playoffStats = { wins: seasonPlayoffWinsTracker, losses: seasonPlayoffLossTracker };

        // 3. Process Champions (Alternative, easier method via final standings if available)
        // 3. Process Champions
        const champ = teams.find(t => t.rankCalculatedFinal === 1);
        if (champ) {
            // Find runner up
            const runnerUp = teams.find(t => t.rankCalculatedFinal === 2);
            champions.push({
                year: year,
                teamId: yearFranchiseMap.get(champ.id),
                runnerUpId: runnerUp ? yearFranchiseMap.get(runnerUp.id) : null,
                w: champ.record.overall.wins,
                l: champ.record.overall.losses
            });
        }
    });
}

function recordH2H(winnerId, loserId, won, tied, winnerScore, loserScore) {
    if (!headToHeadRecords[winnerId][loserId]) headToHeadRecords[winnerId][loserId] = { w: 0, l: 0, t: 0, pf: 0, pa: 0 };
    if (!headToHeadRecords[loserId][winnerId]) headToHeadRecords[loserId][winnerId] = { w: 0, l: 0, t: 0, pf: 0, pa: 0 };

    if (won) {
        headToHeadRecords[winnerId][loserId].w += 1;
        headToHeadRecords[loserId][winnerId].l += 1;
    } else if (tied) {
        headToHeadRecords[winnerId][loserId].t += 1;
        headToHeadRecords[loserId][winnerId].t += 1;
    }

    headToHeadRecords[winnerId][loserId].pf += winnerScore;
    headToHeadRecords[winnerId][loserId].pa += loserScore;

    headToHeadRecords[loserId][winnerId].pf += loserScore;
    headToHeadRecords[loserId][winnerId].pa += winnerScore;
}

// --- UI POPULATION ---
function populateUI() {
    // 1. Populate Dropdowns
    const validYears = Object.keys(leagueData).sort().reverse();
    validYears.forEach(year => {
        const opt = document.createElement('option');
        opt.value = year;
        opt.textContent = `${year} Season`;
        yearSelect.appendChild(opt);
    });

    const teamArray = Array.from(allTeams.values()).sort((a, b) => a.displayName.localeCompare(b.displayName));
    teamArray.forEach(team => {
        const opt1 = document.createElement('option');
        opt1.value = team.id;
        opt1.textContent = team.displayName;
        team1Select.appendChild(opt1);
        const opt2 = document.createElement('option');
        opt2.value = team.id;
        opt2.textContent = team.displayName;
        team2Select.appendChild(opt2);
    });

    // Set team 2 to second option if exists
    if (teamArray.length > 1) {
        team2Select.value = teamArray[1].id;
    }

    // 2. Render Initial Tables
    setupSortListeners();
    renderRecords('all-time');
    renderH2H();
    renderChampions();
    renderAllTimeRecords();
    renderCurrentSeason();

    // 3. Listeners
    yearSelect.addEventListener('change', (e) => renderRecords(e.target.value));
    team1Select.addEventListener('change', renderH2H);
    team2Select.addEventListener('change', renderH2H);
}

function renderRecords(year) {
    recordsTableBody.innerHTML = '';
    let rowData = [];

    if (year === 'all-time') {
        // Build all-time rows
        Object.keys(allTimeRecords).forEach(teamId => {
            const stats = allTimeRecords[teamId];
            const totalGames = stats.w + stats.l + stats.t;
            if (totalGames === 0) return; // Skip teams with no history

            const winPct = (stats.w + (stats.t * 0.5)) / totalGames;
            const champsCount = champions.filter(c => c.teamId === teamId).length;

            rowData.push({
                teamId: teamId, // now a string id
                w: stats.w,
                l: stats.l,
                t: stats.t,
                winPct: winPct,
                pf: stats.pf,
                pa: stats.pa,
                playoffRecord: `${stats.playoffW}-${stats.playoffL}`,
                playoffW: stats.playoffW,
                playoffs: stats.playoffs,
                finals: stats.finals,
                champs: champsCount
            });
        });
    } else {
        // Build specific year rows
        const data = leagueData[year];
        if (!data || !data.teams) return;

        const pStats = data.playoffStats || { wins: {}, losses: {} };
        data.teams.forEach(t => {
            const rec = t.record.overall;
            const champsCount = champions.filter(c => c.teamId === t.franchiseId).length;
            const pW = pStats.wins[t.franchiseId] || 0;
            const pL = pStats.losses[t.franchiseId] || 0;

            rowData.push({
                teamId: t.franchiseId,
                w: rec.wins,
                l: rec.losses,
                t: rec.ties,
                winPct: rec.percentage,
                pf: rec.pointsFor,
                pa: rec.pointsAgainst,
                playoffRecord: `${pW}-${pL}`,
                playoffW: pW,
                playoffs: t.rankCalculatedFinal <= 6 ? 1 : 0,
                finals: t.rankCalculatedFinal <= 2 ? 1 : 0,
                champs: champsCount
            });
        });
    }

    // Dynamic Sorting logic
    rowData.sort((a, b) => {
        let valA = a[currentSortColumn];
        let valB = b[currentSortColumn];

        let comparison = 0;
        if (valA > valB) comparison = 1;
        else if (valA < valB) comparison = -1;
        else {
            if (currentSortColumn === 'pf') {
                comparison = a.winPct > b.winPct ? 1 : (a.winPct < b.winPct ? -1 : 0);
            } else {
                comparison = a.pf > b.pf ? 1 : (a.pf < b.pf ? -1 : 0);
            }
        }

        return currentSortDirection === 'desc' ? -comparison : comparison;
    });

    // Render rows
    rowData.forEach((row, index) => {
        const team = allTeams.get(row.teamId);
        if (!team) return;

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>#${index + 1}</td>
            <td class="sticky-col">
                <div class="team-cell">
                    <img src="${team.logo || 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/default-team-logo-500.png'}" class="team-logo" alt="logo" onerror="this.src='https://a.espncdn.com/combiner/i?img=/i/teamlogos/default-team-logo-500.png'">
                    <span>${team.displayName}</span>
                </div>
            </td>
            <td>${row.w}</td>
            <td>${row.l}</td>
            <td>${row.t}</td>
            <td>${row.winPct.toFixed(3).replace(/^0+/, '')}</td>
            <td>${row.pf.toFixed(1)}</td>
            <td>${row.pa.toFixed(1)}</td>
            <td>${row.playoffRecord}</td>
            <td>${row.playoffs}</td>
            <td>${row.finals}</td>
            <td>${row.champs > 0 ? row.champs + ' 🏆' : '0'}</td>
        `;
        recordsTableBody.appendChild(tr);
    });
}

function renderH2H() {
    const t1 = team1Select.value;
    const t2 = team2Select.value;

    h2hResults.innerHTML = '';

    if (t1 === t2) {
        h2hResults.innerHTML = '<p class="placeholder-text">Please select two different teams.</p>';
        return;
    }

    const records = headToHeadRecords[t1]?.[t2];
    if (!records || (records.w === 0 && records.l === 0 && records.t === 0)) {
        h2hResults.innerHTML = '<p class="placeholder-text">These two teams have never played each other.</p>';
        return;
    }

    const team1Data = allTeams.get(t1);
    const team2Data = allTeams.get(t2);

    h2hResults.innerHTML = `
        <div class="matchup-stats">
            <div class="stat-box">
                <div class="stat-value ${records.w > records.l ? 'text-green' : (records.w < records.l ? 'text-red' : '')}">${records.w}</div>
                <div class="stat-label">${team1Data.displayName} Wins</div>
                <div class="stat-label" style="margin-top:0.5rem">PF: ${records.pf.toFixed(1)}</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" style="color:var(--warning)">${records.t}</div>
                <div class="stat-label">Ties</div>
            </div>
            <div class="stat-box">
                <div class="stat-value ${records.l > records.w ? 'text-green' : (records.l < records.w ? 'text-red' : '')}">${records.l}</div>
                <div class="stat-label">${team2Data.displayName} Wins</div>
                <div class="stat-label" style="margin-top:0.5rem">PF: ${records.pa.toFixed(1)}</div>
            </div>
        </div>
    `;
}

function renderChampions() {
    championsGrid.innerHTML = '';

    // Sort champions latest year first
    const sortedChamps = [...champions].sort((a, b) => b.year - a.year);

    sortedChamps.forEach(champ => {
        const team = allTeams.get(champ.teamId);
        const runnerUp = champ.runnerUpId ? allTeams.get(champ.runnerUpId) : null;

        if (!team) return;

        const card = document.createElement('div');
        card.className = 'champion-card';
        card.innerHTML = `
            <div class="champ-year">${champ.year} Champion</div>
            <div class="champ-team">
                <img src="${team.logo || 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/default-team-logo-500.png'}" class="champ-logo" onerror="this.src='https://a.espncdn.com/combiner/i?img=/i/teamlogos/default-team-logo-500.png'">
                <div class="champ-info">
                    <h3>${team.displayName}</h3>
                    <p>${champ.w} - ${champ.l} Record</p>
                </div>
            </div>
            ${runnerUp ? `
                <div class="champ-stats">
                    <div class="champ-stat">
                        <span>Runner Up</span>
                        <strong>${runnerUp.displayName}</strong>
                    </div>
                </div>
            ` : ''}
        `;
        championsGrid.appendChild(card);
    });
}

function setupSortListeners() {
    document.querySelectorAll('#records-table th.sortable').forEach(th => {
        th.style.cursor = 'pointer';
        th.title = 'Click to sort';
        th.addEventListener('click', () => {
            const column = th.dataset.sort;
            if (currentSortColumn === column) {
                currentSortDirection = currentSortDirection === 'desc' ? 'asc' : 'desc';
            } else {
                currentSortColumn = column;
                currentSortDirection = 'desc';
            }
            updateSortHeaders('#records-table', currentSortColumn, currentSortDirection);
            renderRecords(document.getElementById('year-select').value);
        });
    });
    updateSortHeaders('#records-table', currentSortColumn, currentSortDirection);

    document.querySelectorAll('#current-season-table th.sortable').forEach(th => {
        th.style.cursor = 'pointer';
        th.title = 'Click to sort';
        th.addEventListener('click', () => {
            const column = th.dataset.sort;
            if (csSortColumn === column) {
                csSortDirection = csSortDirection === 'desc' ? 'asc' : 'desc';
            } else {
                csSortColumn = column;
                csSortDirection = 'desc';
            }
            updateSortHeaders('#current-season-table', csSortColumn, csSortDirection);
            renderCurrentSeason();
        });
    });
    updateSortHeaders('#current-season-table', csSortColumn, csSortDirection);
}

function updateSortHeaders(tableSelector, activeCol, activeDir) {
    document.querySelectorAll(`${tableSelector} th.sortable`).forEach(th => {
        const isActive = th.dataset.sort === activeCol;
        let indicator = '';
        if (isActive) {
            indicator = activeDir === 'desc' ? ' ▼' : ' ▲';
        }
        th.textContent = th.textContent.replace(/ [▼▲]/g, '') + indicator;
    });
}

function renderAllTimeRecords() {
    // 1. Highest Weekly Scores
    const topScores = [...highestWeeklyScores].sort((a, b) => b.score - a.score).slice(0, 3);
    
    // 2. Highest Margins (skipping #1 due to a benched players game)
    const topMargins = [...highestMargins].sort((a, b) => b.margin - a.margin).slice(1, 4);
    
    // 3. Most Wins in a Season
    const topWins = [...regularSeasonWins].sort((a, b) => b.wins - a.wins).slice(0, 3);

    // 4. Highest Season Points
    const topSeasonPoints = [...highestSeasonPoints].sort((a, b) => b.points - a.points).slice(0, 3);

    const container = document.getElementById('all-time-records-content');
    if(!container) return;

    let html = `
        <div class="records-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 2rem;">
            
            <!-- Highest Scores -->
            <div class="card" style="padding: 1.5rem;">
                <h3 style="color:var(--warning); margin-bottom: 1rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem;">Highest Weekly Scores</h3>
                ${topScores.map((item, idx) => {
                    const team = allTeams.get(item.teamId);
                    return `
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;">
                        <div style="display: flex; align-items: center; gap: 0.75rem;">
                            <span style="font-weight: 800; color: var(--text-secondary); width: 20px;">#${idx+1}</span>
                            <img src="${team?.logo}" style="width: 32px; height: 32px; border-radius: 50%; background: #fff;" onerror="this.src='https://a.espncdn.com/combiner/i?img=/i/teamlogos/default-team-logo-500.png'">
                            <div>
                                <div style="font-weight: 600; color: #fff;">${item.score.toFixed(2)} pts</div>
                                <div style="font-size: 0.75rem; color: var(--text-secondary);">${team?.displayName} (${item.year})</div>
                            </div>
                        </div>
                    </div>`;
                }).join('')}
            </div>

            <!-- Highest Season Points (Regular Season) -->
            <div class="card" style="padding: 1.5rem;">
                <h3 style="color:var(--warning); margin-bottom: 1rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem;">Highest Season Points</h3>
                <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top:-0.5rem; margin-bottom: 1rem;">(Regular Season Only)</div>
                ${topSeasonPoints.map((item, idx) => {
                    const team = allTeams.get(item.teamId);
                    return `
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;">
                        <div style="display: flex; align-items: center; gap: 0.75rem;">
                            <span style="font-weight: 800; color: var(--text-secondary); width: 20px;">#${idx+1}</span>
                            <img src="${team?.logo}" style="width: 32px; height: 32px; border-radius: 50%; background: #fff;" onerror="this.src='https://a.espncdn.com/combiner/i?img=/i/teamlogos/default-team-logo-500.png'">
                            <div>
                                <div style="font-weight: 600; color: #fff;">${item.points.toFixed(2)} pts</div>
                                <div style="font-size: 0.75rem; color: var(--text-secondary);">${team?.displayName} (${item.year})</div>
                            </div>
                        </div>
                    </div>`;
                }).join('')}
            </div>

            <!-- Most Wins (Regular Season) -->
            <div class="card" style="padding: 1.5rem;">
                <h3 style="color:var(--warning); margin-bottom: 1rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem;">Most Wins in a Season</h3>
                <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top:-0.5rem; margin-bottom: 1rem;">(Regular Season Only)</div>
                ${topWins.map((item, idx) => {
                    const team = allTeams.get(item.teamId);
                    return `
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;">
                        <div style="display: flex; align-items: center; gap: 0.75rem;">
                            <span style="font-weight: 800; color: var(--text-secondary); width: 20px;">#${idx+1}</span>
                            <img src="${team?.logo}" style="width: 32px; height: 32px; border-radius: 50%; background: #fff;" onerror="this.src='https://a.espncdn.com/combiner/i?img=/i/teamlogos/default-team-logo-500.png'">
                            <div>
                                <div style="font-weight: 600; color: #fff;">${item.wins} Wins</div>
                                <div style="font-size: 0.75rem; color: var(--text-secondary);">${team?.displayName} (${item.year})</div>
                            </div>
                        </div>
                    </div>`;
                }).join('')}
            </div>

            <!-- Highest Margins of Victory -->
            <div class="card" style="padding: 1.5rem;">
                <h3 style="color:var(--warning); margin-bottom: 1rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem;">Highest Victory Margins</h3>
                ${topMargins.map((item, idx) => {
                    const winner = allTeams.get(item.winnerId);
                    const loser = allTeams.get(item.loserId);
                    return `
                    <div style="display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1.5rem;">
                        <div style="display: flex; align-items: center; justify-content: space-between;">
                            <div style="display: flex; align-items: center; gap: 0.75rem;">
                                <span style="font-weight: 800; color: var(--text-secondary); width: 20px;">#${idx+1}</span>
                                <div style="font-weight: 600; color: var(--accent);">${item.margin.toFixed(2)} pts</div>
                            </div>
                            <div style="font-size: 0.75rem; color: var(--text-secondary);">${item.year}</div>
                        </div>
                        <div style="display: flex; align-items: center; gap: 0.5rem; justify-content: flex-start; padding-left: 2.2rem;">
                            <div style="display: flex; align-items: center; gap: 0.5rem;">
                                <img src="${winner?.logo}" style="width: 20px; height: 20px; border-radius: 50%; background: #fff;" onerror="this.src='https://a.espncdn.com/combiner/i?img=/i/teamlogos/default-team-logo-500.png'">
                                <span style="color:#fff; font-size: 0.875rem;">${winner?.displayName} <span style="color:var(--text-secondary)">(${item.winnerScore.toFixed(2)})</span></span>
                            </div>
                        </div>
                        <div style="display: flex; align-items: center; gap: 0.5rem; justify-content: flex-start; padding-left: 2.2rem;">
                            <span style="color:var(--text-secondary); font-size: 0.75rem; width: 20px; text-align: center;">vs</span>
                            <div style="display: flex; align-items: center; gap: 0.5rem;">
                                <img src="${loser?.logo}" style="width: 20px; height: 20px; border-radius: 50%; background: #fff;" onerror="this.src='https://a.espncdn.com/combiner/i?img=/i/teamlogos/default-team-logo-500.png'">
                                <span style="color:var(--text-secondary); font-size: 0.875rem;">${loser?.displayName} <span style="opacity:0.7">(${item.loserScore.toFixed(2)})</span></span>
                            </div>
                        </div>
                    </div>`;
                }).join('')}
            </div>
            
        </div>
    `;
    
    container.innerHTML = html;
}

function calculatePowerPoints(teamsArray, valueExtractor) {
    const sorted = [...teamsArray].sort((a, b) => valueExtractor(b) - valueExtractor(a));
    const pointsMap = {};
    let n = teamsArray.length;
    
    for (let i = 0; i < sorted.length; i++) {
        if (i > 0 && valueExtractor(sorted[i]) === valueExtractor(sorted[i-1])) {
            continue;
        }
        
        let tieCount = 1;
        while (i + tieCount < sorted.length && valueExtractor(sorted[i + tieCount]) === valueExtractor(sorted[i])) {
            tieCount++;
        }
        
        let totalPointsForGroup = 0;
        for (let j = 0; j < tieCount; j++) {
            totalPointsForGroup += (n - (i + j));
        }
        const pointsPerTeam = totalPointsForGroup / tieCount;
        
        for (let j = 0; j < tieCount; j++) {
            pointsMap[sorted[i + j].id] = pointsPerTeam;
        }
    }
    
    return pointsMap;
}

// CURRENT SEASON RENDER
function renderCurrentSeason() {
    if (!currentSeasonBody) return;
    currentSeasonBody.innerHTML = '';
    
    const validYears = Object.keys(leagueData).sort().reverse();
    const currentYear = "2025"; // MOCK: Simulate 2025 season
    const data = leagueData[currentYear];
    if (!data || !data.teams) return;

    let teamStats = {};

    data.teams.forEach(t => {
        teamStats[t.id] = {
            id: t.id,
            teamId: t.franchiseId,
            w: 0, l: 0, t: 0, pf: 0, pa: 0,
            totalW: 0, totalL: 0, totalT: 0,
            optW: 0, optL: 0, optT: 0,
            streak: 0,
            rank: t.rankCalculatedFinal
        };
    });
    
    let weeklyScores = {};

    if (data.schedule) {
        data.schedule.forEach(matchup => {
            if (matchup.playoffTierType !== "NONE") return; 
            if (matchup.winner === "UNDECIDED") return; 
            
            // MOCK: Simulate end of week 14
            if (matchup.matchupPeriodId > 14) return;

            const home = matchup.home;
            const away = matchup.away;
            if (!home || !away) return;
            
            const homeId = home.teamId;
            const awayId = away.teamId;
            const week = matchup.matchupPeriodId;
            
            const homePoints = home.totalPoints;
            const awayPoints = away.totalPoints;
            
            if (homePoints > awayPoints) {
                teamStats[homeId].w++; teamStats[awayId].l++;
                teamStats[homeId].streak = teamStats[homeId].streak > 0 ? teamStats[homeId].streak + 1 : 1;
                teamStats[awayId].streak = teamStats[awayId].streak < 0 ? teamStats[awayId].streak - 1 : -1;
            } else if (awayPoints > homePoints) {
                teamStats[awayId].w++; teamStats[homeId].l++;
                teamStats[awayId].streak = teamStats[awayId].streak > 0 ? teamStats[awayId].streak + 1 : 1;
                teamStats[homeId].streak = teamStats[homeId].streak < 0 ? teamStats[homeId].streak - 1 : -1;
            } else {
                teamStats[homeId].t++; teamStats[awayId].t++;
                teamStats[homeId].streak = 0; teamStats[awayId].streak = 0;
            }
            
            teamStats[homeId].pf += homePoints;
            teamStats[homeId].pa += awayPoints;
            teamStats[awayId].pf += awayPoints;
            teamStats[awayId].pa += homePoints;
            
            if (!weeklyScores[week]) weeklyScores[week] = [];
            weeklyScores[week].push({ id: homeId, score: homePoints });
            weeklyScores[week].push({ id: awayId, score: awayPoints });
            
            let homeOpt = homePoints;
            let awayOpt = awayPoints;
            if (typeof currentSeasonOptimal !== 'undefined' && currentSeasonOptimal[week]) {
                if (currentSeasonOptimal[week][homeId] !== undefined) homeOpt = currentSeasonOptimal[week][homeId];
                if (currentSeasonOptimal[week][awayId] !== undefined) awayOpt = currentSeasonOptimal[week][awayId];
            }
            
            if (homeOpt > awayOpt) {
                teamStats[homeId].optW++; teamStats[awayId].optL++;
            } else if (awayOpt > homeOpt) {
                teamStats[awayId].optW++; teamStats[homeId].optL++;
            } else {
                teamStats[homeId].optT++; teamStats[awayId].optT++;
            }
        });
        
        Object.keys(weeklyScores).forEach(week => {
            const scores = weeklyScores[week];
            for (let i = 0; i < scores.length; i++) {
                for (let j = i + 1; j < scores.length; j++) {
                    if (scores[i].score > scores[j].score) {
                        teamStats[scores[i].id].totalW++;
                        teamStats[scores[j].id].totalL++;
                    } else if (scores[i].score < scores[j].score) {
                        teamStats[scores[i].id].totalL++;
                        teamStats[scores[j].id].totalW++;
                    } else {
                        teamStats[scores[i].id].totalT++;
                        teamStats[scores[j].id].totalT++;
                    }
                }
            }
        });
    }

    let sortedTeams = Object.values(teamStats).sort((a, b) => {
        let valA = a[csSortColumn];
        let valB = b[csSortColumn];
        
        let comparison = 0;
        if (valA > valB) comparison = 1;
        else if (valA < valB) comparison = -1;
        else {
            if (csSortColumn === 'pf' || csSortColumn === 'pa') {
                comparison = a.w > b.w ? 1 : (a.w < b.w ? -1 : 0);
            } else {
                comparison = a.pf > b.pf ? 1 : (a.pf < b.pf ? -1 : 0);
            }
        }
        
        return csSortDirection === 'desc' ? -comparison : comparison;
    });

    sortedTeams.forEach((stats, idx) => {
        const team = allTeams.get(stats.teamId);
        if (!team) return;

        const streakStr = stats.streak > 0 ? `W${stats.streak}` : (stats.streak < 0 ? `L${Math.abs(stats.streak)}` : '-');
        const streakColor = stats.streak > 0 ? '#28a745' : (stats.streak < 0 ? '#dc3545' : 'var(--text-secondary)');
        
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>#${idx + 1}</td>
            <td class="sticky-col">
                <div class="team-cell">
                    <img src="${team.logo || 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/default-team-logo-500.png'}" class="team-logo" alt="logo" onerror="this.src='https://a.espncdn.com/combiner/i?img=/i/teamlogos/default-team-logo-500.png'">
                    <span>${team.displayName}</span>
                </div>
            </td>
            <td>${stats.w}-${stats.l}-${stats.t}</td>
            <td>${stats.pf.toFixed(1)}</td>
            <td>${stats.pa.toFixed(1)}</td>
            <td>${stats.optW}-${stats.optL}-${stats.optT}</td>
            <td><strong style="color: ${streakColor};">${streakStr}</strong></td>
        `;
        currentSeasonBody.appendChild(tr);
    });

    // Render Power Rankings
    const prBody = document.getElementById('power-rankings-body');
    if (prBody) {
        prBody.innerHTML = '';
        const teamStatsArr = Object.values(teamStats);
        
        const recordPoints = calculatePowerPoints(teamStatsArr, t => t.w + (t.t * 0.5));
        const totalRecordPoints = calculatePowerPoints(teamStatsArr, t => t.totalW + (t.totalT * 0.5));
        const pointsForPoints = calculatePowerPoints(teamStatsArr, t => t.pf);
        
        const prData = teamStatsArr.map(t => {
            const rPts = recordPoints[t.id] || 0;
            const trPts = totalRecordPoints[t.id] || 0;
            const pfPts = pointsForPoints[t.id] || 0;
            const recStr = `${t.w}-${t.l}${t.t > 0 ? '-' + t.t : ''}`;
            const trStr = `${t.totalW}-${t.totalL}${t.totalT > 0 ? '-' + t.totalT : ''}`;
            const pfStr = t.pf.toFixed(1);
            
            return {
                teamId: t.teamId,
                rPts, trPts, pfPts,
                totalPts: rPts + trPts + pfPts,
                recStr, trStr, pfStr
            };
        });
        
        prData.sort((a, b) => b.totalPts - a.totalPts);
        
        prData.forEach((row, index) => {
            const team = allTeams.get(row.teamId);
            if (!team) return;
            
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>#${index + 1}</td>
                <td class="sticky-col">
                    <div class="team-cell">
                        <img src="${team.logo || 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/default-team-logo-500.png'}" class="team-logo" alt="logo" onerror="this.src='https://a.espncdn.com/combiner/i?img=/i/teamlogos/default-team-logo-500.png'">
                        <span>${team.displayName}</span>
                    </div>
                </td>
                <td>${row.recStr} <span style="color:var(--text-secondary); font-size: 0.85rem;">(${row.rPts})</span></td>
                <td>${row.trStr} <span style="color:var(--text-secondary); font-size: 0.85rem;">(${row.trPts})</span></td>
                <td>${row.pfStr} <span style="color:var(--text-secondary); font-size: 0.85rem;">(${row.pfPts})</span></td>
                <td><strong>${row.totalPts}</strong></td>
            `;
            prBody.appendChild(tr);
        });
    }
}

// BOOT
initApp();
