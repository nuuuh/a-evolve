---
name: sports-result-lookup
description: Efficiently look up sports game results for temporal prediction tasks involving match outcomes
---

# Sports Result Lookup Skill

## When to Use
- Task asks about a specific sports match outcome (win/draw/loss)
- Task asks about tournament/championship winners
- Task involves NHL, NFL, soccer/football, basketball, baseball, MMA/UFC, esports, tennis, etc.
- Resolution date is close to the match date
- Task involves prop bets for a sports event (e.g., UCL matchday)

## Strategy

### Step 1: Direct Result Search (Most Efficient)
Search immediately for the actual result using specific queries:
- `"[Team A] vs [Team B] [date] result"` or `"[Team A] [Team B] final score [date]"`
- `"[Team A] [Team B] [month] [year] score"`
- For championships: `"[tournament name] [year] winner champion"`
- For MMA/UFC: `"UFC [event number] [fighter A] vs [fighter B] result winner"`
- For esports: `"[game] [tournament] [year] winner champion"`
- For tennis: `"[tournament] [year] [men's/women's] singles final winner"`

### Step 2: Verify with Second Source
If result found, quickly verify with one more search or source mention.

### Step 3: Map to Options
Match the result to the provided answer options.

## Reliable Sources
- **ESPN**: Game summaries with final scores
- **Wikipedia**: Tournament/season articles with results
- **BBC Sport**: UK football results
- **NHL.com, NBA.com, NFL.com**: Official league sites
- **Sofascore, Flashscore**: Multi-sport results
- **Football Wiki (Fandom)**: Detailed matchday summaries with all results
- **MMA Fighting, MMA Junkie**: UFC/MMA results
- **Liquipedia**: Esports tournament results
- **ATP/WTA official sites**: Tennis results

## Key Results Observed (Jan-Mar 2026)
### NFL
- **NFC Championship (Jan 25, 2026)**: Seattle Seahawks 31-27 Los Angeles Rams
- **Super Bowl LX (Feb 8, 2026)**: Seattle Seahawks 29-13 New England Patriots (at Levi's Stadium, Santa Clara)
- **Super Bowl LX MVP**: Kenneth Walker III (RB, Seahawks; 161 total yards; first RB MVP in 28 years)
- **Super Bowl LX Stats**: 6 sacks (Seahawks sacked Drake Maye 6 times); 4 total TDs; Myers (Seahawks) 5/5 FGs; 1 missed PAT (Patriots); multiple fumbles
- **NFL Honors (Feb 5, 2026)**: MVP = Matthew Stafford (LA Rams); Coach of Year = Mike Vrabel (NE Patriots)

### Soccer
- **AFCON 2025 Final (Jan 18, 2026)**: Senegal 1-0 Morocco (extra time) - later overturned by CAF in March 2026
- **CFP National Championship (Jan 19, 2026)**: Indiana 27-21 Miami
- **Juventus vs Napoli (Jan 25, 2026, Serie A)**: Juventus 3-0 Napoli (Jonathan David scored)
- **Top 14 Round 16 (Jan 31, 2026)**: Racing 92 37-31 Perpignan (at Paris La Défense Arena)
- **EFL Cup semi-final 2nd leg (Feb 4, 2026)**: Manchester City 3-1 Newcastle United (5-1 agg; goals: Reijnders, Marmoush x2); Man City to face Arsenal in final
- **EFL Championship (Feb 7, 2026)**: West Brom 0-0 Stoke City; Preston North End 1-0 Portsmouth
- **Liga MX Clausura 2026 J5 (Feb 7, 2026)**: Querétaro FC 2-0 Club León FC

### Rugby
- **URC Round 11 (Jan 30-31, 2026)**: Glasgow Warriors 31-22 Munster; Ospreys 19-13 Dragons; Leinster 28-20 Edinburgh; Ulster 21-14 Cardiff
- **Rugby Europe Championship 2026 (Mar 15, 2026)**: Portugal won, defeating defending champions Georgia in the final (held in Madrid at Estadio Ontime Butarque, Leganés). Romania vs Spain played in bronze final. Historic win for Portugal.
- **Women's SVNS Series 2025-26**: New Zealand (Black Ferns Sevens) won overall series title (118 pts vs Australia's 110 pts). New Zealand also won final tournament in New York (defeated Australia 22-21). HSBC SVNS New York 2026 took place ~March 15-16, 2026.

### MMA/UFC
- **UFC 324 (Jan 24, 2026)**: Justin Gaethje def. Paddy Pimblett (unanimous decision) - UFC interim lightweight title
- **UFC 326 (Mar 7, 2026)**: 
  - Rodolfo Bellato def. Luke Fernandez by TKO at 2:42 Round 1 (light heavyweight); Bellato dropped Fernandez with left hook, finished with ground strikes; Bellato improved to 13-3-1 MMA (2-1-1 UFC)
  - Alberto Montes def. Ricky Turcios via submission (anaconda choke) at 0:40 of Round 2 (featherweight); Montes improved to 11-1 MMA

### Esports
- **MLBB M7 World Championship (Jan 25, 2026)**: Aurora Gaming PH def. Alter Ego 4-0

### Tennis
- **Australian Open 2026 Women's Singles (Feb 1, 2026)**: Elena Rybakina def. Aryna Sabalenka 6-4, 4-6, 6-4 (came back from 0-3 in final set)
- **Indian Wells WTA 1000 2026 (BNP Paribas Open, ~Mar 16, 2026)**: Aryna Sabalenka def. Elena Rybakina 3-6, 6-3, 7-6(8-6) in final; saved championship point in deciding tiebreak; Sabalenka's first Indian Wells title; 10th WTA 1000 title
- **Indian Wells ATP 1000 2026 (BNP Paribas Open, ~Mar 15-17, 2026)**: Jannik Sinner def. Daniil Medvedev 7-6(8-6), 7-6(7-4) in final; came back from 0-4 in second set tiebreak; Sinner's 6th Masters 1000 title; 25th career title

### Chess
- **Tata Steel Chess Masters 2026 (Feb 1, 2026)**: Nodirbek Abdusattorov won
- **2026 Prague Masters (resolved ~Mar 8, 2026)**: Nodirbek Abdusattorov won (6/9 pts; hat-trick: London Chess Classic 2025, Tata Steel 2026, Prague Masters 2026)

### NHL
- **Kings vs Hurricanes (Feb 1, 2026)**: Hurricanes 3-2 Kings
- **NY Rangers 2026 NHL trade deadline (Mar 7, 2026)**: TRADED - Carson Soucy→Islanders (Jan 27), Brennan Othmann→Calgary Flames (Mar 6). NOT traded: Trocheck, Zibanejad, Lafrenière

### Formula 1
- **2026 Australian Grand Prix (Mar 5-8, 2026)**: George Russell (Mercedes) won by 2.9s over Kimi Antonelli (Mercedes 1-2)

### Cricket
- **T20 World Cup 2026**: 780 sixes, 1,434 fours; ratio = 0.5439 (option C: 0.50-0.54)

### Basketball
- **Big East Men's Basketball 2025-26 Regular Season Champion**: St. John's (NY) - second consecutive year

### Other
- **Saudi Pro League Al Fateh vs Al Hazem (Feb 1, 2026)**: 1-1 draw
- **Argentine Primera Division CA Tucuman vs CA Huracan (Jan 31, 2026)**: 1-1 draw

### College Basketball (March 2026)
- **SEC Men's Basketball Tournament 2026 (Mar 11-15, 2026)**: Arkansas Razorbacks won (defeated Vanderbilt in championship game)
- **Big 12 Conference Championship 2026 (Mar 14, 2026)**: Arizona won (defeated Houston 79-74; Arizona's first Big 12 Tournament title; Brayden Burries and Koa Peat each scored 21 pts)
- **ACC Men's Basketball Tournament 2026 (Mar 14, 2026)**: Duke won (defeated Virginia 74-70 at Spectrum Center, Charlotte; 2nd consecutive ACC Tournament title; Cameron Boozer named ACC Player of Year and Rookie of Year; Coach Jon Scheyer named ACC Coach of Year)

### Chess (March 2026)
- **2026 American Cup Open division (Mar 2-13, 2026, Saint Louis Chess Club)**: Wesley So won (defeated Levon Aronian 1.5-0.5 in Grand Final; also defeated Fabiano Caruana in Championship Bracket finals)

### Copa Libertadores 2026 (March 2026)
- **Deportes Tolima vs O'Higgins (Mar 11, 2026)**: Tolima 2-0 O'Higgins (Tolima qualified for group stage)
- **Independiente Medellín vs Juventud (Mar 13, 2026)**: Medellín 2-1 Juventud (3-2 on aggregate)

### Bundesliga (March 2026)
- **Borussia Mönchengladbach vs St. Pauli (Mar 13, 2026)**: Gladbach 2-0 St. Pauli

## Resolution Date Awareness
- Match results are typically final at the resolution date
- Exception: Disciplinary decisions, VAR reviews, appeals (rare)
- For overturned results: Use the state AT the resolution date
- Example: AFCON final - Senegal won on Jan 18, but CAF overturned in March. Resolution date Jan 18 = Senegal

## Example Queries
- Soccer: `"Coventry City Leicester City January 17 2026 result"`
- NHL: `"Golden Knights Kings January 14 2026 final score"`
- NFL/CFP: `"College Football Playoff National Championship 2026 winner"`
- International: `"AFCON 2025 final result winner"`
- MMA: `"UFC 324 Gaethje Pimblett result winner"`
- Esports: `"MLBB M7 World Championship 2026 winner"`
- Tennis: `"Australian Open 2026 women's singles final winner"`

## UCL/Multi-Match Prop Bets Strategy
When asked about prop bets across multiple matches (e.g., "UCL Matchday 7 prop bets"):
1. Search for the matchday summary: `"[competition] matchday [N] [date] results all matches"`
2. Use Football Wiki Fandom for comprehensive matchday data: `"site:football.fandom.com [competition] match day [N] [year]"`
3. For each prop, check specific matches:
   - Penalties: Look for "penalty" in match reports
   - Red cards: Look for "red card" in match reports
   - First 5 min goals: Check match timelines
   - Specific player goals (Haaland, Mbappe): Search directly
4. With 16-18 matches, statistically likely props: goal in first 5 min (YES ~90%), 5+ draws (NO ~70%)
5. For "comeback from 2 down" - check high-scoring matches for score progressions
6. For "PL teams win" - identify all PL teams in competition and check each result

### Cycling (March 2026)
- **2026 Milano-Sanremo (Mar 22, 2026)**: Tadej Pogačar won, beating Thomas Pidcock in two-up sprint on Via Roma. Podium: 1. Pogačar, 2. Pidcock, 3. Wout van Aert. MVDP was dropped early on Poggio slopes. Ganna was not in the lead group at the Poggio. Of Pogačar/Ganna/MVDP, only 1 (Pogačar) was in first 3 at top of Poggio.

### Rugby (March 2026 additional)
- **2026 Six Nations Rugby Championship**: France won (retained title with last kick of tournament on March 15, 2026). Ireland finished 2nd (Thomas Ramos broke Ireland hearts). Scotland 3rd. Ireland won the Triple Crown (defeated Scotland 43-21 on March 14, 2026 at Aviva Stadium; Ireland's 4th Triple Crown in 5 years).

### Soccer (March 2026 additional)
- **2026 AFC Women's Asian Cup Champion**: Japan defeated Australia 1-0 in final (March 21, 2026). Japan's captain Yui Hasegawa lifted trophy. Japan's 3rd title in 4 editions.
- **UCL Round of 16 2025-26 (Mar 10-18, 2026)**: First legs: Galatasaray 1-0 Liverpool (Mar 10), Atletico 5-2 Tottenham (Mar 10), Real Madrid 3-0 Man City (Mar 11), PSG 5-2 Chelsea (Mar 11), Newcastle 1-1 Barcelona (Mar 11), Atalanta 1-6 Bayern (Mar 11). Second legs: Man City 1-2 Real Madrid (5-1 agg), Chelsea 0-3 PSG (8-2 agg), Tottenham 3-2 Atletico (7-4 agg), Barcelona 7-2 Newcastle (8-3 agg). Bodo/Glimt hosted Sporting CP Leg 2 on Mar 17.

### Baseball (March 2026)
- **2026 World Baseball Classic (WBC)**: Venezuela won, defeating USA 3-2 in championship game (March 17-18, 2026) at loanDepot Park, Miami. Venezuela's first-ever WBC title. Eugenio Suárez's RBI double in 9th inning was decisive.

### Basketball (March 2026 additional)
- **2026 March Madness Sweet 16**: Florida (1 seed) upset by Iowa (9 seed) - only 3 of 4 #1 seeds advanced. Big Ten had 6 teams in Sweet 16 (conference record). All 16 teams from ACC, Big Ten, Big 12, SEC (only 4 conferences). Kansas flopped as 2 seed. WCC had ZERO teams in Sweet 16.

### Esports (March 2026 additional)
- **2026 First Stand Tournament (League of Legends)**: BLG (Bilibili Gaming) from LPL (China) defeated G2 Esports 3-1 in Grand Finals (São Paulo, Brazil, March 16-22, 2026). Champion came from LPL region.
- For LoL regional questions: LPL (China) and LCK (Korea) are historically dominant; LEC/LCS/other regions rarely win international tournaments

### Sumo (March 2026)
- **Haru Basho 2026 (March 2026)**: Aonishiki Arata's yokozuna bid FAILED (7-8 record/make-koshi). Was promoted to ozeki in January 2026 after winning November 2025 Kyushu Basho. Yokozuna promotion requires dominant performance (typically winning the tournament).

### Poker (March 2026)
- **2026 Triton Jeju $100K NLHE Main Event**: 178 entries (well below 250 threshold). Won by Ben Tollerene for $3,766,000. 2025 had 285 entries (record), 2024 had 216 entries.
