# CAREN Act Federal Advocacy — Project Context

**Last updated:** 2026-11-08

## Goal
Create a public GitHub repository and advocacy website to support making the San Francisco CAREN Act (Caution Against Racial and Exploitative Non-Emergencies, Police Code §637 / Ordinance No. 219-20) a federal law. The federal version should prohibit discriminatory 911/emergency calls nationwide with a private right of action.

## Repository
- **URL:** https://github.com/ProDataMan/CAREN-Act
- **Owner:** ProDataMan
- **Visibility:** Public

## Progress to Date
1. Repository created (public, auto-init README).
2. README.md updated with project overview, goals, structure, and data/legal disclaimers.
3. docs/README.md added with notes on the original SF ordinance and instructions for uploading the PDF.
4. Original SF CAREN Act PDF downloaded locally (Ordinance No. 219-20). Binary not yet committed to the repo (tool limitation for binary files); user can upload manually to docs/SF-CAREN-Act.pdf.
5. website/index.html created and iteratively updated with interactive Leaflet map, toggleable layers, source links, prioritization guidance, and accurate notes on zombie ordinances.
6. **Major website expansion (latest):**
   - Added layers for police killings / disproportionate contact (linking Mapping Police Violence) and larger minority populations (Census patterns).
   - Historical sundown/redlining shown in one color; residual/zombie ordinances highlighted in a different color (example: Boynton Beach, FL 2024 repeal).
   - Allies color-coded by position and potential power/influence (high/medium/local samples).
   - Prioritization of high-overlap areas (lynchings + residual language + police violence + minority populations) via bolder/larger markers without filtering or removing other data.
   - Contact-your-representative form that prepares a pre-filled message supporting the $1,000 damages structure and opens mailto or allows copy.
   - Link to the draft bill.
7. **Draft federal bill created** as website/bill.html:
   - Model language with specific-intent standard, good-faith exception, no preemption of stronger laws, optional data collection.
   - Damages: minimum $1,000 statutory ($500 from the individual caller + $500 from the responding police department/agency) + fees + possible punitives.
   - Click any paragraph to suggest changes (suggestions stored locally in browser via localStorage; open to anyone for now; future login/moderation planned).
8. context.md maintained as the living status document.
9. **2026-11-08 update:**
   - GitHub Pages confirmed live (source: main, root). Root index.html redirects to /website/.
   - README updated with live URLs. Original SF PDF committed to docs/SF-CAREN-Act.pdf (from sfbos.org).
   - website/history.html added: origins (Walton; Pacific Heights chalk incident June 2020; Amy Cooper/Central Park May 2020), legislative timeline from the PDF (final passage 11–0 on Oct 27, 2020), provisions, parallel state laws, sources.
   - Map: added priority heat-map layer (leaflet.heat, illustrative weights), links to history and PDF, escaped contact-form output.
   - Bill comments rebuilt: click paragraph → suggest edit (prefilled text, word diff) + comment; comment icon with count → side panel listing comments + "Add new comment"; yellow highlight for paragraphs with comments; per-comment "Share on GitHub" issue link; JSON export/import. Still localStorage (v1 suggestions auto-migrated).

10. **2026-11-08 (second update):**
   - All map sample data replaced with real data built by scripts/build_data.py (weekly GitHub Action refresh):
     - EJI lynchings: 4,447 victims, 942 counties
     - Mapping Police Violence: 15k+ killings through 2026
     - FBI hate crimes 2021–2025, geolocated by agency
     - Census ACS 2020–24 minority share
     - Mapping Inequality HOLC polygons
     - Composite county priority score (methodology in website/data.html)
   - Allies layer is live: House and Senate Judiciary members (color by chair/ranking vs member), Rep. Janelle Bynum (OR-5, author of Oregon's 2019 law) as champion, Sup. Walton as local ally.
   - Residual ordinances: curated, cited file (Boynton Beach verified).
   - Segregation layer: 17 states + DC with legally segregated schools pre-1954.
   - Representative lookup: street address goes to the Census Geocoder (ACS2025_Current vintage = 119th districts). ZIP-only uses the ZCTA→CD119 file. Members come from congress-legislators. A personalized letter is drafted per member, with contact form, phone, and office address.
   - Bill comments are public via GitHub Issues (label bill-comment). The bill text lives in website/bill.json. Adding the `accepted` label triggers the workflow that merges the edit, records history, and gives the commenter a gold star; `hidden` hides spam.
   - The 120th Congress starts 2027-01-03, and several states redrew districts. The ZIP file and geocoder vintage need updating to CD120 then; congress-legislators updates members automatically.

11. **2026-11-08 (third update):**
   - New page website/deaths.html:
     - 5 verified disputed hanging deaths (Trey Reed, Tory Medley, Tasia Fortune, Justice Kai James, To'Nea Miller) in data/contested_deaths.json. Sources: Capital B News (Sept 24, 2026), Mississippi Today, Mississippi Free Press. Map layer "Contested hanging deaths".
     - CDC charts (data.cdc.gov nt65-c7a7 injury deaths by race and intent 1999–2016; w26f-tf3h suicide rates by race to 2024), built by build_data.py (`python3 scripts/build_data.py cdc` runs only this step).
     - Finding: Black Americans have the highest rate of hanging/suffocation deaths ruled homicide in every year 1999–2016, and a lower hanging-suicide rate than White Americans.
   - CDC WONDER API returns an Akamai 403 for automated requests, and CDC policy limits its API to national data anyway. State and county numbers by race need manual exports.
   - Individual case data for "all hangings in 50 years" does not exist publicly. The plan is a crowdsourced, verified case registry (issue form contested-death.yml) plus partners: JULIAN (70 cases 2000–2025), NAACP LDF (asked Congress for a commission), Capital B, The Marshall Project.
   - New page website/laws.html, the old laws tracker:
     - Issue form residual-law.yml.
     - Status labels: needs-verification → verified → repeal-requested → repeal-introduced → repealed (also not-residual).
     - Generates a cover letter plus a model repeal ordinance or state bill.
     - laws-followup.yml sends daily 30-day reminders to the adopter.
     - DECIDED: no automated legal motions, class actions, or messages sent on allies' behalf. Repeal is legislative, unenforced laws give no standing, and auto-sending or impersonation would be spam or fraud. Real people deliver each request.
   - Design: shared header and mobile hamburger menu (assets/site.css, assets/site.js) on all pages.
     - Map page: hero with calls to action; layer panel as a card over the map on desktop, collapsible on mobile; collapsible legend; `?layers=deaths` URL parameter.
     - Bill panel sits below the sticky header and is full-width on phones.
   - Labels created: residual-law, needs-verification, verified, repeal-requested, repeal-introduced, repealed, not-residual, contested-death.
   - BLOCKER: the gh token lacks the `workflow` scope. The workflow files (bill-comments, refresh-data, laws-followup) are committed locally but NOT pushed. The user must run `gh auth refresh -s workflow && git push`.

12. **2026-11-08 (fourth update):**
   - Volunteer recruitment:
     - website/volunteer.html with role cards and a state tile grid counting open `volunteer` issues.
     - Priority states: 17 segregation states + DC + the top 10 states by high-overlap counties.
     - Issue form volunteer.yml (state dropdown, roles, background, hours, commitments; no contact details because sign-ups are public).
     - Labels: volunteer, volunteer-active, cdc-wonder.
     - "Volunteer" added to the nav; the hamburger breakpoint is now 1080px.
   - CDC WONDER:
     - deaths.html#export has step-by-step instructions for two exports: hanging X70/X91/Y20 by state × race × ICD sub-chapter, and injury intent by state × race.
     - build_data.py `build_cdc_wonder()` parses website/data/cdc_wonder/*.txt into cdc_wonder_states.json (`python3 scripts/build_data.py wonder`), shown as a state table on deaths.html.
     - Volunteers upload exports through a GitHub issue labeled cdc-wonder.
   - Outreach letters drafted to JULIAN (Jill Collen Jefferson; "A Crimson Record", Feb 18 2026, 70+ cases in 7 states, database at julianfreedom.org) and the Legal Defense Fund (Aug 24 2026 letters to Congress and the UN). Kept out of the repo and handed to the user.
   - Lead to follow: congressional Democrats' Sept 2026 letter asking DOJ to investigate the hanging deaths (theGrio). Its signers are potential allies to add to the map.
   - Planned: Google/Facebook login (e.g. Supabase Auth) so volunteers and commenters don't need GitHub accounts.

13. **2026-11-08 (Azure deployment, following Ohana_Belltown's process):**
   - Ohana's process: GitHub Actions builds the Docker image, pushes it to GHCR (public package), then runs `az containerapp update` through OIDC with app registration `ohana-belltown-github-deploy` (appId c7d8073d-…). That registration is shared with No_Limit_Auto_Salon via one federated credential per repo plus Contributor on each resource group.
   - "Database server" = Azure SQL server **postgresdata.database.windows.net** (SQL Server despite the name) in RG Ohana. Existing DB: Ohana_Data (free serverless). The Ohana app itself stores JSON files and doesn't use it.
   - CREATED:
     - DB **CAREN_Act** on postgresdata (GP_S_Gen5 serverless, free limit, auto-pause 60 min, local backup redundancy).
     - RG **CARENAct** (centralus), environment **caren-act-env**, container app **caren-act-server** (system-assigned identity principal e184de7e-b9a5-41b6-9467-855ad5312ae4, 0.25 vCPU/0.5Gi, min 0 / max 2 replicas). Currently on the placeholder image.
     - App URL: https://caren-act-server.calmpebble-c668572f.centralus.azurecontainerapps.io
     - Env vars set: DB_SERVER, DB_NAME, PUBLIC_BASE_URL, CORS_ORIGINS, NODE_ENV, PORT, ADMIN_EMAILS.
   - Code:
     - server/ (Node 22 + Express + mssql, managed-identity auth, migrations, volunteers API, Google/Facebook OAuth gated by env vars, admin endpoints).
     - server/Dockerfile (repo-root build context).
     - .github/workflows/deploy-server.yml (local commit; needs workflow scope).
     - website/volunteer.html private sign-up form; website/admin.html.
   - BLOCKED (Claude's auto-mode refused permission grants; the user must run these):
     - scripts/azure-setup.sh: federated credential `caren-act-main`, Contributor on CARENAct, repo secrets AZURE_CLIENT_ID/TENANT_ID/SUBSCRIPTION_ID.
     - server/sql/grant-app-identity.sql in the Portal query editor (creates the DB user for the managed identity).
     - `gh auth refresh -s workflow,write:packages && git push`, then make the GHCR package caren-act-server public.
   - Later: new Google/Facebook OAuth clients for CAREN (don't reuse Ohana's), then set the env vars on the container app.

14. **2026-11-08 (GitHub Pages + Azure SQL):**
   - GitHub Pages is still live and serves the same site. Both copies use Azure SQL through the API.
   - Cross-site sign-in: /auth/:provider?next=<allowed origin URL> returns to GitHub Pages with #caren_token=<session>. assets/api.js stores it in localStorage and sends `Authorization: Bearer`. The server accepts the bearer or the cookie; CORS allows Authorization/PATCH for CORS_ORIGINS.
   - volunteer.html and admin.html use assets/api.js, so the admin page works on GitHub Pages too.
   - Added website/privacy.html (required for the Google/Facebook apps) and a footer link.
   - README now has an "Owner's to-do list" (steps 1–9: setup script, SQL grant, gh scopes + push, public package, verify, OAuth setup, editor tasks, outreach, Jan 2027 switch, costs).

15. **2026-11-08 (Take action features, no new keys):**
   - The lawmaker lookup moved to website/assets/reps.js (shared by index.html, act.html, embed.html).
   - New in the lookup:
     - an optional "Why does this matter to you?" story, added to every letter and call script and updated live (hand edits are kept);
     - a click-to-call button and a 30-second call script for each member;
     - a state-lawmaker card with the visitor's exact State Senate/House districts from the Census Geocoder, a state-bill letter and an Open States link. OR and CA letters ask to strengthen the existing law;
     - a city council / county board card with a local-ordinance letter. San Francisco instead gets a "thank your supervisor and back a federal bill" letter;
     - a share bar.
   - New pages:
     - act.html: Take action hub with steps, lookup, vote links (vote.gov, vote.org, VOTE411), know-your-rights links (ACLU, ILRC red cards, IDP, United We Dream, NILC, LDF, NLG) and embed code;
     - county.html?f=FIPS: stat tiles, priority rank, canvas share image (Web Share with file on mobile, download elsewhere), Facebook/X links;
     - embed.html: iframe widget.
   - Nav: added "Your county"; the CTA is now "Take action" (act.html). Menu breakpoint is now 1180px. Map county popups link to county pages.
   - Not built yet (need keys): AI letter helper (Anthropic API key; Haiku 5.5 ≈ $0.001/letter) and the state bill watcher / legislator names (free Open States key).

16. **2026-11-08 (recommended data sources added):**
   - New builders in scripts/build_data.py (standalone: `calls`, `covenants`, `mwt`, `bjs`, `acs`). In the full run, each one fails soft and keeps last week's manifest entry.
     - **districts.json:** ACS B03002 for 437 congressional (5001900US), 1,958 state senate (610U900US) and 4,873 state house (620L900US) districts, from the same bulk file as the counties. reps.js shows "% people of color" on House and state cards.
     - **city_calls.json:** resident-initiated "suspicious person" calls, past 365 days, from SF (data.sf.gov 2zdj-bwza), Seattle (33kz-ixgy) and New Orleans (yearly "Calls for Service YYYY" datasets found through the Socrata catalog). Outcomes are bucketed per city into enforcement / nothing found / other, with duplicates and cancellations dropped. Points are on a 0.005° grid, cells under 3 calls dropped. Results: SF 28,302 calls, 0.9% enforcement; Seattle 36,962, 24.0% (its category includes vehicles and incidents); New Orleans 12,549, 8.9% (reports only).
     - **lynchings_all_races.json:** Monroe Work Today explore/data/s_1_3.txt. 5,027 victims, 1818–2021; race codes grouped into B/L/N/A/W/U; 36 unknown-county records are kept but not mapped; CC BY-NC 4.0.
     - **covenants.json:** UMNLibraries/mp-us-racial-covenants GeoJSON (via Git LFS media URLs), 13 counties, about 105k covenants, grouped into 0.0025° cells (415 KB).
     - **bjs_contacts.json:** PPCS 2020 tables 3 and 6 (force: Black 4.3%, Hispanic 2.4%, White 1.5%, Asian 1.0%; street stops ending in search or arrest: Black 14.2% vs White 3.0%).
   - Map: new layers `mwt`, `calls`, `covenants`, plus legend and sources-table rows. Legend max-height is 55vh.
   - data.html: new dataset rows, a #calls outcomes table, a BJS table, and a status column on the recommendations (✅ / 🔑 / ✋).
   - Not added: LegiScan, Congress.gov and Police Scorecard (keys); Stanford OPP (multi-GB per city); Sundown Towns (permission); ADL HEAT (blocks automated download); LCCR/NAACP report cards (PDFs).

17. **2026-11-09 (deploy, comments, county location):**
   - The user ran `gh auth refresh -s workflow,write:packages`. The four workflows were pushed, and the Azure secrets were already set (Step 1 ran).
   - The first deploy failed at OIDC login (AADSTS700213). GitHub sends ID-based subjects (`repo:ProDataMan@9538094/CAREN-Act@1450580633:ref:refs/heads/main`). Creating the federated credential was blocked in auto mode, so the README has the exact command for the user. azure-setup.sh now creates both forms.
   - Comments weren't appearing because none had ever been posted. The repo had zero issues: the flow needs a GitHub sign-in and clicking Create, and the labeling workflow wasn't pushed yet.
   - Fix: POST /api/comments on the server creates the labeled issue with GITHUB_TOKEN (a fine-grained PAT, Issues read/write on this repo only; README Step 6b). It validates the marker, JSON block and title; rate-limits 10/hour per IP; has a honeypot; breaks @mentions; and adds "Posted from the website by: <name>". /api/health reports `comments: true/false`.
   - bill.html posts through the API when available (optional name field), otherwise falls back to GitHub with a clear "not saved until you click Create" note. parseIssue shows `data.name` (or Anonymous) for website comments.
   - county.html: "Use my location" button (browser geolocation → Census geocoder coordinates → county; nearest-centroid fallback).
   - Race breakdown (window.CarenRace in site.js): groups listed largest first, stopping once the groups shown cover ≥50% of the people-of-color share or once both Black and Hispanic are shown. Used in map pop-ups, county tiles and lawmaker cards (embed.html now loads site.js).
   - Data: counties.json rows gained pct_asian, pct_native, pct_pacific and pct_other_or_multiracial (indices 15–18); districts.json entries gained the same (indices 4–7). The standalone `acs` build refreshes them in place.

18. **2026-11-09:** The user added the ID-based federated credential, and the deploy succeeded (run 42565633712). /api/health: db ok, comments false (GITHUB_TOKEN not set yet), auth not configured. CORS from prodataman.github.io verified. Remaining owner steps: 6b (comment token) and 6 (OAuth).

## Key Legal & Data Notes (for accuracy)
- SF CAREN Act is a local civil ordinance only. Federal version modeled on it.
- Explicit good-faith exception retained.
- Formal sundown ordinances are not currently enforceable. Residual “zombie” language exists in some codes until cleaned up and is shown in a distinct highlight color. Historical research areas use a different color.
- Lynchings: EJI. Police violence: Mapping Police Violence (disproportionate minority impact documented). Hate crimes: FBI UCR.
- No comprehensive national public geocoded dataset of race-motivated 911 calls exists.
- Most formal Jim Crow statutes have been repealed or struck down.
- Census Data API now requires a key; the pipeline uses keyless bulk files instead. WaPo police-shootings data stopped at 2024-12-31, so Mapping Police Violence is used.

## Next Steps
1. ~~Enable GitHub Pages~~ Done: https://prodataman.github.io/CAREN-Act/website/
2. ~~Upload the SF CAREN Act PDF~~ Done.
2a. ~~Shared comment backend~~ Done (GitHub Issues). Optional later: allow comments without a GitHub account (would need a hosted backend plus moderation).
2b. Jan 2027: switch the ZIP→district file to CD120 and the geocoder layer to 120th districts.
2d. Push workflow files after `gh auth refresh -s workflow`.
2e. Seed the old laws tracker: check UNC "On the Books" (NC) and the South Carolina project results against the current codes; recruit verifiers per state.
2f. Send the outreach letters to JULIAN and LDF (drafted 2026-11-08).
2g. Add Google/Facebook sign-in (Supabase Auth or Firebase) for volunteers and commenters; move volunteer contact details to private storage.
2h. Add the signers of the Sept 2026 congressional letter asking DOJ to investigate the hangings as allies on the map.
2i. When keys exist: AI letter helper endpoint on the Azure server (Anthropic key, Haiku 5.5, rate limits, Console spend cap) and the weekly Open States + Congress.gov bill watcher Action with hearing alerts to state volunteers.
2k. Data follow-ups: add more cities to CITY_CALLS (Detroit, Cincinnati, Dallas…); a one-time Stanford OPP extract of search rates by race; ask Tougaloo for Sundown Towns data; have a volunteer export ADL HEAT and transcribe the LCCR scorecard; consider citing the 911-outcome and BJS figures in the bill's findings.
2j. Optional: Spanish translations of act.html and the letters (volunteer-reviewed).
2c. Add recommended data sources (LegiScan, Congress.gov, Stanford Open Policing, city 911 data). See website/data.html.
3. Further expand map samples or begin integrating real GeoJSON (county boundaries + attributes from EJI, Mapping Police Violence, Census).
4. Identify and list specific potential congressional sponsors/champions (especially Judiciary members or newly elected with civil rights records).
5. Add a short data-methodology page.
6. Improve suggestion system (export suggestions, optional backend later).
7. Refine contact form with actual district lookup if possible.

## Clarifying Questions Outstanding / Resolved
- Prioritization without filtering: implemented via emphasis markers.
- Residual vs historical: different colors applied.
- Allies: color-coded by power/position (samples).
- Focus on high lynchings/police killings/disproportionate contact + larger minority populations: layers added and prioritized.
- Bill damages structure: $500 individual + $500 agency implemented in draft.
- Click-to-suggest on bill paragraphs: implemented (localStorage).

## How to Continue on Another Machine/Account
- Clone or browse https://github.com/ProDataMan/CAREN-Act
- Read this context.md first for full status.
- Website: index.html (map + contact Congress), bill.html (draft + public comments), deaths.html (contested deaths + CDC data), laws.html (old laws tracker), history.html, data.html. Shared nav: assets/site.js + site.css.
- To update files: use GitHub web editor, git, or API tools as available.
- After any successful change, update this context.md with new progress and revised next steps.

---
*This file is the single source of truth for project status. Update it after every successful action.*