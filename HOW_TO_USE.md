# ADMC Report Agent — How to Use

## One-time setup: connect Asana

The simplest, most reliable way to add your Asana token:

1. Get your token from https://app.asana.com/0/my-apps → **Create new token** → copy it.
2. In the `admc_report_agent` folder, create a plain text file named **`asana_token.txt`**.
3. Paste **only the token** into that file (nothing else) and save.

That's it. The app reads the token from this file automatically — no .env, no
Settings panel, no encoding problems.

> You can still use the Settings panel in the app if you prefer; both work.

## One-time setup: add logos

Put your logo image files here (PNG or JPG):

- **Client logos:** `admc_report_agent/Inputs/logos/Clients/`
  (filename should contain the client name, e.g. `Denodo.png`)
- **Active DMC logo:** `admc_report_agent/Inputs/logos/active_dmc/`
  (any image file, or name it `logo.png`)

Logos are scaled to keep their correct proportions (no stretching).

## Run the app

From the folder that contains `Start_ADMC_Agent.bat`:

1. Double-click **`Start_ADMC_Agent.bat`** (it pulls the latest code, then starts).
2. Open **http://localhost:5000** in your browser.
3. Upload your tracker, pick the client and period, click **Generate**.

## If deliverables are still empty

The **Deliverables Overview** slide now tells you exactly why, e.g.:

- *"No Asana token configured"* → create `asana_token.txt` (see above).
- *"Could not load deliverables from Asana: 401 …"* → the token is invalid or
  expired; create a new one.
- *"No deliverables found for 'X' in the period …"* → Asana connected fine but
  no tasks matched the client name + date range. Check the project name contains
  the client name, and the dates cover the tasks.

The console window also prints a full `[Asana] …` trace each time you generate.

## How counting works

- Each **top-level Asana task** = one deliverable (press release, interview,
  commentary, byline, etc.).
- **Subtasks are ignored** — they are internal steps (draft, translate, approve,
  publish) and are not counted, so totals are accurate.
- Sections and milestones are skipped.
