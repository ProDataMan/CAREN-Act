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
- Website: website/index.html (map + heat map + contact), website/bill.html (draft + comments), website/history.html (origins).
- To update files: use GitHub web editor, git, or API tools as available.
- After any successful change, update this context.md with new progress and revised next steps.

---
*This file is the single source of truth for project status. Update it after every successful action.*