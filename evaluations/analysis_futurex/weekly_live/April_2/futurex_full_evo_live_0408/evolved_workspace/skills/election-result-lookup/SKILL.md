---
name: election-result-lookup
description: Look up election results and political outcomes for temporal prediction tasks
---

# Election Result Lookup Skill

## When to Use
- Task asks about election winners or vote shares
- Task asks about which candidates advanced to runoffs
- Task involves political appointments or policy decisions
- Resolution date is after the election date
- Task asks about head-to-head comparisons between candidates

## Strategy

### Step 1: Direct Result Search
- `"[country/region] [election type] [year] results winner"`
- `"[election name] [date] first round results"`
- For runoffs: `"[election] second round candidates who qualified"`

### Step 2: Wikipedia Cross-Check
- Wikipedia election articles are usually accurate and comprehensive
- Search: `"[election name] Wikipedia"`
- Look for vote percentages and candidate rankings

### Step 3: Multi-Select Questions
- For "who qualified for second round" questions, identify ALL qualifying candidates
- Typically top 2 candidates advance in two-round systems
- Check exact vote percentages to confirm ranking

### Step 4: Head-to-Head Comparisons
- For "X(YES) vs Y(NO)" questions, determine which candidate got MORE votes
- If X got more votes than Y, the outcome is YES (X wins the head-to-head)
- If Y got more votes than X, the outcome is NO (Y wins the head-to-head)
- Example: "Seguro(YES) vs Ventura(NO)" → Seguro 31.12% > Ventura 23.52% → YES

## Key Patterns Observed
- **Portugal 2026 Presidential First Round** (Jan 18, 2026):
  1. António José Seguro: 31.12% (1,755,764 votes)
  2. André Ventura: 23.52% (1,326,942 votes)
  3. João Cotrim de Figueiredo: 16.01% (903,201 votes)
  4. Henrique Gouveia e Melo: 12.32% (695,244 votes)
  5. Luís Marques Mendes: 11.30% (637,535 votes)
  - Seguro and Ventura advanced to runoff (first runoff in Portugal in 40 years)
  - Seguro won second round with ~66%
- **Two-round systems**: Top 2 candidates advance unless one gets >50% in round 1
- **Thailand legislative election (Feb 8, 2026)**: Bhumjaithai Party (BJT) won most seats (~193-194/500); PM Anutin Charnvirakul; "stunning victory the polls never saw coming"
- **Japan lower house election (Feb 2026)**: Team Mirai (チームみらい) won 11 seats (falls in '7+' category); party's goal was 'five or more seats'
- **NJ-11 Democratic primary special election (Feb 5, 2026)**: Analilia Mejia won (stunning upset); progressive organizer allied with Bernie Sanders; defeated Brendan Gill, Tom Malinowski, Tahesha Way
- **Indiana redistricting**: House passed HB 1032 (Dec 5, 2025) but Senate voted it DOWN (Dec 11, 2025, 31-19); Indiana's 2021 map remains for 2026 elections
- **Texas Democratic Senate primary (Mar 3, 2026)**: James Talarico won 53.03% vs Jasmine Crockett 45.66% (margin 7.37%); Talarico is Democratic nominee for 2026 US Senate election in Texas
- **Baden-Württemberg Landtag election (Mar 8, 2026)**: Greens (Bündnis 90/Die Grünen) won 30.2%, 56 seats (tied with CDU for 1st place); first place finish for Greens
- **Colombia 2026 elections (Mar 2026)**: Pacto Histórico (PH) won most seats in BOTH Chamber of Representatives AND Senate; led by President Gustavo Petro's coalition
- **Nepal House of Representatives Election (Mar 5, 2026)**: Rastriya Swatantra Party (RSP), led by Balendra "Balen" Shah, won 182/275 seats (landslide). Largest majority in Nepal in 60+ years.

## Reliable Sources
- Wikipedia: Comprehensive election articles with results
- Reuters, AP: Breaking election news
- Official electoral commission websites
- BBC, DW for European elections
- RTP (Portugal), Expresso (Portugal) for Portuguese elections

## Resolution Date Considerations
- Use results as of the resolution date
- If runoff hasn't happened yet at resolution date, answer is about first round
- If question asks "who qualified for second round" and resolution is on election day, answer based on first round results

## UK Cabinet Changes (2025-2026)
- **David Lammy**: Left Foreign Secretary role Sep 9, 2025; moved to Deputy PM + Lord Chancellor/Secretary of State for Justice
- **Rachel Reeves**: Remained as Chancellor of the Exchequer through at least Jan 2026
- For "Reeves or Lammy out first" question: Lammy left Foreign Secretary first (Sep 2025)
- Search: `"[UK minister] resign sacked fired [year]"` for cabinet changes

## Additional Key Patterns (March 2026)
- **Castilla y León election (March 15, 2026)**: PP (Partido Popular) won with 33 seats (gained 2 from 2022's 31). Falls in 32-35 seats range. PP needed Vox (13 seats) to form majority. Mañueco won as PP leader.
- **IL-08 Democratic Primary (March 17, 2026)**: Melissa Bean won (former U.S. Rep., moderate Democrat). Defeated Junaid Ahmed and others. Democratic nominee for U.S. House Illinois District 8.

## Additional Key Patterns (March 2026 additional)
- **Sucre (Bolivia) Mayoral Election 2026**: Fátima Tardío (Alianza Gente Nueva/AGN) won with 33,894 votes (20.22% of total votes counted). She is the new mayor of Sucre.
