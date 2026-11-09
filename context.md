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
| Azure | Live. Image deployed for commit 0f5a9bb+. `/api/health`: `db ok`, `comments false`, `google false`, `facebook false` |
| Workflows | All four pushed. Deploy succeeds. Refresh run tested by hand on 2026-11-09 |
| Comments | `github-token` secret exists on the app, but the `GITHUB_TOKEN` setting isn't connected to it. Command in README Step A |
| Google sign-in | `GOOGLE_OAUTH_CLIENT_ID` is set and the `google-client-secret` secret exists, but `GOOGLE_OAUTH_CLIENT_SECRET=secretref:google-client-secret` isn't set (same command) |
| Facebook sign-in | Not started |
| Content | 0 GitHub issues: no comments, old-law reports, volunteers or cases yet. 0 volunteer sign-ups in SQL |
| Outreach | Letters to JULIAN and LDF drafted (kept out of the repo), not sent |

## Architecture

- **Static site** in `website/`. The shared header, menu, footer and race-breakdown helper (`window.CarenRace`) live in `assets/site.js` and `site.css`.
  - `assets/api.js`: client for the Azure API. Same origin on Azure or localhost; otherwise the Azure URL plus a bearer token.
  - `assets/reps.js`: lawmaker lookup, used by `index.html`, `act.html` and `embed.html`.
- **Server** in `server/`: Node 22, Express, `mssql` with managed-identity auth, migrations in `src/migrations`.
  - **Endpoints:** health, volunteers (sign-up, coverage, admin), comments (creates a GitHub issue), Google/Facebook OAuth.
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
| contested_deaths.json, residual_ordinances.json | Curated and cited. The only hand-edited data files |

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
- **Bill damages:** $500 from the caller plus $500 from the responding agency (user's structure).

## Key legal and data notes

- The SF CAREN Act is a local civil ordinance. Related state laws: Oregon (2019, $250 cap) and California AB 1775 (2020, criminal penalties).
- Formal sundown ordinances and most Jim Crow statutes have been repealed or struck down. Leftover "zombie" text is tracked only once verified.
- No national dataset of race-motivated 911 calls exists. The map shows proxies, and city outcome data is the closest direct evidence.
- The Census API needs a key, so the pipeline uses keyless bulk files. The Washington Post police-shootings data ended 2024-12-31, so the site uses Mapping Police Violence.
- The 120th Congress starts 2027-01-03, and several states redrew districts. The lookup uses 119th districts until then.

## Next steps

1. **Owner:** connect `GITHUB_TOKEN` and `GOOGLE_OAUTH_CLIENT_SECRET` to their secrets (README Step A). Then test a website comment and the admin sign-in.
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
10. **Education component ("Learn"):** plan in `docs/education-plan.md`. It covers 10 history modules with evidence labels (documented / debated / belief or myth), a History map layer group with a year slider, quests tied to real tasks, and state team scores. Phase 1 builds the evidence policy, the timeline, and modules 1 (why the fear), 5 (science and reproductive control) and 8 (policing). Waiting on the owner's answers to the open questions at the end of the plan.

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
  - **The owner's test comment:** it was never posted and lives only in their browser as Pending. Discard removes it.
