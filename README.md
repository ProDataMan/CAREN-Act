# CAREN Act Federal Advocacy

This repository supports efforts to introduce and pass a federal version of San Francisco's Caution Against Racial and Exploitative Non-Emergencies (CAREN) Act, which makes it unlawful to call the police on someone to discriminate against them.

## Live site

The site runs at **https://prodataman.github.io/CAREN-Act/website/** (GitHub Pages; https://prodataman.github.io/CAREN-Act/ redirects there). An identical copy with a private database runs on Azure (see [Two copies of the site](#two-copies-of-the-site-one-database)).

**Take action**
- **Take action hub:** call and write your members of Congress, state lawmakers and city council, register to vote, know your rights: https://prodataman.github.io/CAREN-Act/website/act.html
- **Your county's numbers, with a share image and "Use my location":** https://prodataman.github.io/CAREN-Act/website/county.html (e.g. [Hinds County, MS](https://prodataman.github.io/CAREN-Act/website/county.html?f=28049))
- **Draft federal bill (click a paragraph to comment or suggest an edit):** https://prodataman.github.io/CAREN-Act/website/bill.html
- **Volunteer as a state ally:** https://prodataman.github.io/CAREN-Act/website/volunteer.html
- **Embeddable lawmaker lookup for partner sites:** https://prodataman.github.io/CAREN-Act/website/embed.html (embed code on the Take action page)

**Learn**
- **How we got here, and the way out:** sourced history lessons with evidence labels, quizzes, quests, XP and badges: https://prodataman.github.io/CAREN-Act/website/learn.html
- **First modules:** [Before race: where the fear came from](https://prodataman.github.io/CAREN-Act/website/module.html?m=before-race), [Science as a weapon](https://prodataman.github.io/CAREN-Act/website/module.html?m=science), [Policing and the 911 call](https://prodataman.github.io/CAREN-Act/website/module.html?m=policing), [The path forward](https://prodataman.github.io/CAREN-Act/website/module.html?m=path-forward)

**Map and data**
- **Priority heat map:** https://prodataman.github.io/CAREN-Act/website/
- **How to read the map, with one-click example views:** https://prodataman.github.io/CAREN-Act/website/#how-to-read
- **Data sources, methodology and worked score examples:** https://prodataman.github.io/CAREN-Act/website/data.html (scores: [#score](https://prodataman.github.io/CAREN-Act/website/data.html#score); what "suspicious person" 911 calls lead to: [#calls](https://prodataman.github.io/CAREN-Act/website/data.html#calls))
- **Contested hanging deaths and CDC deaths by race:** https://prodataman.github.io/CAREN-Act/website/deaths.html (CDC WONDER export guide for volunteers: [#export](https://prodataman.github.io/CAREN-Act/website/deaths.html#export))
- **Old laws tracker (getting Jim Crow and sundown laws off the books):** https://prodataman.github.io/CAREN-Act/website/laws.html
- **How the SF CAREN Act came about:** https://prodataman.github.io/CAREN-Act/website/history.html
- **Original SF ordinance (PDF):** https://prodataman.github.io/CAREN-Act/docs/SF-CAREN-Act.pdf

**Report something**
- **An old law still on the books:** https://github.com/ProDataMan/CAREN-Act/issues/new?template=residual-law.yml
- **A contested death:** https://github.com/ProDataMan/CAREN-Act/issues/new?template=contested-death.yml

Map links can preselect layers and a location, for example `?layers=redlining,covenants&at=44.96,-93.27,12` (latitude, longitude, zoom). A `?layers=` link shows exactly the layers listed.

---

## Status at a glance (November 9, 2026)

| Area | Status |
|---|---|
| GitHub Pages site | ✅ Live, redeploys on every push to `main` |
| Azure server + database | ✅ Live. Deploys on every push. `/api/health` reports `"db":"ok"` |
| Volunteer sign-up (private, Azure SQL) | ✅ Works on both copies of the site. No sign-ups yet |
| Bill comments | ✅ Switched on (Nov 9): the website posts comments directly. A first live test comment is still to come |
| Google sign-in | ✅ Switched on (Nov 9). Test it on the admin page and the Learn page |
| Facebook sign-in | ⬜ Not started (see [Step C](#c-facebook-sign-in-optional)) |
| Weekly data refresh | ✅ Runs Mondays 09:17 UTC. Tested by hand on Nov 9. It now also redeploys the Azure copy |
| Learn section | ✅ Live: 4 modules drafted (1, 5, 8, 10), 6 outlined. Progress saves by device ID; sign-in adds a profile and badge card. ⚠️ No historian has reviewed the modules yet |
| GitHub issues | None yet: no comments, old-law reports, volunteers or cases filed |
| Outreach to JULIAN and LDF | ⬜ Letters drafted, not yet sent |

Check the server at any time:

```bash
curl https://caren-act-server.calmpebble-c668572f.centralus.azurecontainerapps.io/api/health
```

`"db":"ok"`, `"comments":true` and `"google":true` mean everything is switched on. `"db":"waking"` is normal for up to a minute after the database has been idle.

---

## Owner's to-do list

### A. Switch on website comments (1 minute)

The `github-token` secret is already stored on the app, but the app isn't told to use it. Run this together with Step B:

```bash
az containerapp update -n caren-act-server -g CARENAct --set-env-vars \
  GITHUB_TOKEN=secretref:github-token \
  GOOGLE_OAUTH_CLIENT_SECRET=secretref:google-client-secret
```

Then `/api/health` should show `"comments":true`, and the bill page's button changes from **Continue to post on GitHub** to **Post comment**. Website comments are posted as GitHub issues labeled `bill-comment`, with "Posted from the website by: <name>" (or *Anonymous*). Each IP address can post 10 an hour, and @mentions are disabled so a comment can't notify GitHub users.

The token should be a fine-grained token limited to this repository with only **Issues: Read and write**, and it expires after the period you chose. To replace it, create a new one at https://github.com/settings/personal-access-tokens/new and run `az containerapp secret set -n caren-act-server -g CARENAct --secrets github-token=NEW_TOKEN`, then restart the app (`az containerapp revision restart`, or push any change).

### B. Finish Google sign-in (1 minute)

`GOOGLE_OAUTH_CLIENT_ID` and the `google-client-secret` secret are set. The command in Step A also connects the secret. Afterward:

1. Check that the Google OAuth client's **Authorized redirect URI** is exactly `https://caren-act-server.calmpebble-c668572f.centralus.azurecontainerapps.io/auth/google/callback`.
2. Check that the OAuth consent screen is **published** (not "Testing"), with the privacy policy URL `https://prodataman.github.io/CAREN-Act/website/privacy.html`.
3. `/api/health` should show `"google":true`. Open https://prodataman.github.io/CAREN-Act/website/admin.html, sign in with your Google account (it's in `ADMIN_EMAILS`), and you'll see the volunteer list.

To add admins: `az containerapp update -n caren-act-server -g CARENAct --set-env-vars ADMIN_EMAILS=you@example.com,other@example.com`. This replaces the list, so include yourself.

### C. Facebook sign-in (optional)

1. Go to https://developers.facebook.com/apps → **Create App**, and choose **Authenticate and request data from users with Facebook Login**.
2. **Use cases → Facebook Login → Settings**: add the Valid OAuth Redirect URI `https://caren-act-server.calmpebble-c668572f.centralus.azurecontainerapps.io/auth/facebook/callback`.
3. **App settings → Basic**: set the Privacy Policy URL and the *Data deletion instructions URL* to `https://prodataman.github.io/CAREN-Act/website/privacy.html`. Copy the **App ID** and **App Secret**.
4. Make sure the `email` permission is added, then switch the app to **Live**.
5. Store the credentials:
   ```bash
   az containerapp secret set -n caren-act-server -g CARENAct --secrets facebook-app-secret=PASTE_SECRET
   az containerapp update -n caren-act-server -g CARENAct --set-env-vars \
     FACEBOOK_OAUTH_APP_ID=PASTE_APP_ID FACEBOOK_OAUTH_APP_SECRET=secretref:facebook-app-secret
   ```

### D. Outreach

Send the letters to JULIAN (Jill Collen Jefferson) and the NAACP Legal Defense Fund through their website contact forms. They were shared with you privately and aren't stored in this public repo. Point new volunteers to the volunteer page.

### E. January 3, 2027: switch to the 120th Congress

Several states redrew their districts. When the new Congress is seated:

1. In `scripts/build_data.py`, change `zcta_cd` to the Census 120th-Congress ZCTA file once it's published, and run the full build.
2. In `website/assets/reps.js`, change the geocoder match to `/120th Congressional/` and the vintage to `Current_Current`.
3. Re-run the data build so `districts.json` uses the new districts once the Census bulk file includes them.

Member names and contact details update on their own from `congress-legislators`.

### F. Later, when you have the keys (optional)

- **AI letter helper:** turns a visitor's few sentences into a polished personal letter that they review and send. It needs an Anthropic API key from https://console.anthropic.com, billed separately from a Claude Pro subscription. With Claude Haiku 5.5, a letter costs about $0.001, so 1,000 letters is roughly $1. Set a monthly spend limit (for example $10) under Billing → Limits.
- **State legislator names and a weekly state bill watcher:** these need a free Open States key from https://open.pluralpolicy.com/accounts/profile/. Until then, the lookup shows each visitor's exact state districts and links to Open States.
- **Federal bill tracking:** this needs a free Congress.gov (api.data.gov) key.
- **Police Scorecard data:** request a key at policescorecard.org.

---

## Ongoing editor work

| Task | Where | How |
|---|---|---|
| Approve a bill comment | [Issues labeled `bill-comment`](https://github.com/ProDataMan/CAREN-Act/issues?q=label%3Abill-comment) | Add the `accepted` label. The edit is merged into the bill on both copies of the site and the commenter gets a ⭐. Add `hidden` for spam. |
| Verify an old-law report | [Issues labeled `residual-law`](https://github.com/ProDataMan/CAREN-Act/issues?q=label%3Aresidual-law) | Confirm the citation in the current official code, then swap `needs-verification` for `verified`. Move it along `repeal-requested` → `repeal-introduced` → `repealed`, or label it `not-residual`. |
| Welcome a volunteer | `/website/admin.html` (private sign-ups) or [issues labeled `volunteer`](https://github.com/ProDataMan/CAREN-Act/issues?q=label%3Avolunteer) | Set status **active** on the admin page, or add `volunteer-active`, then assign them to reports in their state. |
| Add a contested-death case | [Issues labeled `contested-death`](https://github.com/ProDataMan/CAREN-Act/issues?q=label%3Acontested-death) | Verify the sources, then add an entry to `website/data/contested_deaths.json` and push. |
| Add CDC WONDER exports | [Issues labeled `cdc-wonder`](https://github.com/ProDataMan/CAREN-Act/issues?q=label%3Acdc-wonder) | Save the `.txt` files to `website/data/cdc_wonder/`, run `python3 scripts/build_data.py wonder`, and push. |
| **New law or history source found** | `website/data/learn.json`, then README and `context.md` | **Standing rule:** add it to the right module's section, timeline and `sourcesList`, with an evidence label (`documented`, `debated` or `belief`). Then update this README and `context.md`. |
| Review a Learn module | `website/data/learn.json` | Once a historian has reviewed a module, change its `status` from `draft` to `reviewed` and update the `review` note at the top. |
| Refresh map data now | Actions → **Refresh map data** → **Run workflow** | Runs automatically every Monday. |
| Change the priority-score weights | `PRIORITY_WEIGHTS` in `scripts/build_data.py` | Keep them adding up to 1, run `python3 scripts/build_data.py`, and push. Examples are on [data.html#score](https://prodataman.github.io/CAREN-Act/website/data.html#score). |
| Watch the server | `az containerapp logs show -n caren-act-server -g CARENAct --tail 100` | Also see https://github.com/ProDataMan/CAREN-Act/actions for deploys. |

---

## Two copies of the site, one database

| | GitHub Pages | Azure |
|---|---|---|
| URL | https://prodataman.github.io/CAREN-Act/website/ | https://caren-act-server.calmpebble-c668572f.centralus.azurecontainerapps.io/website/ |
| Hosting | Free static hosting, deployed on every push to `main` (branch `main`, repo root) | Container App `caren-act-server`, deployed by `deploy-server.yml` |
| Volunteer sign-up, coverage counts | Calls the Azure API (CORS) | Same origin |
| Sign-in and admin page | Signs in on Azure, then returns with a session token kept in the browser and sent as `Authorization: Bearer` | Regular sign-in cookie |
| Bill comments | Read from GitHub issues; posted through the Azure API when it's switched on, otherwise through GitHub | Same |
| Map, data, trackers, lookup | Static | Static |

Browsers never connect to the database directly. Every read and write goes through the API on Azure. If the API is down, GitHub Pages keeps working and falls back to GitHub-based sign-up and commenting.

## Azure resources

| Resource | Details |
|---|---|
| Container App | `caren-act-server`, resource group `CARENAct` (Central US), environment `caren-act-env`, 0–2 replicas (scales to zero), port 8080, system-assigned managed identity |
| Image | `ghcr.io/prodataman/caren-act-server:<commit sha>` (public package) |
| Database | `CAREN_Act` on Azure SQL server `postgresdata.database.windows.net` (resource group `Ohana`; SQL Server despite the name). Serverless GP_S_Gen5 on the free offer, auto-pauses after 60 minutes, and pauses rather than bills if the free monthly limit is used up. The app signs in with its managed identity, so there's no password |
| Deploy identity | App registration `ohana-belltown-github-deploy` (shared with Ohana_Belltown and No_Limit_Auto_Salon). Federated credentials `caren-act-main` and `caren-act-main-withid` (GitHub's ID-based subject `repo:ProDataMan@9538094/CAREN-Act@1450580633:ref:refs/heads/main`), with Contributor on `CARENAct` only |
| Repo secrets | `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` |
| App settings | `DB_SERVER`, `DB_NAME`, `PUBLIC_BASE_URL`, `CORS_ORIGINS` (https://prodataman.github.io), `NODE_ENV`, `PORT`, `ADMIN_EMAILS`, `GOOGLE_OAUTH_CLIENT_ID`. To be connected: `GITHUB_TOKEN`, `GOOGLE_OAUTH_CLIENT_SECRET`. Optional: `FACEBOOK_OAUTH_APP_ID`/`FACEBOOK_OAUTH_APP_SECRET`, `GITHUB_REPO` |
| App secrets | `github-token`, `google-client-secret` (add `facebook-app-secret` for Step C) |

**Rebuilding from scratch:** `scripts/azure-setup.sh` creates both federated credentials, the role assignment and the repo secrets. `server/sql/grant-app-identity.sql` (run in the Portal query editor for `CAREN_Act` while signed in with Microsoft Entra) creates the database user for the app's identity. The GHCR package must be public. Your GitHub CLI needs the `workflow` and `write:packages` scopes to push workflow files.

### Costs

- **Container App:** scales to zero when idle and should stay within Azure's monthly free grant at campaign traffic, plus a small Log Analytics workspace for logs.
- **Database:** on Azure SQL's free offer (100,000 vCore-seconds and 32 GB a month). It pauses if that runs out, so there are no overage charges.
- **GitHub Pages, Actions and public container images:** free.

## Server API (`server/`)

Node.js 22 + Express + `mssql`. It serves `website/` and `docs/`, and creates its tables from `server/src/migrations/*.sql` on first start.

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Database, comments and sign-in status |
| `POST /api/volunteers` | Private volunteer sign-up (rate-limited, honeypot) |
| `GET /api/volunteers/coverage` | Public counts by state only |
| `POST /api/comments` | Posts a bill comment as a labeled GitHub issue (needs `GITHUB_TOKEN`). Validates the comment format, allows 10 per hour per IP, and disables @mentions |
| `GET /api/me` | Current sign-in |
| `POST /api/learn/sync` | Learn progress. Takes the browser's random device ID and its event keys (`read:<module>`, `quiz:<module>`, `quest:<id>`). Returns the saved events. XP comes from `learn.json` on the server, never from the browser. When signed in, it moves the device's progress onto the profile. 120 calls per hour per IP |
| `GET /api/learn/teams` | XP and learner counts by state (public totals only) |
| `GET /api/admin/volunteers`, `PATCH /api/admin/volunteers/:id` | Admin only |
| `/auth/google`, `/auth/facebook`, `/auth/logout` | Sign-in. After sign-in, GitHub Pages gets its session token in the URL fragment, and only origins in `CORS_ORIGINS` can receive it |

To run it locally: `cd server && npm install && DB_SERVER=postgresdata.database.windows.net DB_NAME=CAREN_Act npm start`. Your `az login` must be allowed through the SQL firewall.

## GitHub Actions

| Workflow | Trigger | What it does |
|---|---|---|
| `deploy-server.yml` | Every push to `main` that touches `server/`, `website/` or `docs/`, or a manual run | Builds the image, pushes it to GHCR, and updates the Container App through OIDC |
| `refresh-data.yml` | Mondays 09:17 UTC, or a manual run | Rebuilds `website/data/` from the publishers, commits any changes, rebuilds GitHub Pages and starts the Azure deploy |
| `bill-comments.yml` | New, edited or labeled issues | Labels website comments `bill-comment`. When an editor adds `accepted`, merges the edit into `website/bill.json`, stars the commenter, and redeploys both copies |
| `laws-followup.yml` | Daily | Reminds whoever took on a repeal case after 30 days without an update |

Commits made by a workflow don't trigger other workflows, so the refresh and comment workflows start the Azure deploy explicitly.

---

## How the main features work

### Lawmaker lookup (`website/assets/reps.js`)

Used on the map page, the Take action page and the embed. A street address goes only to the U.S. Census Geocoder, which returns the congressional district, state senate and house districts, county and city. A ZIP code alone falls back to the ZIP-to-district file. For each senator and representative, the lookup shows:
- a click-to-call button and a 30-second call script;
- a letter that includes the visitor's optional personal story and updates as they type (hand edits are kept);
- the official contact form;
- the district's demographics.

It also drafts letters to state lawmakers (asking states with a related law to strengthen it) and to the city council or county board (San Francisco instead gets a "thank your supervisor" letter). Members load live from `@unitedstates/congress-legislators`.

### Priority heat map

Every county gets a score from 0 to 1. The weights are 30% lynching history (EJI), 30% police killings per resident, 15% race/ethnicity hate crimes per resident, and 25% share of residents who are people of color. Rates are smoothed for small counties and capped at the 95th percentile. Glows are weighted by score², and neighboring glows add up, so red marks regional clusters. Purple rings mark counties that are high on at least 3 of the 4 factors. The full explanation is at [#how-to-read](https://prodataman.github.io/CAREN-Act/website/#how-to-read), and the math at [data.html#score](https://prodataman.github.io/CAREN-Act/website/data.html#score).

Race breakdowns ("63% people of color (Asian 35%)") list groups largest first. They stop once the groups shown add up to half of all people of color, or once both Black and Hispanic have appeared.

### Commenting on the draft bill

- **Commenting:** click a paragraph to propose new wording and/or comment. Comments are public GitHub issues labeled `bill-comment`, and the page lists them live.
- **Highlights:** paragraphs with comments are highlighted in yellow. Click a comment to see its changes, with removed words in red and added words in green. The bill always shows the approved text.
- **Not posted yet:** if a comment goes through GitHub and the person never clicks **Create**, it exists only in their own browser as *Pending*. **Discard** deletes it.
- **For editors:** adding `accepted` merges the text into `website/bill.json`, keeps the old wording in the paragraph's `history`, stars the commenter and closes the issue. `hidden` removes spam.

### State allies (volunteers)

The [volunteer page](https://prodataman.github.io/CAREN-Act/website/volunteer.html) has a private sign-up form, stored in Azure SQL and visible only to admins, plus a public GitHub sign-up as a fallback. The tile map shows coverage by state from both. The roles are law verifier, case verifier, CDC data exporter, local deliverer, legal reviewer, researcher and history reviewer. The [privacy policy](https://prodataman.github.io/CAREN-Act/website/privacy.html) explains what's collected and how to delete it.

### Learn (education)

[learn.html](https://prodataman.github.io/CAREN-Act/website/learn.html) is the hub, and `module.html?m=<id>` renders each module. All the content lives in **`website/data/learn.json`**: modules (sections, timelines, quizzes, sources), the Source detective quiz, quests, XP values, levels and badges. To add or fix content you edit only that file. The plan and the build phases are in [docs/education-plan.md](docs/education-plan.md).

- **Evidence labels:** every section is labeled *Documented*, *Debated* or *Belief or myth*.
- **XP:** 20 for reading a module, 30 for passing its quiz (80%), and 15–400 for quests, depending on how much the task matters. Quests are on the honor system for now.
- **Levels:** Listener, Learner, Witness, Ally, Organizer, Changemaker.
- **Badges:** 9.
- **Saving progress:** without an account, progress lives in the browser under a random device ID and is backed up to Azure SQL (`learn_events`). Signing in with Google moves it onto a profile that works on any device and adds a downloadable badge card.
- **State teams:** pick a state and your XP counts toward its total on the leaderboard.
- **Recruiting reviewers:** the volunteer page has a new *History reviewer* role ([volunteer.html#reviewer](https://prodataman.github.io/CAREN-Act/website/volunteer.html#reviewer)).

### Old laws tracker

Repeal is a legislative act, so the tracker never files legal motions or sends anything automatically. It:
1. collects reports through the issue form;
2. waits for an editor to verify each one against the current official code;
3. generates a cover letter and a ready-to-adopt repeal ordinance or bill on [laws.html](https://prodataman.github.io/CAREN-Act/website/laws.html);
4. lets a real resident or an ally's office deliver it;
5. tracks status by label, with 30-day reminders.

---

## Data

`scripts/build_data.py` fetches every dataset from its publisher and writes compact JSON to `website/data/` (needs Python 3.9+, `openpyxl` and `pdftotext`/poppler). Run everything with `python3 scripts/build_data.py`, or a single source with `python3 scripts/build_data.py calls`. The other single-source options are `covenants`, `mwt`, `bjs`, `acs`, `cdc` and `wonder`. If one of the newer sources fails during the weekly refresh, last week's file is kept.

| Dataset | File |
|---|---|
| EJI racial terror lynchings 1877–1950 (county supplement) | `counties.json` |
| Mapping Police Violence, 2013–present | `police_killings.json` |
| FBI Crime Data Explorer hate crimes, located by agency | `hate_crimes.json` |
| Census ACS 5-year B03002 (counties, all races) | `counties.json` |
| Census ACS by 119th congressional, state senate and state house district | `districts.json` |
| Census Gazetteer; ZCTA → 119th district relationship file | `counties.json`, `zip_districts.json` |
| Mapping Inequality HOLC redlining | `redlining.json` |
| Mapping Prejudice racial covenants, 13 counties | `covenants.json` |
| Monroe Work Today lynchings of all races (CC BY-NC 4.0) | `lynchings_all_races.json` |
| "Suspicious person" 911 calls and outcomes, past 12 months: San Francisco, Seattle, New Orleans (add cities in `CITY_CALLS`) | `city_calls.json` |
| BJS Police-Public Contact Survey 2020 | `bjs_contacts.json` |
| CDC/NCHS injury deaths by race and intent; suicide rates by race | `cdc_deaths.json` |
| CDC WONDER state exports (by hand; the site blocks automated access) | `cdc_wonder_states.json` |
| Contested deaths (curated from reputable reporting) | `contested_deaths.json` |
| Residual ordinances (curated, cited; the only hand-edited data file besides contested deaths) | `residual_ordinances.json` |

**Not added yet** (see the status column on [data.html](https://prodataman.github.io/CAREN-Act/website/data.html)):
- **Needs an API key:** LegiScan, Congress.gov, Police Scorecard.
- **Files too large for the weekly refresh:** Stanford Open Policing (multi-GB per city).
- **Needs permission:** Sundown Towns database.
- **Needs a volunteer export or a partnership:** ADL H.E.A.T. map, civil-rights voting report cards.

## Contents

- `website/`: the site.
  - **Pages:** `index.html` (map), `act.html`, `county.html`, `embed.html`, `bill.html` + `bill.json`, `deaths.html`, `laws.html`, `history.html`, `learn.html` + `module.html` (content in `data/learn.json`), `data.html`, `volunteer.html`, `admin.html`, `privacy.html`.
  - **`assets/`:** `site.css`, `site.js` (header, menu, footer, race breakdown), `api.js` (Azure API client), `reps.js` (lawmaker lookup), `learn.js` (Learn progress, XP, badges, quizzes).
  - **`data/`:** generated datasets.
- `server/`: Node.js API and static server for Azure, with `Dockerfile` and `sql/grant-app-identity.sql`.
- `scripts/build_data.py`: data pipeline. `scripts/azure-setup.sh`: one-time Azure permissions.
- `.github/workflows/`, `.github/scripts/apply-accepted.js`, `.github/ISSUE_TEMPLATE/`: automation and issue forms.
- `docs/education-plan.md`: the plan for the Learn section.
- `docs/SF-CAREN-Act.pdf`: the original ordinance, with its legislative history on the last page.
- `context.md`: project status and decisions.

## About the original ordinance

The San Francisco ordinance (Police Code §637, Ordinance No. 219-20, File No. 200735) makes it unlawful to knowingly cause a peace officer to contact a person with the specific intent to discriminate on the basis of a protected characteristic, such as race, religion or sexual orientation. It creates a civil cause of action for damages of at least $1,000 plus fees, with possible punitive damages.

Supervisor Shamann Walton introduced it in July 2020, after the June 2020 Pacific Heights incident (a couple called police on a Filipino American man chalking "Black Lives Matter" outside his own home) and the May 2020 Central Park call by Amy Cooper about Black birdwatcher Christian Cooper. The Board of Supervisors passed it 11–0 on October 27, 2020. See the [history page](https://prodataman.github.io/CAREN-Act/website/history.html).

## Goal

Make protections against discriminatory emergency calls available nationwide through federal legislation, so the practice is illegal in every city in every state.

## Disclaimer

Map layers use publicly available historical and statistical data for education and advocacy. The priority-score weights are an advocacy judgment, documented on the methodology page. The heat map shows where to prioritize outreach; it is not a count of discriminatory calls, and no national data on those exists. Formal sundown ordinances have been repealed or struck down. Any claim that a specific racist law is still on the books needs verification against the current official code. Always verify with primary sources.
