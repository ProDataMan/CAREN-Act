# CAREN Act Federal Advocacy

This repository supports efforts to introduce and pass a federal version of San Francisco's Caution Against Racial and Exploitative Non-Emergencies (CAREN) Act.

## Live Site (GitHub Pages)

- **Home / interactive priority heat map:** https://prodataman.github.io/CAREN-Act/website/
- **How to read the heat map, with example views:** https://prodataman.github.io/CAREN-Act/website/#how-to-read. Links like `?layers=redlining,covenants&at=44.96,-93.27,12` open a chosen set of layers at a place. Score weights live in `PRIORITY_WEIGHTS` in `scripts/build_data.py`; there's a worked example at https://prodataman.github.io/CAREN-Act/website/data.html#score
- **Take action (call and write Congress, state lawmakers and city council; register to vote; know your rights):** https://prodataman.github.io/CAREN-Act/website/act.html
- **Your county's numbers + share image:** https://prodataman.github.io/CAREN-Act/website/county.html (e.g. [Hinds County, MS](https://prodataman.github.io/CAREN-Act/website/county.html?f=28049))
- **Embeddable lawmaker lookup for partner sites:** https://prodataman.github.io/CAREN-Act/website/embed.html (embed code on the Take action page)
- **Draft federal bill (click a paragraph to suggest edits):** https://prodataman.github.io/CAREN-Act/website/bill.html
- **How the SF CAREN Act came about:** https://prodataman.github.io/CAREN-Act/website/history.html
- **Contested hanging deaths & unnatural deaths by race (CDC):** https://prodataman.github.io/CAREN-Act/website/deaths.html
- **Old laws tracker (get Jim Crow / sundown laws off the books):** https://prodataman.github.io/CAREN-Act/website/laws.html
- **Data sources & methodology:** https://prodataman.github.io/CAREN-Act/website/data.html
- **What "suspicious person" 911 calls lead to (SF, Seattle, New Orleans):** https://prodataman.github.io/CAREN-Act/website/data.html#calls
- **New map layers:** [lynchings of all races, 911 calls, racial covenants](https://prodataman.github.io/CAREN-Act/website/?layers=mwt,calls,covenants)
- **Volunteer as a state ally (verifiers, data exporters, local deliverers):** https://prodataman.github.io/CAREN-Act/website/volunteer.html
- **CDC WONDER export guide for volunteers:** https://prodataman.github.io/CAREN-Act/website/deaths.html#export
- **Report an old law:** https://github.com/ProDataMan/CAREN-Act/issues/new?template=residual-law.yml
- **Report a contested death:** https://github.com/ProDataMan/CAREN-Act/issues/new?template=contested-death.yml
- **Original SF ordinance (PDF):** https://prodataman.github.io/CAREN-Act/docs/SF-CAREN-Act.pdf

https://prodataman.github.io/CAREN-Act/ redirects to the site.

## Two copies of the site, one database

The site runs in two places. Both use the same Azure SQL database through the campaign API. Browsers can never connect to a database directly, so every database read or write goes through the API on Azure.

| | GitHub Pages | Azure |
|---|---|---|
| URL | https://prodataman.github.io/CAREN-Act/website/ | https://caren-act-server.calmpebble-c668572f.centralus.azurecontainerapps.io/website/ |
| Hosting | Free static hosting, deployed automatically on every push to `main` | Container App `caren-act-server`, deployed by `.github/workflows/deploy-server.yml` |
| Volunteer sign-up | ✅ posts to the Azure API (CORS) and is stored in Azure SQL | ✅ same |
| Coverage by state | ✅ from the Azure API plus GitHub sign-ups | ✅ same |
| Google/Facebook sign-in and admin page | ✅ sign-in happens on Azure, then returns to GitHub Pages with a session token (kept in the browser's localStorage and sent as `Authorization: Bearer`) | ✅ uses a regular sign-in cookie |
| Everything else (map, bill comments, trackers, data) | ✅ | ✅ |

Until the setup steps below are finished, the Azure API isn't running. GitHub Pages still works, but it hides the private sign-up form and shows only the GitHub sign-up.

---

## Owner's to-do list (step by step)

Do these **in order**. Steps 1–6b are one-time setup for the Azure deployment. Step 7 onward covers ongoing work.

What's already done: database `CAREN_Act` on `postgresdata`, resource group `CARENAct`, Container Apps environment `caren-act-env`, and Container App `caren-act-server` with its managed identity and settings. The app is still running a placeholder image.

### Status (Nov 9, 2026)

Steps 1–5 are done. The deploy runs on every push, the server is live, and `/api/health` reports `"db":"ok"`. A second federated credential, `caren-act-main-withid`, was added because GitHub now identifies repos by permanent IDs, and `scripts/azure-setup.sh` creates both. **Next: Step 6b (website comments), then Step 6 (sign-in).**

### Step 1. Let GitHub Actions deploy to Azure (about 2 minutes)

This uses the same deploy identity as Ohana_Belltown and No_Limit_Auto_Salon.

```bash
cd ~/GitRepos/CAREN-Act
az login                     # if you aren't already signed in
bash scripts/azure-setup.sh  # read it first, it's short
```

The script does three things:

1. Adds federated credentials named `caren-act-main` and `caren-act-main-withid` (GitHub's newer ID-based format) to the `ohana-belltown-github-deploy` app registration, so GitHub Actions on this repo's `main` branch can sign in to Azure without a password.
2. Gives that identity **Contributor on the `CARENAct` resource group only**. It gets no new access to `Ohana` or the SQL server.
3. Sets the repo secrets `AZURE_CLIENT_ID`, `AZURE_TENANT_ID` and `AZURE_SUBSCRIPTION_ID`, the same names Ohana uses.

Check it worked with `gh secret list -R ProDataMan/CAREN-Act`, which should list the three secrets.

### Step 2. Give the app access to its database (about 3 minutes)

1. Open https://portal.azure.com, search for **SQL databases**, and open **CAREN_Act** (server `postgresdata`).
2. Click **Query editor (preview)** in the left menu.
3. Under *Microsoft Entra authentication*, click **Continue as** your account.
   - If it says your IP isn't allowed, click **Allowlist IP …** and try again. You can delete that rule later under the server's **Networking** page.
4. Paste the contents of [`server/sql/grant-app-identity.sql`](server/sql/grant-app-identity.sql) and click **Run**. You should see *Query succeeded*.

This creates a database user for the app's managed identity, so there's no password to manage. It has access to `CAREN_Act` only, not `Ohana_Data`.

### Step 3. Let your GitHub CLI push workflow files and container images, then push

```bash
gh auth refresh -h github.com -s workflow,write:packages   # follow the browser prompt
cd ~/GitRepos/CAREN-Act
git push
```

This publishes four GitHub Actions workflows that are committed locally but couldn't be pushed without the `workflow` permission:

| Workflow | What it does |
|---|---|
| `deploy-server.yml` | Builds and deploys to Azure. Runs on every push to `main` that touches `server/`, `website/` or `docs/` |
| `bill-comments.yml` | Labels website comments and merges accepted edits into the bill |
| `refresh-data.yml` | Rebuilds the map data every Monday |
| `laws-followup.yml` | Sends 30-day reminders on repeal cases |

The push starts the first **Build and deploy server** run. Watch it at https://github.com/ProDataMan/CAREN-Act/actions.

### Step 4. Make the container image public (one time)

The first run creates the image `ghcr.io/prodataman/caren-act-server`. GitHub makes new images private, and Azure can only pull public ones, the same as Ohana's.

1. Open https://github.com/users/ProDataMan/packages/container/caren-act-server/settings.
2. Under **Danger Zone**, click **Change visibility**, choose **Public** and confirm.
3. Re-run the deploy: go to **Actions → Build and deploy server → Run workflow**, or click **Re-run all jobs** on the first run.

### Step 5. Check that it's live

```bash
curl https://caren-act-server.calmpebble-c668572f.centralus.azurecontainerapps.io/api/health
```

You want `"db":"ok"`. The very first call can say `"waking"` for up to a minute while the paused database resumes. The app creates its tables on that first connection.

Then open the volunteer page on **both** copies of the site. The private sign-up form should appear on each, and test sign-ups should show up in the database.

- https://caren-act-server.calmpebble-c668572f.centralus.azurecontainerapps.io/website/volunteer.html
- https://prodataman.github.io/CAREN-Act/website/volunteer.html

If something fails, check the logs:

```bash
az containerapp logs show -n caren-act-server -g CARENAct --tail 100
```

### Step 6. Turn on Google and Facebook sign-in

Sign-in is needed for the admin page. Your email is already the admin (`ADMIN_EMAILS`). Create **new** OAuth apps named for the campaign rather than reusing Ohana's, because users see the app's name when they sign in.

**Google**

1. Go to https://console.cloud.google.com and create a project such as **Federal CAREN Act**.
2. Open **APIs & Services → OAuth consent screen**:
   - Choose **External** and enter the app name *Federal CAREN Act*, your support email, and the privacy policy URL `https://prodataman.github.io/CAREN-Act/website/privacy.html`.
   - Add only the scopes `openid`, `email` and `profile`. These don't need Google verification.
   - Click **Publish app** so anyone can sign in, not just test users.
3. Open **APIs & Services → Credentials → Create credentials → OAuth client ID**:
   - Application type: **Web application**.
   - Authorized redirect URI: `https://caren-act-server.calmpebble-c668572f.centralus.azurecontainerapps.io/auth/google/callback`
   - Click **Create** and copy the **Client ID** and **Client secret**.
4. Store them on the app. The secret goes in as a Container Apps secret, not a plain setting:

   ```bash
   az containerapp secret set -n caren-act-server -g CARENAct --secrets google-client-secret=PASTE_SECRET
   az containerapp update -n caren-act-server -g CARENAct --set-env-vars \
     GOOGLE_OAUTH_CLIENT_ID=PASTE_CLIENT_ID GOOGLE_OAUTH_CLIENT_SECRET=secretref:google-client-secret
   ```

**Facebook**

1. Go to https://developers.facebook.com/apps, click **Create App**, and choose the use case **Authenticate and request data from users with Facebook Login**.
2. Open **Use cases → Facebook Login → Settings** and add this to **Valid OAuth Redirect URIs**: `https://caren-act-server.calmpebble-c668572f.centralus.azurecontainerapps.io/auth/facebook/callback`
3. Open **App settings → Basic** and set:
   - **Privacy Policy URL**: `https://prodataman.github.io/CAREN-Act/website/privacy.html`
   - **User data deletion**: choose *Data deletion instructions URL* and enter the same privacy URL. It explains how to request deletion.
   - Copy the **App ID** and **App Secret**.
4. Under **Use cases → Facebook Login → Permissions**, make sure `email` is added. Then switch the app from *Development* to **Live**.
5. Store the credentials:

   ```bash
   az containerapp secret set -n caren-act-server -g CARENAct --secrets facebook-app-secret=PASTE_SECRET
   az containerapp update -n caren-act-server -g CARENAct --set-env-vars \
     FACEBOOK_OAUTH_APP_ID=PASTE_APP_ID FACEBOOK_OAUTH_APP_SECRET=secretref:facebook-app-secret
   ```

**Check:** `curl https://caren-act-server.calmpebble-c668572f.centralus.azurecontainerapps.io/api/health` should now show `"google":true` and `"facebook":true`. The sign-in buttons appear on the volunteer and admin pages on both copies of the site.

**Admins:** open `/website/admin.html` on either copy, sign in, and you'll see every sign-up with filters, status changes and a CSV download. To add more admins:

```bash
az containerapp update -n caren-act-server -g CARENAct --set-env-vars ADMIN_EMAILS=you@example.com,other@example.com
```

### Step 6b. Let visitors post bill comments without a GitHub account (about 3 minutes)

Without this, commenting opens GitHub with the comment pre-filled. The comment isn't saved until the person signs in to GitHub and clicks **Create**, and most people won't. With it, the Azure server posts the comment for them as a labeled GitHub issue, and it appears on the bill page right away.

1. Create a fine-grained token: https://github.com/settings/personal-access-tokens/new
   - **Token name:** `caren-act-comments`. **Expiration:** 1 year. Add a calendar reminder to renew it.
   - **Repository access:** *Only select repositories* → `CAREN-Act`
   - **Permissions → Repository → Issues:** *Read and write*. Leave everything else as *No access*.
   - Click **Generate token** and copy it.
2. Store it on the app:
   ```bash
   az containerapp secret set -n caren-act-server -g CARENAct --secrets github-token=PASTE_TOKEN_HERE
   az containerapp update -n caren-act-server -g CARENAct --set-env-vars GITHUB_TOKEN=secretref:github-token
   ```
3. Check that `curl https://caren-act-server.calmpebble-c668572f.centralus.azurecontainerapps.io/api/health` shows `"comments":true`. The bill page's button then reads **Post comment** instead of **Continue to post on GitHub**.

Website comments show "Posted from the website by: <name>" (or *Anonymous*). Each IP address can post 10 per hour, and @mentions are disabled so a comment can't notify GitHub users. Remove spam by adding the `hidden` label.

### Step 7. Ongoing editor work (on GitHub)

| Task | Where | How |
|---|---|---|
| Approve a bill comment | [Issues labeled `bill-comment`](https://github.com/ProDataMan/CAREN-Act/issues?q=label%3Abill-comment) | Add the `accepted` label. The edit is merged into the bill and the commenter gets a ⭐. Add `hidden` for spam. |
| Verify an old-law report | [Issues labeled `residual-law`](https://github.com/ProDataMan/CAREN-Act/issues?q=label%3Aresidual-law) | Check the citation in the current official code, then swap `needs-verification` for `verified`. Move it to `repeal-requested` → `repeal-introduced` → `repealed` as it progresses, or use `not-residual` if it's already gone. |
| Welcome a volunteer | GitHub sign-ups: [issues labeled `volunteer`](https://github.com/ProDataMan/CAREN-Act/issues?q=label%3Avolunteer). Private sign-ups: `/website/admin.html` | Add the `volunteer-active` label, or set status **active** on the admin page, then assign them to reports in their state. |
| Add a contested-death case | [Issues labeled `contested-death`](https://github.com/ProDataMan/CAREN-Act/issues?q=label%3Acontested-death) | Verify the sources, then add an entry to `website/data/contested_deaths.json` in the same format and push. |
| Add CDC WONDER exports | [Issues labeled `cdc-wonder`](https://github.com/ProDataMan/CAREN-Act/issues?q=label%3Acdc-wonder) | Save the attached `.txt` files to `website/data/cdc_wonder/`, then run `python3 scripts/build_data.py wonder` (or wait for the Monday refresh) and push. |
| Refresh map data now | Actions → **Refresh map data** → **Run workflow** | Runs automatically every Monday. |

### Step 8. Outreach

Send the letters to JULIAN (Jill Collen Jefferson) and the Legal Defense Fund (shared with you privately, not stored in this public repo) through their website contact forms. Then point new volunteers to https://prodataman.github.io/CAREN-Act/website/volunteer.html.

### Step 9. January 3, 2027: switch to the 120th Congress

Several states redrew their districts. When the new Congress is seated:

1. In `scripts/build_data.py`, change `zcta_cd` to the Census `tab20_cd12020_zcta520_natl.txt` file once it's published, then rebuild the data.
2. In `website/assets/reps.js`, change the geocoder lookup to look for `/120th Congressional/` and use `vintage=Current_Current`.

Member names and contact details update on their own from `congress-legislators`.

### Later: the AI letter helper and automatic bill watcher (optional)

These need keys you don't have yet. Everything else on the Take action page already works without them.

- **AI letter helper** (turns a visitor's few sentences into a polished personal letter they review and send). This needs an Anthropic API key from https://console.anthropic.com. It is billed separately from a Claude Pro subscription. With the Claude Haiku 5.5 model, a letter costs about $0.001, so 1,000 letters is roughly $1. Set a monthly spend limit (for example $10) in the Console under Billing → Limits so it can never cost more. Tell Claude when you have the key, and it will add the endpoint to the Azure server with per-visitor rate limits.
- **State legislator names in the lookup and the bill watcher** (weekly search for CAREN-style bills in every state). These need a free Open States API key from https://open.pluralpolicy.com/accounts/profile/. Until then, the lookup shows each visitor's exact state districts and links to Open States to find the names.

### Costs

- **Container App:** scales to zero when idle and should stay within Azure's monthly free grant at campaign traffic. It also uses a small Log Analytics workspace for logs.
- **Database:** on Azure SQL's free offer (100,000 vCore-seconds and 32 GB a month). It pauses if that's used up, so there are no overage charges.
- **GitHub Pages and public container images:** free.

## Azure deployment (site + API + database)

The same site also runs on Azure with a small API and a private database. It uses the same deployment process and Azure account as Ohana_Belltown.

- **URL:** https://caren-act-server.calmpebble-c668572f.centralus.azurecontainerapps.io/website/
- **Admin (volunteer list):** `/website/admin.html` (sign in with Google or Facebook using an email in `ADMIN_EMAILS`)
- **App:** Azure Container App `caren-act-server` in resource group `CARENAct` (Central US), environment `caren-act-env`, scales to zero when idle
- **Database:** `CAREN_Act` on the existing Azure SQL server `postgresdata.database.windows.net` (resource group `Ohana`), free serverless tier that pauses when idle. The app signs in with its **managed identity**, so there is no database password.
- **Deploy:** `.github/workflows/deploy-server.yml` builds `server/Dockerfile`, pushes `ghcr.io/prodataman/caren-act-server:<sha>`, then runs `az containerapp update` through OIDC with the same `ohana-belltown-github-deploy` app registration. It runs on every push to `main` that touches `server/`, `website/` or `docs/`.
- **One-time setup:** see [Owner's to-do list](#owners-to-do-list-step-by-step), steps 1–6.

### Server (`server/`)

Node.js + Express with the `mssql` driver. Vapor, the Swift framework Ohana uses, has no maintained SQL Server driver. The server:

- serves `website/` and `docs/`;
- `GET /api/health`: reports database and sign-in status;
- `POST /api/volunteers`: private volunteer sign-up (rate-limited, honeypot). It is also callable from the GitHub Pages copy via CORS;
- sessions: a cookie on the Azure site, or an `Authorization: Bearer` token on GitHub Pages. After sign-in, the token is handed back in the URL fragment, and only to origins listed in `CORS_ORIGINS`;
- `GET /api/volunteers/coverage`: public counts by state only;
- `GET /api/admin/volunteers`, `PATCH /api/admin/volunteers/:id`: admin only;
- `/auth/google`, `/auth/facebook`: sign-in, enabled only when `GOOGLE_OAUTH_CLIENT_ID`/`GOOGLE_OAUTH_CLIENT_SECRET` or `FACEBOOK_OAUTH_APP_ID`/`FACEBOOK_OAUTH_APP_SECRET` are set. These are the same variable names Ohana uses. Use new OAuth clients branded for this campaign. Redirect URIs: `<base>/auth/google/callback` and `<base>/auth/facebook/callback`.

Tables are created automatically from `server/src/migrations/*.sql` on first start. Run it locally with `cd server && npm install && DB_SERVER=postgresdata.database.windows.net DB_NAME=CAREN_Act npm start`; your `az login` must be allowed through the SQL firewall.

Container app settings: `DB_SERVER`, `DB_NAME`, `PUBLIC_BASE_URL`, `CORS_ORIGINS`, `ADMIN_EMAILS`, `NODE_ENV`, `PORT`, plus the optional OAuth keys. GitHub Pages deploys from the `main` branch, repository root.

## About the Original Ordinance

The San Francisco ordinance (Police Code §637, Ordinance No. 219-20, File No. 200735) makes it unlawful to knowingly cause a peace officer to contact a person with the specific intent to discriminate on the basis of protected characteristics (race, color, ancestry, ethnicity, national origin, place of birth, sex, age, religion, creed, disability, sexual orientation, gender identity, weight, or height). It creates a civil cause of action for damages: a minimum of $1,000 plus fees, with possible punitive damages.

Supervisor Shamann Walton introduced it in July 2020. It followed the June 2020 Pacific Heights incident, in which a couple called police on a Filipino American man chalking "Black Lives Matter" on his own home, and the May 2020 Central Park call by Amy Cooper about Black birdwatcher Christian Cooper. The Board passed it 11–0 on October 27, 2020. See the [history page](https://prodataman.github.io/CAREN-Act/website/history.html) for details and sources.

## Contents

- `docs/SF-CAREN-Act.pdf`: original San Francisco ordinance, with legislative history on the last page
- `website/index.html`: advocacy map built on live public data, plus the lawmaker lookup
- `website/act.html`: Take action hub: lawmaker lookup, county sharing, voter registration, know-your-rights links, embed code
- `website/county.html`: one county's numbers (`?f=<FIPS>`) with a downloadable or shareable 1080×1080 image
- `website/embed.html`: compact lawmaker lookup for partner sites to embed in an iframe
- `website/assets/reps.js`: shared lookup used by the three pages above. Census Geocoder → congressional, state legislative and local districts; members from congress-legislators; a call script and click-to-call for each member; letters to Congress, state lawmakers and the city council or county board, rewritten live around the visitor's own story
- `website/bill.html` + `website/bill.json`: draft federal bill (text lives in `bill.json`) with public, per-paragraph comments
- `website/history.html`: origin story of the SF CAREN Act
- `website/deaths.html`: disputed hanging deaths (curated in `website/data/contested_deaths.json`) and CDC charts of hanging/unnatural deaths by race
- `website/laws.html`: tracker for residual Jim Crow / sundown laws, from report → verification → drafted repeal ordinance or bill → delivery → follow-up
- `website/assets/site.css`, `website/assets/site.js`: shared header, mobile menu, and footer used by every page
- `website/volunteer.html`: state ally recruitment, with a private sign-up form (Azure API) or a public GitHub sign-up, and a coverage grid
- `website/admin.html`: volunteer list for admins (works on both copies of the site)
- `website/assets/api.js`: shared browser client for the Azure API (works out the API address and attaches the sign-in token)
- `website/privacy.html`: privacy policy (required by Google and Facebook sign-in)
- `server/`: Node.js API and static server for Azure (see "Azure deployment")
- `scripts/azure-setup.sh`, `server/sql/grant-app-identity.sql`: one-time permission setup for the Azure deployment
- `website/data/cdc_wonder/`: drop hand-exported CDC WONDER `.txt` files here; the build turns them into `cdc_wonder_states.json`
- `.github/ISSUE_TEMPLATE/`: forms for reporting old laws and contested deaths, and for volunteering as a state ally
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

## State Allies (volunteers)

Volunteers sign up through the [volunteer form](https://github.com/ProDataMan/CAREN-Act/issues/new?template=volunteer.yml) (label `volunteer`). Editors add `volunteer-active` and assign them to reports in their state. Roles:

- law verifier
- case verifier
- CDC data exporter
- local deliverer
- legal reviewer
- researcher

Sign-ups are public, so the form asks for no contact details. Planned: Google/Facebook sign-in, which needs a hosted auth backend such as Supabase Auth or Firebase Auth, plus private volunteer records.

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
- Census ACS 5-year B03002 for every 119th-Congress district and state legislative district (`districts.json`, shown on lawmaker cards)
- "Suspicious person" 911 calls and their outcomes, past 12 months, from the San Francisco, Seattle and New Orleans open-data portals (`city_calls.json`). To add a city, append an entry to `CITY_CALLS`.
- Monroe Work Today lynchings of all races (`lynchings_all_races.json`, CC BY-NC 4.0 with attribution)
- Mapping Prejudice racial covenants from 13 counties, grouped into ~250 m cells (`covenants.json`)
- BJS Police-Public Contact Survey 2020: force and street-stop outcomes by race (`bjs_contacts.json`)

Rebuild a single source with `python3 scripts/build_data.py calls` (also `covenants`, `mwt`, `bjs`, `acs`, `cdc`, `wonder`). If one of the newer sources fails during the weekly refresh, last week's file stays in place.

Still not added: LegiScan, Congress.gov and Police Scorecard (need API keys), Stanford Open Policing (multi-GB files), the Sundown Towns database (needs permission), ADL H.E.A.T. and civil-rights report cards (need a volunteer export or a partnership). See the status column on the data page.

CDC WONDER (state and county numbers by race) blocks automated access, so those have to be exported by hand. Contested deaths are curated from reputable reporting and verified before they are added.

Members of Congress and committee rosters load live from [@unitedstates/congress-legislators](https://github.com/unitedstates/congress-legislators). Address-to-district lookups go through the Census Geocoder. See [data.html](https://prodataman.github.io/CAREN-Act/website/data.html) for methodology and recommended additional sources.

## Goal

Make similar protections against discriminatory emergency calls available nationwide through federal legislation, so the practice is illegal in every city in every state.

## Disclaimer

Map layers use publicly available historical and statistical data for educational and advocacy purposes. They illustrate patterns from sources such as the Equal Justice Initiative (lynchings 1877–1950), FBI Uniform Crime Reporting (hate crimes), Mapping Inequality / HOLC (redlining), Mapping Police Violence, and historical research on sundown towns (e.g., James Loewen). The priority-score weights are an advocacy judgment, documented on the methodology page. Formal sundown ordinances have been repealed. Claims of current operational "sundown laws" or active Jim Crow statutes require specific verification, as most have been struck down or repealed. Always verify with primary sources.

## Getting Involved

See the [website](https://prodataman.github.io/CAREN-Act/website/) for ways to support, contact representatives, and comment on the bill. Target members of Congress (especially House/Senate Judiciary) for sponsorship.
