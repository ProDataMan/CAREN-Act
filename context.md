# CAREN Act Federal Advocacy: Project Context

**Last updated:** 2026-11-09

Read this first when picking up the project. The README holds the owner's to-do list and how-tos; this file holds the current state, the decisions and their reasons, and the history.

## Goal

A public repository and advocacy site supporting a federal version of San Francisco's CAREN Act (Caution Against Racial and Exploitative Non-Emergencies, Police Code §637, Ordinance No. 219-20). The federal bill would prohibit knowingly causing police to contact someone with the specific intent to discriminate, with a private right of action. The draft sets a $1,000 minimum, $500 from the caller and $500 from the responding agency, plus fees.

## Where things are

- **Repo:** https://github.com/ProDataMan/CAREN-Act (public; owner ProDataMan; commits as ProDataMan <Antoine.Victor@ProDataMan.com>)
- **Site:** https://prodataman.github.io/CAREN-Act/website/ (GitHub Pages, `main`, repo root; the root `index.html` redirects)
- **Azure copy and API:** https://caren-act-server.calmpebble-c668572f.centralus.azurecontainerapps.io

## Current state (2026-11-09)

| Area | State |
|---|---|
| GitHub Pages | Live |
| Azure | Live, deployed for commit c359e78 (Learn). `/api/health`: `comments true`, `google true`, `facebook false`. Migration 002 applied, and `/api/learn/sync` tested live |
| Workflows | All four pushed. Deploy succeeds. Refresh run tested by hand on 2026-11-09 |
| Comments | `GITHUB_TOKEN` is connected (2026-11-09). Posting from the website is on; no live test comment yet |
| Google sign-in | Connected (2026-11-09). Not tested end to end yet |
| Facebook sign-in | Not started |
| Content | 0 GitHub issues: no comments, old-law reports, volunteers or cases yet. 0 volunteer sign-ups in SQL |
| Learn | Live. Hub `learn.html`, renderer `module.html`, teach-in kits `teach.html`, content `data/learn.json`. 39 modules, all written (status `draft` until reviewed). Order: before-race, columbus, colonizers, afro-latino, conquest, slavery-law, reconstruction, black-towns, faith, christian-nationalism, veterans, science, health, borders, place, destroyed, schools, wealth, labor, banking, environment, voting, incarceration, policing, courts, surveillance, technology, media, many-targets, women, culture, lgbtq, systemic, evidence, twenty-twenties, performance, world, movements, path-forward. 42 quests, 13 badges, `threeThings`, `readingList`. Labels: documented, debated, belief, plan. Not reviewed by a historian yet; recruiting through `history-reviewer` |
| Outreach | Letters to JULIAN and LDF drafted (kept out of the repo), not sent |

## Architecture

- **Static site** in `website/`. The shared header, menu, footer and race-breakdown helper (`window.CarenRace`) live in `assets/site.js` and `site.css`.
  - `assets/api.js`: client for the Azure API. Same origin on Azure or localhost; otherwise the Azure URL plus a bearer token.
  - `assets/reps.js`: lawmaker lookup, used by `index.html`, `act.html` and `embed.html`.
  - `assets/learn.js`: `window.CarenLearn`. Handles the device ID (`localStorage` `caren-device`), local progress (`caren-learn`), syncing through `/api/learn/sync`, XP, levels and badges, plus shared UI (`ui.quiz`, `ui.timeline`, `ui.chip`, `ui.award`).
  - **Learn content:** all in `data/learn.json`. The server reads the same file to set XP, so the browser can't award itself XP.
- **Server** in `server/`: Node 22, Express, `mssql` with managed-identity auth, migrations in `src/migrations`.
  - **Endpoints:** health, volunteers (sign-up, coverage, admin), comments (creates a GitHub issue), Learn (`/api/learn/sync`, `/api/learn/teams`), Google/Facebook OAuth.
  - **Migrations:** `001_initial` (users, sessions, volunteers) and `002_learn` (`learn_events`: `device_id` or `user_id`, `event_key`, `xp`, `state`). Signing in claims the device's rows and removes duplicates.
  - **Sessions:** a cookie on Azure; on GitHub Pages, a bearer token handed back as `#caren_token=` only to `CORS_ORIGINS`.
- **Azure:**
  - **Container App:** `caren-act-server` in RG `CARENAct` (centralus), env `caren-act-env`, 0–2 replicas, port 8080, system identity e184de7e-b9a5-41b6-9467-855ad5312ae4.
  - **Database:** `CAREN_Act` on `postgresdata.database.windows.net` (Azure SQL despite the name, RG `Ohana`), GP_S_Gen5 serverless on the free offer, auto-pause after 60 minutes, pauses when the free limit is used up.
  - **Ohana_Data:** Ohana's own database on the same server, untouched.
- **Deploy:** GHCR image `ghcr.io/prodataman/caren-act-server:<sha>` (public), then `az containerapp update --image` through OIDC.
  - **Identity:** app registration `ohana-belltown-github-deploy` (shared with Ohana_Belltown and No_Limit_Auto_Salon), with Contributor on `CARENAct`.
  - **Federated credentials:** `caren-act-main` (`repo:ProDataMan/CAREN-Act:ref:refs/heads/main`) and `caren-act-main-withid` (`repo:ProDataMan@9538094/CAREN-Act@1450580633:ref:refs/heads/main`). GitHub now sends the ID-based form.
- **Workflows:**
  - `deploy-server.yml`: push to server/website/docs, or a manual run.
  - `refresh-data.yml`: Mondays 09:17 UTC. Commits data, rebuilds Pages, and starts the deploy with `gh workflow run`, because pushes made with the workflow token don't trigger workflows.
  - `bill-comments.yml`: labels comments, merges accepted edits, stars the commenter and redeploys.
  - `laws-followup.yml`: daily 30-day reminders.
- **Data pipeline:** `scripts/build_data.py`.
  - The full run rebuilds everything.
  - Standalone runs: `cdc`, `wonder`, `calls`, `covenants`, `mwt`, `bjs`, `acs`. `acs` also refreshes the race columns in `counties.json` in place.
  - The newer builders fail soft and keep last week's manifest entry.
  - Score weights are in `PRIORITY_WEIGHTS`.

## Data files (website/data)

| File | Source / notes |
|---|---|
| counties.json | Gazetteer + ACS B03002 + EJI + MPV + FBI. Fields 0–14: fips, name, state, lat, lon, pop, pct_minority, pct_black, pct_hispanic, lynchings, police_killings, police_killings_black, race_hate_crimes, score, overlap. 15–18: pct_asian, pct_native, pct_pacific, pct_other_or_multiracial |
| districts.json | ACS B03002 for 437 CD119 (`5001900US`), 1,958 state senate (`610U900US`) and 4,873 state house (`620L900US`) districts. Entry: [pop, minority, black, hispanic, asian, native, pacific, other]. Keys match Census Geocoder GEOIDs |
| city_calls.json | Resident-initiated "suspicious person" calls, past 365 days. SF (data.sf.gov 2zdj-bwza), Seattle (33kz-ixgy; category includes vehicles and incidents), New Orleans (yearly "Calls for Service YYYY" datasets found through the Socrata catalog). Outcomes are bucketed per city. Points on a 0.005° grid, cells under 3 calls dropped. Nov 2026: SF 28,302 calls, 0.9% arrest/citation/report; Seattle 36,962, 24.0%; New Orleans 12,549, 8.9% (reports only) |
| lynchings_all_races.json | Monroe Work Today explore/data/s_1_3.txt. 5,027 victims; race codes grouped B/L/N/A/W/U; 36 unknown-county records kept but unmapped (lat null). CC BY-NC 4.0 |
| covenants.json | UMNLibraries/mp-us-racial-covenants GeoJSON via Git LFS media URLs, 13 counties, ~105k covenants in 0.0025° cells |
| bjs_contacts.json | PPCS 2020 tables 3 and 6. Threat or use of force: Black 4.3%, Hispanic 2.4%, White 1.5%, Asian 1.0%. Street stops ending in search or arrest: Black 14.2%, White 3.0% |
| police_killings.json, hate_crimes.json, redlining.json, zip_districts.json, cdc_deaths.json, cdc_wonder_states.json | As named. CDC WONDER exports are made by hand |
| contested_deaths.json, residual_ordinances.json | Curated and cited. Hand-edited |
| destroyed_communities.json | Curated, 34 places (Tulsa/Greenwood, Colfax, Wilmington, Elaine, Ocoee, Rosewood, Seneca Village, Bruce's Beach, Vanport, Katrina, urban renewal and highways, Chinese expulsions, gentrification). Map layer `destroyed`, colored by type: massacre, expulsion, flood, seized, renewal, gentrification. Hand-edited |
| history_sites.json | 10 WRA incarceration camps and 16 major federal Indian boarding schools (of the 408 in the Interior report), with years. Map layer `history`. Hand-edited |
| learn.json | Learn content: modules, the Source detective quiz, quests and XP, levels and badges. Hand-edited. Section labels: `documented` / `debated` / `belief` |

## Decisions (and why)

- **No automated legal filings, class actions or messages on anyone's behalf.** Repeal is legislative, unenforced laws give no one standing to sue, and auto-sending or impersonation would be spam or fraud. People deliver every request themselves, and the site only drafts.
- **Contested deaths are presented as disputed, not as proven lynchings.** Only verified cases from reputable reporting are included.
- **No sending to the CDC WONDER API or ADL** to get around their blocks. Those exports are done by hand by volunteers.
- **Auto-mode limits:** Claude's auto mode is blocked from granting Azure permissions (federated credentials, role assignments, SQL grants, firewall rules). Those steps are written out for the owner to run.
- **Raw IDs stay out of the public repo:** no subscription or tenant IDs. Scripts look them up at runtime.
- **Comments go through GitHub issues** so moderation, history and editor approval stay in one place. The server posts on visitors' behalf only with a narrowly scoped token, validated and rate-limited.
- **Node instead of Vapor for the server:** no maintained SQL Server driver for Swift.
- **Race breakdowns:** groups largest first, stopping once the groups shown cover ≥50% of the people-of-color share or both Black and Hispanic are shown (user's rule).
- **Education content is labeled by evidence level, and modules are reviewed by an expert before publishing.** Religious or conspiracy stories (the Curse of Ham, race myths built on Enoch, "Planned Parenthood was founded to exterminate Black Americans") are explained and labeled as beliefs, next to what the record shows. One weak claim would discredit the documented ones.
- **Learn progress:** saved by an anonymous device ID by default. Google sign-in adds a profile that works across devices and a badge card (owner's choice). XP scales with how much a task matters, from 15 to 400. Quests use the honor system until they can be verified.
- **Learn is its own menu item**, and the History page links to its key modules (owner's choice).
- **Standing rule (owner):** whenever we find a new law or a new history source, update the Learn modules in `learn.json`, then the README and context.md.
- **Bill damages:** $500 from the caller plus $500 from the responding agency (user's structure).

## Key legal and data notes

- The SF CAREN Act is a local civil ordinance. Related state laws: Oregon (2019, $250 cap) and California AB 1775 (2020, criminal penalties).
- Formal sundown ordinances and most Jim Crow statutes have been repealed or struck down. Leftover "zombie" text is tracked only once verified.
- No national dataset of race-motivated 911 calls exists. The map shows proxies, and city outcome data is the closest direct evidence.
- The Census API needs a key, so the pipeline uses keyless bulk files. The Washington Post police-shootings data ended 2024-12-31, so the site uses Mapping Police Violence.
- The 120th Congress starts 2027-01-03, and several states redrew districts. The lookup uses 119th districts until then.

## Next steps

1. **Owner:** test a website comment, the admin sign-in and the Learn profile sign-in. The env vars were connected on 2026-11-09.
2. **Owner:** Facebook sign-in (optional, README Step C). Send the outreach letters (Step D).
3. **2027-01-03:** switch the ZIP file, geocoder vintage and districts to the 120th Congress (README Step E).
4. Seed the old laws tracker: check UNC "On the Books" (NC) and the South Carolina project findings against current codes, and recruit verifiers in each state.
5. Add the signers of the Sept 2026 congressional letter asking DOJ to investigate the hanging deaths as allies on the map.
6. Consider citing the 911-outcome and BJS figures in the bill's findings section.
7. Data follow-ups:
   - more cities in `CITY_CALLS` (Detroit, Cincinnati, Dallas);
   - a one-time Stanford Open Policing extract of search rates by race;
   - ask Tougaloo for the Sundown Towns data;
   - a volunteer to export ADL HEAT and transcribe the civil-rights scorecards.
8. When keys exist:
   - AI letter helper (Anthropic key, Claude Haiku 5.5, about $0.001 per letter, Console spend cap);
   - Open States key for legislator names and a weekly state bill watcher with hearing alerts;
   - Congress.gov key.
9. Optional: Spanish translations of `act.html` and the letters, reviewed by a volunteer.
10. **Learn, next steps** (plan in `docs/education-plan.md`). As of 2026-11-10, all 27 modules are written, and the teach-in kits, the year slider and the camp/school layer are built. Remaining:
    - **Most important:** recruit a history reviewer, have them review each module, and change its `status` to `reviewed`.
    - Replace Wikipedia links with primary sources, and add URLs to sources cited only by title.
    - Add the full list of 408 boarding schools (from the Interior report's appendix) and a sterilizations-by-state layer (needs a reliable per-state source, such as Kaelber's site, with permission).
    - Automatic quests for accepted bill edits (gold star) and verified law reports. That needs a link between GitHub identity and Learn profiles.
    - Spanish: translate the full text of the remaining Learn modules into `learn.es.json`, and have a fluent volunteer review everything.
    - Fundraising: a fiscal sponsor or nonprofit first, then a Support page.

## History (condensed)

- **2026-11-08:**
  - **Foundation:** repo, README, original SF PDF (from sfbos.org), history page, GitHub Pages.
  - **Map on live data:** EJI, MPV, FBI, ACS, HOLC, segregation states, residual ordinances, allies (House and Senate Judiciary members, Rep. Janelle Bynum, Sup. Shamann Walton), priority score and heat map.
  - **Draft bill:** in `bill.json`, with public per-paragraph comments through GitHub issues, word diffs, editor acceptance and gold stars.
  - **Lawmaker lookup:** Census Geocoder, ZIP fallback, letter for each member.
  - **Contested deaths page:** 5 verified cases, CDC charts, CDC WONDER volunteer export guide.
  - **Old laws tracker:** issue form, statuses, generated repeal drafts, 30-day follow-up.
  - **Shared design:** nav and mobile menu.
  - **Volunteer recruitment:** private Azure SQL sign-up, admin page, privacy page.
  - **Azure deployment:** following Ohana_Belltown's process.
  - **GitHub Pages ↔ Azure:** CORS and bearer-token sign-in.
  - **Take action features:** call scripts, personal story, state and local letters, county share cards, embed widget.
  - **Recommended data sources added:** district demographics, city 911 outcomes, Monroe Work Today, Mapping Prejudice, BJS.
- **2026-11-09:**
  - **Workflows and deploy:** the owner added the `workflow` and `write:packages` scopes, the workflows were pushed, and the ID-based federated credential fixed the deploy (AADSTS700213).
  - **Comments:** found that none had ever been posted (GitHub's Create step), and added `POST /api/comments` with a clearer fallback.
  - **County page:** "Use my location", plus the fuller race breakdown, with Asian, Native, Pacific and other shares added to the county and district data.
  - **Heat map:** explainer on the map page with example views, `?at=` support, `?layers=` made exact, and worked score examples on the data page.
  - **Workflow fixes:** the refresh and comment workflows now redeploy Azure after their commits, and the covenant listing uses the workflow token.
  - **Education plan:** `docs/education-plan.md` drafted (systemic racism history, map history layers, gamified quests).
  - **Learn built:**
    - hub and module pages;
    - modules 1, 5, 8 and 10 drafted, with timelines, quizzes and sources;
    - the Source detective quiz, 12 quests, 6 levels and 9 badges;
    - progress saved by device ID with an optional profile, plus state teams;
    - the history-reviewer volunteer role, History page links, and privacy policy updates.
- **2026-11-10:**
  - **New module "Burned, flooded and taken":**
    - Greenwood/Black Wall Street in detail (2001 commission, 2024 grave identification and dismissed lawsuit, 2025 DOJ report);
    - other massacres;
    - expulsions and seizures (Forsyth, Seneca Village, Bruce's Beach, Chavez Ravine, Black farmland);
    - floods (Oscarville/Lake Lanier, 1927, Vanport, Katrina);
    - urban renewal and highways;
    - gentrification, labeled debated.
  - **Data:** `destroyed_communities.json`, with its map layer and a Tulsa example view.
  - **Quests:** "Uncover local history" (60 XP, crowdsources new places).
  - **Proposed modules** added to `docs/education-plan.md`.
  - **Six more modules:** black-towns, wealth, voting, incarceration, many-targets (Latino, Asian, Native) and performance (audit studies, achievement, the inferiority myth). Modules were reordered roughly by time.
  - **Quests and badges:** 26 new quests in community, pro bono and build-wealth categories, plus advocacy (register voters, poll worker, op-ed, fair hiring, run for office); 4 new badges; "three things everyone should know".
  - **The six outlines are now full modules:** conquest, slavery-law, reconstruction, borders, place, world. New quests: `whose-land` and `check-deed`.
  - **More modules:** columbus, colonizers, systemic, evidence, banking, courts.
    - **The Columbus module** presents his journal ("none of them black"), the 1498 Guinea-canoes passage, Peter Martyr, al-ʿUmarī and Van Sertima. Pre-Columbian African contact is labeled *debated*; "African villages already there" is labeled *belief or myth*.
  - **Stories** (`stories.html`): submission with consent, an elder interview guide, and links to archives.
    - **Database:** migration `003_stories`.
    - **API:** `/api/stories`; admin review on `admin.html`.
    - **Quests:** `share-story`, and `oral-history` now links here. Both are awarded on submission.
    - "Stories" added to the nav.
  - **County story** (`county.html#town`): builds a county's local history from all the datasets.
    - Monroe Work Today matched by "County, ST"; covenants by jurisdiction; contested deaths by county.
    - Destroyed communities, sites, old laws and redlining cities by distance from the county center.
    - New `redlining_cities.json` (city grade counts plus centers), written by `write_redlining_cities` in `build_redlining`.
  - **New modules:** afro-latino, christian-nationalism, technology, twenty-twenties, labor, culture. Spanish titles and summaries are in `learn.es.json`.
  - **Local action toolkit** (`toolkit.html`): copy-ready templates. Linked from act.html, and the council-resolution, speak-council, op-ed and coalition quests point to it.
  - **Spanish (hub and spoke):**
    - **Engine:** in `site.js`. It picks the language from `?lang=`, then `localStorage` `caren-lang`, then the browser locale, and shows a selector in the header. It translates text and attributes through a MutationObserver. Writes only happen when the text changes, to avoid an observer loop.
    - **Header:** collapses to the menu when the links don't fit (`.site-header.compact`).
    - **Files:** `i18n/es.json` (about 1,100 strings plus patterns), `data/learn.es.json` (interface, quests and badges; titles and summaries for all modules; full text for before-race, evidence, policing and path-forward), and `scripts/i18n_extract.py`.
    - **Kept in English:** the bill text, letters and repeal drafts.
  - **Map:** `history` layer, and a year slider (`?year=`) that filters any layer whose markers carry a `year` option (mwt, destroyed, history).
  - **Automatic quests:** `quest:volunteer` on a successful sign-up and `quest:suggest-bill-edit` on a successful website comment (`learn.js` is loaded on `volunteer.html` and `bill.html`).
  - **New topic modules:** environment, surveillance, media, veterans, schools, health, women, lgbtq and faith, plus the reading list.
  - **How movements won** (`movements`, with the `plan` label and the `power-map` quest) and **teach-in kits** (`teach.html`).
  - **Fundraising:** discussed with the owner, not built. The recommendation is a fiscal sponsor or nonprofit structure before collecting money (see the plan).
  - **The owner's test comment:** it was never posted and lives only in their browser as Pending. Discard removes it.
