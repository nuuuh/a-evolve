---
name: entertainment-data-lookup
description: Look up box office data, award nominations, and entertainment industry results for temporal prediction tasks
---

# Entertainment Data Lookup Skill

## When to Use
- Task asks about box office gross (opening weekend, total gross)
- Task asks about Oscar/Academy Award nominations or winners
- Task asks about Grammy Award nominations or winners
- Task asks about book charts (Amazon, NYT bestsellers)
- Task asks about entertainment industry events

## Box Office Strategy

### Step 1: Identify the Film and Release Date
- Note the film title and release date
- Check if it's a holiday weekend (MLK, Memorial Day, Labor Day, Thanksgiving, Christmas)

### Step 2: Search for Box Office Data
- `"[film title] box office opening weekend [year]"`
- `"[film title] domestic opening weekend Box Office Mojo"`
- For holiday weekends: `"[film title] [holiday] weekend opening"`

### Step 3: Holiday Weekend Reporting
**CRITICAL**: Box Office Mojo uses different reporting for holiday weekends:
- **MLK Weekend (3-day Mon)**: BOM reports **4-day** figure as "opening weekend"
- **Memorial Day Weekend**: BOM reports **4-day** figure
- **Labor Day Weekend**: BOM reports **4-day** figure
- **Thanksgiving**: BOM reports **5-day** figure
- **Christmas**: BOM reports **12-day** figure
- **Regular weekends**: BOM reports **3-day** figure

Example: "28 Years Later: The Bone Temple" (MLK 2026)
- 3-day (Fri-Sun): $13 million
- 4-day (Fri-Mon): $15 million
- **Box Office Mojo reports $15M as the "opening weekend"** for MLK weekend

### Step 4: Verify with Multiple Sources
- Box Office Mojo: boxofficemojo.com
- The Numbers: the-numbers.com
- Deadline Hollywood: deadline.com/tag/box-office/

## Oscar Nominations Strategy

### Step 1: Search for Nominations
- `"[year] Oscar nominations [category] complete list"`
- `"98th Academy Awards [category] nominees"`
- Wikipedia: `"[year] Academy Awards Wikipedia"`

### Step 2: Verify All Nominees
- There are always exactly 5 nominees per category (except Best Picture: 10)
- Cross-check with multiple sources
- The official Oscars website (oscars.org) is authoritative

### Key Data Points Observed - 98th Academy Awards (2026 Oscars)
Nominations announced January 22, 2026. Ceremony March 15, 2026. Hosted by Conan O'Brien (2nd year in a row).

**Best Picture (10 nominees)**:
Bugonia, F1, Frankenstein, Hamnet, Marty Supreme, **One Battle After Another** (WINNER), The Secret Agent, Sentimental Value, Sinners, Train Dreams
- NOT nominated: It Was Just an Accident, Weapons, Wicked: For Good, No Other Choice

**Best Director**:
**Paul Thomas Anderson** (One Battle After Another, WINNER), Ryan Coogler (Sinners), Chloé Zhao (Hamnet), Joachim Trier (Sentimental Value), Josh Safdie (Marty Supreme)

**Best Actor**:
Leonardo DiCaprio (One Battle After Another), Timothée Chalamet (Marty Supreme), Ethan Hawke (Blue Moon), **Michael B. Jordan** (Sinners, WINNER), Wagner Moura (The Secret Agent)
- NOTE: Michael B. Jordan won Best Actor for Sinners (NOT Ethan Hawke)

**Best Actress**:
**Jessie Buckley** (Hamnet, WINNER - first Irish woman to win Best Actress), Rose Byrne (If I Had Legs I'd Kick You), Renate Reinsve (Sentimental Value), Emma Stone (Bugonia), Kate Hudson (Song Sung Blue)

**Best Supporting Actor**:
**Sean Penn** (One Battle After Another, WINNER - was a no-show at ceremony)

**Best Supporting Actress**:
Teyana Taylor (One Battle After Another), **Amy Madigan** (Weapons, WINNER), Inga Ibsdotter Lilleaas (Sentimental Value), Wunmi Mosaku (Sinners), Elle Fanning (Sentimental Value)

**Best Animated Feature**:
**KPop Demon Hunters** (WINNER - also won Best Original Song for "Golden", first K-pop tune to win; 99% audience score on RT)

**Best International Feature Film**:
**Sentimental Value** (Norway, WINNER)

**Best Documentary Short Film**:
**All the Empty Rooms** (WINNER - Joshua Seftel and Conall Jones)

**Best Live Action Short Film**:
**TIE: The Singers AND Two People Exchanging Saliva** (rare joint win)
Other nominees: Butcher's Stain, A Friend of Dorothy, Jane Austen's Period Drama

**Best Documentary**:
The Alabama Solution, Come See Me in the Good Light, Cutting Through Rocks, **Mr. Nobody Against Putin** (WINNER), The Perfect Neighbor

**Achievement in Casting**:
**Cassandra Kulukundis** (One Battle After Another, WINNER), Francine Maisler (Sinners), Nina Gold (Hamnet), Jennifer Venditti (Marty Supreme), Gabriel Domingues (The Secret Agent)

**Frankenstein wins (3 total)**:
- Best Costume Design
- Best Makeup and Hairstyling
- Best Production Design

**Win Counts Summary**:
- One Battle After Another: **6 wins** (Best Picture, Best Director, Best Supporting Actor [Sean Penn], Best Adapted Screenplay, Best Film Editing, Best Casting)
- Sinners: **4 wins** (Best Actor [Michael B. Jordan], Best Original Score [Ludwig Göransson], Best Original Screenplay, + 1 more)
- Frankenstein: **3 wins** (Costume Design, Makeup and Hairstyling, Production Design)
- KPop Demon Hunters: **2 wins** (Best Animated Feature, Best Original Song "Golden")
- Hamnet: **1 win** (Best Actress)
- Weapons: **1 win** (Best Supporting Actress)
- Sentimental Value: **1 win** (Best International Feature)
- Marty Supreme: **0 wins** (nominated for 9, won none)

**Key stats**: Sinners led with record 16 nominations. One Battle After Another won 6 awards. Wicked: For Good was completely snubbed. Warner Bros. tied record for most Oscar wins by a studio (11 wins total from One Battle After Another + Sinners).

## Grammy Awards Strategy

### Step 1: Search for Grammy Results
- `"[year] Grammy Awards [category] winner"`
- `"[N]th Annual Grammy Awards [category]"`
- Wikipedia: `"[N]th Grammy Awards Wikipedia"`

### Key Data Points Observed - 68th Grammy Awards (Feb 1, 2026)
Ceremony held in Los Angeles, February 1, 2026.

**Songwriter of the Year, Non-Classical**: **Amy Allen** (WINNER)
- Other nominees: Edgar Barrera, Jessie Jo Dillon, Tobias Jesso Jr., Laura Veltz

**Best Pop Vocal Album**: **Lady Gaga "MAYHEM"** (WINNER)
- Other nominees: Justin Bieber "SWAG", Sabrina Carpenter "Man's Best Friend", others

**Record of the Year**: **Kendrick Lamar & SZA "Luther"** (WINNER)
- Other nominees: Bad Bunny "DtMF", Sabrina Carpenter "Manchild", Doechii "Anxiety", others

**Best New Artist**: **Olivia Dean** (WINNER); other nominees: Katseye, The Marias, Addison Rae, Sombr, Leon Thomas, Alex Warren, Lola Young

**Key stats**: Kendrick Lamar was biggest winner (5 awards, 2nd consecutive year as biggest winner)

## Amazon Charts Strategy

### Step 1: Search for Current Charts
- `"Amazon Charts most read fiction [date] [year]"`
- `"amazon.com/charts most read fiction"`
- Note: Amazon Charts updates weekly, so search for the specific week

### Step 2: Interpret Results
- Amazon Charts ranks by average daily Kindle readers + Audible listeners
- Harry Potter books often dominate the top spots
- New releases can temporarily displace perennial bestsellers

### Key Data Points Observed
- January 2026: Harry Potter books dominated top spots, with The Correspondent (Virginia Evans) and Dungeon Crawler Carl (Matt Dinniman) also appearing

## Spotify Wrapped 2025 (Released Dec 3, 2025)
- **Most Streamed Album Globally**: "Debí Tirar Más Fotos" by Bad Bunny (#1)
- **Second Most Streamed Album**: KPop Demon Hunters Soundtrack
- **Most Streamed Album Overall (by streams)**: Kendrick Lamar's GNX (2.9B+ streams)
- Note: "Most streamed" can mean different things - check if question asks about global chart vs total streams

## Super Bowl LX Halftime Show (Feb 8, 2026)
- **Headliner**: Bad Bunny (Apple Music Super Bowl LX Halftime Show)
- **Guest appearances**: Lady Gaga (performed "Die With A Smile"), Ricky Martin, Cardi B, Karol G, Pedro Pascal
- Latin music theme at Levi's Stadium, Santa Clara, CA

## Chinese Short Drama Rankings
- **BiaNews (鞭牛士) short drama hot list (短剧热度榜) for March 9, 2026** (covering March 2-8, 2026):
  - Top-ranked short drama: 《消失的拳王第二季》 (The Disappearing Boxing Champion Season 2)
  - Top-ranked manga drama (漫剧): 《西游起源第一季》
  - Published jointly by 新腕儿 and 鞭牛士 with WETRUE
  - Search: `"鞭牛士 短剧热度榜 [date]"` for specific dates

## Chinese Media Rankings Strategy

### Maoyan 猫眼电影想看榜 (Want to Watch List)
- Search: `"猫眼电影想看榜 [date]"` for specific date data
- **March 21, 2026**: Positions 6-8 were 阳光女子合唱团, 寒战1994, 千金不换. Top was 沙丘3 (Dune 3). Positions 4-5: 迈克尔·杰克逊：巨星之路, 小黄人与大怪兽.

### Douban Rankings (豆瓣)
- **一周口碑电影榜 (weekly word-of-mouth movie ranking) March 20, 2026**: 超时空辉夜姬 was #1, 我当你兄弟 was #2, 弗兰肯斯坦 was #5. 翠湖 and 东北警察故事3 also appeared.
- **国外口碑综艺榜 (overseas variety show ranking) March 23, 2026**: Korean variety shows dominated. Show with 全炫茂/申东熙/姜智荣 was ranked #3. 怪奇谜案限时破 第二季 was ranked #4.
- Search: `"豆瓣 [ranking type] [date]"` for specific date data

### KolRank WeChat/Weibo Rankings
- Top positions consistently dominated by major Chinese state media (人民日报, 央视新闻, 新华社, 共青团中央)
- Positions 7-9 on WeChat typically include 环球时报, 人民网, 中央纪委国家监委
- Daily rankings fluctuate based on content performance
- Search: `"KolRank [platform] [date]"` for specific date data

### Youmei/Midu 政法委微博账号影响力排行榜
- Daily rankings change frequently based on activity metrics (传播力, 服务力, 互动力, 认同度)
- Published daily at 16:00 by Youmei (铀媒) platform
- Positions 15-17 are extremely hard to predict precisely
- Typical accounts: provincial and municipal political-legal committee accounts (平安北京, 平安上海, etc.)

## Gaming Announcements (March 2026)
- **Assassin's Creed: Black Flag Resynced**: Officially announced March 4-5, 2026 by Ubisoft (blog post by Jean Guesdon). PEGI rating leaked December 2025. March 20 was date for additional Twitch stream details. Game was announced BEFORE March 20, 2026.

## Dongchedi (懂车帝) Hot List Rankings Strategy
- **Hot list (热门榜)** is based on user interest/attention on the platform, NOT just sales
- **Sedan hot list (轿车全国热门榜) March 23, 2026**: #1 小米SU7 (new 2026款 launched March 19); #2 比亚迪秦L; #3 特斯拉Model 3; #4 比亚迪汉
- **SUV hot list (SUV全国热门榜) March 23, 2026**: #3 理想L6; #4 问界M7; #5 哈弗H6
- New model launches cause temporary spikes (e.g., 小米SU7 2026款 launched March 19 → #1 on March 23)
- Consistently popular sedans: 小米SU7, 比亚迪秦L/秦PLUS, 特斯拉Model 3, 比亚迪汉
- Consistently popular SUVs: 特斯拉Model Y (often #1), 理想L6, 问界M7, 哈弗H6, 比亚迪宋PLUS
- Search: "懂车帝 轿车全国热门榜 [date]" or "懂车帝 SUV全国热门榜 [date]"

## Maoyan 购票评分榜 (Ticket Purchase Rating List)
- Ranks currently-showing films by ticket purchase ratings (not box office gross)
- Spring Festival films dominate for weeks after release
- New releases can enter top 10 on premiere day
- **March 19, 2026**: Top 3 likely 飞驰人生3, 镖人：风起大漠, 惊蛰无声; positions 4-6 included 熊出没·年年有熊, 阳光女子合唱团
- 阳光女子合唱团 premiered around March 19, 2026 (首映 509.2万)
- Search: "猫眼电影购票评分榜 [date]" for specific date data

## China Spring Festival 2026 Box Office
- Top 4 Spring Festival 2026 films: 飞驰人生3 (1st), 惊蛰无声 (2nd), 镖人：风起大漠 (3rd), 熊出没·年年有熊 (4th)
- 飞驰人生3 total box office: 43.76 亿元 (as of March 19, 2026 - 47 days in theaters)
- 镖人：风起大漠 total box office: 14.33 亿元 (as of March 19, 2026 - 47 days in theaters)
- 2026 China annual box office surpassed 80 亿元 by Feb 23, 2026

## Box Office Mojo Domestic Weekly (US)
- **Week ending March 19, 2026**: #1 "Hoppers" (Pixar animated film; opened March 6 with $46M; $28.5M in second weekend)
- "Project Hail Mary" opened March 20-22, 2026 (after March 19 deadline)

## QQ Music Soaring Chart (QQ音乐飙升榜)
- Updates daily based on weekly play growth rates; highly volatile
- **March 7, 2026**: #1 aespa - 'ATTITUDE'
- **March 19, 2026 trending**: 《我对缘分小心翼翼》(林俊杰/JJ Lin), 《以闪亮之名》, "Colder"
- Search: "QQ音乐飙升榜 [date]" for specific date data

## NetEase Cloud Music 欧美热歌榜
- Updates every Thursday (每周四更新)
- March 19, 2026 was a Thursday (update day)
- Hard to predict specific positions without direct access to historical chart data
- Search: "网易云音乐欧美热歌榜 [date]" for specific date data
