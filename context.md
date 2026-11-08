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
5. website/index.html created and iteratively updated:
   - Interactive Leaflet.js map of the US.
   - Toggleable sample layers: Hate Crimes (FBI UCR), Historical Lynchings (EJI), Southern States (slavery/Jim Crow history), Sundown histories / residual ordinances / redlining, Potential Allies.
   - Direct links to authoritative sources: EJI Lynching map, FBI Crime Data Explorer, Mapping Inequality (HOLC redlining), Loewen/Tougaloo sundown database.
   - Prioritization guidance for areas with overlapping high lynching history + residual discriminatory ordinance language + elevated hate crime or race-motivated 911 patterns.
   - Accurate notes on “zombie ordinances” (obsolete text that may remain until repealed; unenforceable under Equal Protection, Civil Rights Act, Fair Housing Act). Example: Boynton Beach, FL repealed three segregation/sundown-era ordinances in 2024.
6. Website updated with stronger source links and prioritization call-out (commit 73b7ff6).

## Key Legal & Data Notes (for accuracy)
- SF CAREN Act is a local civil ordinance only. It creates a private right of action (min $1,000 damages + fees + possible punitives) for knowingly causing a peace officer to contact a person with specific intent to discriminate on listed protected characteristics or to cause enumerated harms.
- Explicit good-faith exception for reports of actual or reasonably suspected crime/danger.
- Formal sundown ordinances are not currently enforceable. Residual “zombie” language exists in some codes until cleaned up. Historical sundown-town research (Loewen) documents thousands of places that were deliberately exclusionary for decades.
- Lynchings: EJI documents >4,000 racial terror lynchings (1877–1950), concentrated in the South.
- Hate crimes: FBI UCR — race/ethnicity is the largest bias category.
- No comprehensive national public geocoded dataset of race-motivated 911 calls exists.
- Most formal Jim Crow statutes have been repealed or struck down.

## Next Steps
1. **Enable GitHub Pages** (manual):
   - Repo Settings → Pages → Deploy from branch → main → /website (or root).
   - Live URL will be https://prodataman.github.io/CAREN-Act/ (or /website/).
2. Upload the SF CAREN Act PDF to docs/SF-CAREN-Act.pdf.
3. Expand map with prioritized high-overlap counties/cities (sample markers with citations from EJI + sundown database + residual ordinance examples).
4. Add a “Contact your representative” section or pre-filled email links targeting House/Senate Judiciary members.
5. Draft a model federal bill outline in the repo (findings, specific-intent standard, good-faith exception, damages, no preemption of stronger state/local laws, optional data-collection provision).
6. Add data-methodology page and/or expand layers with real GeoJSON where feasible (county boundaries + EJI/FBI attributes).
7. Identify and list specific potential congressional sponsors/champions (especially newly elected or members with civil rights records).

## Clarifying Questions Outstanding
- Prioritize specific high-overlap counties with custom markers, or keep broader illustrative layers?
- Focus “laws on the books” layer only on verified residual/zombie ordinances (with citations) or also include broader historical sundown research areas?
- Allies layer scope: Judiciary members only, or wider set with civil-rights sponsorship records?
- Any preferred states/metros to emphasize first?

## How to Continue on Another Machine/Account
- Clone or browse https://github.com/ProDataMan/CAREN-Act
- Read this context.md first for full status.
- Website source: website/index.html
- To update files: use GitHub web editor, git, or API tools as available.
- After any successful change, update this context.md with new progress and revised next steps.

---
*This file is the single source of truth for project status. Update it after every successful action.*