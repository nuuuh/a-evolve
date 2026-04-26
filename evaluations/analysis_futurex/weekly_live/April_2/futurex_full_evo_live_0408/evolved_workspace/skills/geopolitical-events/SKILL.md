---
name: geopolitical-events
description: Look up geopolitical events, political developments, and international affairs for temporal prediction tasks
---

# Geopolitical Events Lookup Skill

## When to Use
- Task asks about political leaders being captured, assassinated, or removed from power
- Task asks about military actions, missile launches, or conflicts
- Task asks about international sanctions, treaties, or diplomatic events
- Task asks about doomsday clock, nuclear threats, or global security
- Task asks about political cabinet changes or resignations
- Task asks about IOC/sports governance policy changes
- Resolution date is tied to a specific geopolitical event

## Strategy

### Step 1: Direct Event Search
- `"[person/country] [event type] [month year] result"`
- `"[country] [action] [year] Wikipedia"`
- For assassinations: `"assassination of [person] [year]"`
- For captures: `"[person] arrested captured [year]"`
- For missile launches: `"[country] missile launch [month year]"`
- For policy changes: `"[organization] [policy] announced [year]"`

### Step 2: Wikipedia Cross-Check
- Wikipedia has comprehensive articles on major geopolitical events
- Search: `"[event name] Wikipedia [year]"`
- Look for exact dates and outcomes

### Step 3: Resolution Date Awareness
- For "by date X" questions: check if event happened BEFORE or AFTER the deadline
- For "still in custody" questions: check if person was released before resolution date
- For "still in office" questions: check if person resigned/was removed before resolution date
- For "before [event]" questions: check if policy/event happened before the reference event

## Key Data Points Observed (2025-2026)

### Venezuela / Nicolas Maduro
- **Jan 3, 2026**: Maduro captured by US forces in Caracas, Venezuela
- **Jan 5, 2026**: Appeared in federal court in Manhattan, pleaded not guilty to narco-terrorism and drug trafficking charges
- **Held at**: Metropolitan Detention Center (MDC) in Brooklyn, NY
- **Next court hearing**: March 17, 2026
- **NOT released** by January 31, 2026
- Wikipedia: "2026 United States intervention in Venezuela"

### Iran / Ali Khamenei
- **Feb 28, 2026**: Khamenei assassinated in Tehran by Israeli airstrikes
- **March 1, 2026**: Death confirmed by Iranian government
- This is AFTER January 31, 2026 deadline
- For "pull a Nasrallah on Khamenei by end of January 2025" → NO (happened Feb 28, 2026)

### North Korea Missile Launches (January 2026)
- **Jan 4, 2026**: First ballistic missile drill of 2026 (toward Sea of Japan)
- **Jan 27, 2026**: Multiple KN-25 short-range ballistic missiles toward East Sea
- North Korea DID launch missiles by Jan 31, 2026: YES

### Doomsday Clock (2026)
- **Jan 27, 2026**: Moved from 89 seconds to 85 seconds to midnight
- Movement: 4 seconds forward (closer to midnight)
- This is LESS than 10 seconds
- For "move by 10 seconds or more" → NO

### UK Cabinet Changes (2025)
- **Sep 9, 2025**: David Lammy left Foreign Secretary role; moved to Deputy PM + Lord Chancellor
- Rachel Reeves remained as Chancellor of the Exchequer through at least Jan 2026
- For "Reeves or Lammy out first": Lammy left Foreign Secretary first (Sep 2025)

### IOC Transgender Policy (2026)
- **Feb 7, 2026**: Sports leaders reached consensus on new gender policy during Winter Olympics
- **March 26, 2026**: IOC officially announced ban on transgender women from Olympics
- The intention was to announce during Winter Games (Feb 6-22) but delayed by legal wrangling
- For "banned before Winter Games" (resolution ~Feb 5, 2026) → NO (ban came March 26)
- The ban applies starting with 2028 LA Olympics

### Gustavo Petro (Colombia) US Visit (Feb 2026)
- **Feb 2, 2026**: Petro arrived in US
- **Feb 3, 2026**: Met with Trump at White House
- **Feb 5, 2026**: Official visit ended (4-day visit total)
- Granted special 5-day visa; did NOT stay more than 5 consecutive days
- For "stay longer than 5 consecutive days starting Feb 3" → NO


### Dubai Airport (March 2026)
- **~Feb 28 - Mar 1, 2026**: Dubai airport shut down due to US-Israel-Iran conflict
- **Mar 2, 2026**: Only limited operations resumed (25-37% of normal capacity)
- **Mar 3-6, 2026**: Still limited operations
- **Mar 7, 2026**: Airport again suspended (Iranian drone strikes)
- **~Mar 17-18, 2026**: Normal operations resumed (UAE airspace returned to normal)
- For "when did normal operations resume" → March 7 or later (option D)

### Democracy Report 2026
- **Brazil**: Ranked 28th out of 179 countries (15.6%) = top 10-20% (YES)
- **Ecuador**: Did NOT improve its score in 2026 Democracy Report (NO)
- Search: `"V-Dem Democracy Report 2026 [country] ranking"`

### Nornickel Palladium (2026)
- Guided at 2.415-2.465 million ounces
- Did NOT fall below 2.4 million ounces threshold
- For "will fall below 2.4M oz" → NO

### Global Platinum Availability (March 2026)
- Did NOT fall below 2 million ounces by March 4, 2026
- South African mine supply issues created deficits (~1.082M oz in 2025) but total availability remained above 2M oz
- For "will fall below 2M oz by March 4, 2026" → NO

### Sidney Crosby NHL (March 2026)
- No NHL team other than Pittsburgh Penguins publicly announced Crosby would join their roster before March 7, 2026
- Crosby returned to play for the Penguins in March 2026
- For "will another NHL team announce Crosby before Mar 7, 2026" → NO

### US-Israel-Iran Conflict (March 2026)
- **Feb 28, 2026**: US and Israel launched strikes on Iran (Operation Epic Fury / Operation Roaring Lion)
- **March 11-15, 2026**: Conflict actively ongoing; NO ceasefire announced
- **March 14, 2026**: Trump said Iran was ready to negotiate but he wasn't ready to stop
- **March 15, 2026**: Iran's Foreign Minister Abbas Araghchi stated: "Tehran has never asked for a ceasefire"
- **March 25, 2026**: Iran dismissed a US 15-point ceasefire plan
- **Actual ceasefire**: April 2026 timeframe (after March 15 deadline)
- For "ceasefire announced March 11-15, 2026" → NO

### Tel Aviv Airport (TLV) Foreign Airlines (March 2026)
- **Feb 28 - Mar 1, 2026**: US-Israel strikes on Iran triggered mass flight cancellations
- **March 4, 2026**: Israeli airlines (El Al, Israir, Arkia) began limited resumption
- **March 10, 2026**: Foreign airlines still drawing up plans; had NOT resumed
- **March 11, 2026**: Explosion in northern Tel Aviv
- **March 18, 2026**: Missile strike at Ben Gurion Airport (reduced capacity to 130)
- **Multiple foreign airlines** (EasyJet until March 29, ITA Airways until April 2, United until mid-June) extended suspensions
- For "foreign airlines resume by March 15, 2026" → NO

### Mexico City Travel Advisory (March 2026)
- Mexico City consistently at **Level 2 - "Exercise Increased Caution"**
- High-risk Level 4 states: Sinaloa, Tamaulipas, Guerrero, Colima, Michoacán, Zacatecas (NOT Mexico City)
- For "CDMX above Level 2 by mid-March 2026" → NO

### 2025-26 Iranian Protests Death Toll
- Protests began December 28, 2025; major crackdown January 8-9, 2026
- **HRANA (credible US-based rights group)**: ~6,872 confirmed deaths by early February 2026
- **UN Special Rapporteur (Jan 22, 2026)**: May surpass 20,000
- **Iran International (Jan 25, 2026)**: 36,500+ killed in just January 8-9 crackdown
- **Trump (Feb 20, 2026)**: Cited estimate of 32,000+
- By March 20, 2026: Death toll exceeded 10,000 (conservative estimates)

## Reliable Sources
- Wikipedia: Comprehensive articles on major geopolitical events
- Reuters, AP: Breaking news on political events
- BBC, Guardian: UK political news
- US Department of State: Official US government actions
- Bulletin of Atomic Scientists: Doomsday Clock announcements
- CSIS, RAND: Geopolitical analysis

## Common Patterns
- "Will X be assassinated/captured by date Y?" → Search for the event, check if it happened before Y
- "Will X be released from custody by date Y?" → Search for release date, compare to Y
- "Will X resign/be fired by date Y?" → Search for resignation/firing date, compare to Y
- "Will country X launch missiles by date Y?" → Search for launch dates, check if any before Y
- "Will doomsday clock move by X seconds?" → Find the actual movement amount, compare to X
- "Will [policy] happen before [event]?" → Find policy announcement date, compare to event date

### Warner Bros. Discovery (WBD) M&A Timeline (2025-2026)
- **Dec 4, 2025**: WBD entered into merger agreement with Netflix
- **Feb 17, 2026**: WBD set Special Meeting date of March 20, 2026 to vote on Netflix merger
- **Feb 26, 2026**: WBD's board determined Paramount's revised $110.9 billion offer ($31/share) was a **superior proposal** to Netflix's offer
- **Feb 27, 2026**: Netflix **declined to match** the offer and **withdrew**; Paramount-WBD formal merger agreement announced
- **March 20, 2026**: This date became the **record date** for the Paramount deal shareholder vote (NOT the meeting date); Netflix deal was terminated before this date
- **March 26, 2026**: WBD set **April 23, 2026** as the new special meeting date to vote on the Paramount merger
- For "March 20 special meeting" question: Netflix deal was cancelled; meeting was effectively cancelled → "Not acquired" at March 20 meeting

### 2025-26 Iranian Protests Death Toll (Updated)
- By March 20, 2026: Confirmed/verified deaths ~5,000-7,000 (below 10,000); broader estimates 20,000-43,000+
- factually.co (March 17, 2026): "roughly 5,000-6,000 verified deaths up to claims of 20,000-36,500 or more"
- Resolution likely uses verified/confirmed figure → option A (Below 10,000) for "before March 20" question
