# CAREN Act Federal Advocacy

This repository supports efforts to introduce and pass a federal version of San Francisco's Caution Against Racial and Exploitative Non-Emergencies (CAREN) Act.

## Live Site (GitHub Pages)

- **Home / interactive priority heat map:** https://prodataman.github.io/CAREN-Act/website/
- **Draft federal bill (click a paragraph to suggest edits):** https://prodataman.github.io/CAREN-Act/website/bill.html
- **How the SF CAREN Act came about:** https://prodataman.github.io/CAREN-Act/website/history.html
- **Contested hanging deaths & unnatural deaths by race (CDC):** https://prodataman.github.io/CAREN-Act/website/deaths.html
- **Old laws tracker (get Jim Crow / sundown laws off the books):** https://prodataman.github.io/CAREN-Act/website/laws.html
- **Data sources & methodology:** https://prodataman.github.io/CAREN-Act/website/data.html
- **Report an old law:** https://github.com/ProDataMan/CAREN-Act/issues/new?template=residual-law.yml
- **Report a contested death:** https://github.com/ProDataMan/CAREN-Act/issues/new?template=contested-death.yml
- **Original SF ordinance (PDF):** https://prodataman.github.io/CAREN-Act/docs/SF-CAREN-Act.pdf

https://prodataman.github.io/CAREN-Act/ redirects to the site. Pages deploys from the `main` branch, repository root.

## About the Original Ordinance

The San Francisco ordinance (Police Code §637, Ordinance No. 219-20, File No. 200735) makes it unlawful to knowingly cause a peace officer to contact a person with the specific intent to discriminate on the basis of protected characteristics (race, color, ancestry, ethnicity, national origin, place of birth, sex, age, religion, creed, disability, sexual orientation, gender identity, weight, or height). It creates a civil cause of action for damages: a minimum of $1,000 plus fees, with possible punitive damages.

Supervisor Shamann Walton introduced it in July 2020. It followed the June 2020 Pacific Heights incident, in which a couple called police on a Filipino American man chalking "Black Lives Matter" on his own home, and the May 2020 Central Park call by Amy Cooper about Black birdwatcher Christian Cooper. The Board passed it 11–0 on October 27, 2020. See the [history page](https://prodataman.github.io/CAREN-Act/website/history.html) for details and sources.

## Contents

- `docs/SF-CAREN-Act.pdf`: original San Francisco ordinance, with legislative history on the last page
- `website/index.html`: advocacy map built on live public data, plus a lookup that finds your representatives and drafts a letter to each
- `website/bill.html` + `website/bill.json`: draft federal bill (text lives in `bill.json`) with public, per-paragraph comments
- `website/history.html`: origin story of the SF CAREN Act
- `website/deaths.html`: disputed hanging deaths (curated in `website/data/contested_deaths.json`) and CDC charts of hanging/unnatural deaths by race
- `website/laws.html`: tracker for residual Jim Crow / sundown laws, from report → verification → drafted repeal ordinance or bill → delivery → follow-up
- `website/assets/site.css`, `website/assets/site.js`: shared header, mobile menu, and footer used by every page
- `.github/ISSUE_TEMPLATE/`: forms for reporting old laws and contested deaths
- `.github/workflows/laws-followup.yml`: daily check that reminds the volunteer on a repeal case after 30 days without an update
- `website/data.html`: data sources, priority-score methodology, recommended additional sources
- `website/data/`: generated datasets (do not hand-edit, except the curated `residual_ordinances.json`)
- `scripts/build_data.py`: fetches every dataset from its publisher and rebuilds `website/data/`
- `.github/workflows/refresh-data.yml`: reruns the data build every Monday (and on demand)
- `.github/workflows/bill-comments.yml` + `.github/scripts/apply-accepted.js`: comment labeling and accepted-edit merging
- `context.md`: living project status document

## Commenting on the Draft Bill

- Click a paragraph to propose a revised wording and/or add a comment. GitHub opens with the comment pre-filled; a free GitHub account is required to post.
- Comments are public GitHub issues labeled `bill-comment`. The page lists them live.
- Paragraphs with comments are highlighted in yellow. Click the comment icon to see them, and click a comment to see its proposed changes (removed words in red, added words in green). The bill itself always shows the current approved text.

### For editors (approving comments)

1. Open the comment's **View on GitHub** link (or the [issue list](https://github.com/ProDataMan/CAREN-Act/issues?q=label%3Abill-comment)).
2. Add the **`accepted`** label. The `Bill comments` workflow checks that you have write access, merges the proposed text into `website/bill.json`, keeps the previous text in the paragraph's `history`, comments ⭐ on the issue, and closes it. The commenter gets a gold star on the site.
3. Add the **`hidden`** label to remove spam or abuse from the site.

## Old Laws Tracker

Repeal is a legislative act: a city council, county commission, or state legislature has to vote to remove the text, and constitutional text also needs a ballot vote. The tracker never files legal motions or sends anything automatically. It:

1. collects reports through the [issue form](https://github.com/ProDataMan/CAREN-Act/issues/new?template=residual-law.yml) (label `residual-law`, `needs-verification`);
2. waits for an editor to confirm the text is in the current official code (`verified`);
3. generates a cover letter and a ready-to-adopt repeal ordinance or bill on [laws.html](https://prodataman.github.io/CAREN-Act/website/laws.html);
4. lets a real resident or an ally's office deliver it, then moves the label along: `repeal-requested` → `repeal-introduced` → `repealed`;
5. runs `laws-followup.yml` daily, which comments on any case with no update for 30 days to remind whoever took it on.

## Data

Run `python3 scripts/build_data.py` (needs `openpyxl` and `pdftotext`/poppler) to rebuild everything locally. Sources:

- EJI lynchings
- Mapping Police Violence
- FBI Crime Data Explorer hate crimes and agency locations
- Census ACS 5-year B03002
- Census Gazetteer
- Mapping Inequality HOLC
- Census ZCTA to 119th-Congress district file
- CDC/NCHS injury mortality by race and intent, 1999–2016, and suicide rates by race through 2024 (data.cdc.gov)

CDC WONDER (state and county numbers by race) blocks automated access, so those have to be exported by hand. Contested deaths are curated from reputable reporting and verified before they are added.

Members of Congress and committee rosters load live from [@unitedstates/congress-legislators](https://github.com/unitedstates/congress-legislators). Address-to-district lookups go through the Census Geocoder. See [data.html](https://prodataman.github.io/CAREN-Act/website/data.html) for methodology and recommended additional sources.

## Goal

Make similar protections against discriminatory emergency calls available nationwide through federal legislation, so the practice is illegal in every city in every state.

## Disclaimer

Map layers use publicly available historical and statistical data for educational and advocacy purposes. They illustrate patterns from sources such as the Equal Justice Initiative (lynchings 1877–1950), FBI Uniform Crime Reporting (hate crimes), Mapping Inequality / HOLC (redlining), Mapping Police Violence, and historical research on sundown towns (e.g., James Loewen). The priority-score weights are an advocacy judgment, documented on the methodology page. Formal sundown ordinances have been repealed. Claims of current operational "sundown laws" or active Jim Crow statutes require specific verification, as most have been struck down or repealed. Always verify with primary sources.

## Getting Involved

See the [website](https://prodataman.github.io/CAREN-Act/website/) for ways to support, contact representatives, and comment on the bill. Target members of Congress (especially House/Senate Judiciary) for sponsorship.
