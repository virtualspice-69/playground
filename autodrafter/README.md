# eBay Auto-Drafter

Turn a folder of item photos into ready-to-review eBay draft listings using Claude vision.

You take the photos; this tool writes the title, condition, category, item specifics, description, flaw list, and a suggested price range for every item. You review, publish on eBay, and crosslist with Flyp.

## Setup (one time)

1. Install [Node.js](https://nodejs.org) 18 or newer.
2. In this folder, run:
   ```sh
   npm install
   ```
3. Get a Claude API key at <https://platform.claude.com> and set it:
   ```sh
   export ANTHROPIC_API_KEY=sk-ant-...
   ```

## Put it on the web (Render)

This gets you a real `https://` address you can open from any phone, and lets sign-ups and Google connect work from anywhere. All in a browser — no computer needed.

1. Go to <https://render.com> and sign up (free) — you can sign in with GitHub.
2. Click **New +** → **Blueprint**.
3. Connect your GitHub and pick the **playground** repo, branch `claude/ebay-listing-automation-vog6mt`. Render reads `render.yaml` and sets up the web service automatically.
4. Click **Apply**. When it asks for environment variables, paste your **ANTHROPIC_API_KEY** (from <https://platform.claude.com>). Leave the Google keys blank for now.
5. Wait a couple minutes for the first deploy. Render gives you a URL like `https://ebay-autodrafter.onrender.com` — that's your app. Open it on your Pixel.

**To make the Google Photos/Drive buttons work on the live site:** in the Google Cloud console (see next section), add your Render URL as an authorized redirect URI — `https://YOUR-APP.onrender.com/auth/google/callback` — then paste `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` into Render's Environment settings.

> **Free-tier note:** the free plan sleeps after ~15 minutes idle and its storage resets on sleep/redeploy — great for playing and fine-tuning, but accounts and drafts won't stick around long-term yet. Making the data permanent (a small database) is the recommended next step once you've had a play.

## Accounts

The web app opens to a sign-up / sign-in screen, like a real auto-lister:

- **Create account** with email + password (min 8 chars) and a quick human-check captcha.
- **Confirm your email** — a confirmation link is generated. With no email service configured, the link is shown on screen and printed to the server console; click it to activate the account. (Disposable/throwaway email domains are blocked, and you can't sign in until confirmed.)
- **Sign in** with "Keep me signed in" for auto-login next time.

Accounts and drafts are stored locally in the `data/` and `drafts/` folders (never committed). Passwords are hashed with scrypt; sessions use signed cookies.

> **Sending real confirmation emails** (needed if others will sign up): plug an email provider into `sendConfirmationEmail` in `src/auth.js` — e.g. add `nodemailer` and your SMTP credentials. Until then, the on-screen link works for you and anyone you set up by hand.

## Connect Google Photos & Drive

The first screen has **Google Photos** and **Google Drive** buttons so you can pull item photos straight from your Google account. This needs a free Google Cloud OAuth app — only you can create it:

1. Go to <https://console.cloud.google.com>, create a project.
2. **APIs & Services → Enable APIs**: enable **Google Photos Library API** and **Google Drive API**.
3. **OAuth consent screen**: set it up (External), add yourself as a test user.
4. **Credentials → Create OAuth client ID → Web application**. Under *Authorized redirect URIs* add:
   `http://localhost:3000/auth/google/callback` (match your port).
5. Copy the **Client ID** and **Client secret** and start the server with them:
   ```sh
   GOOGLE_CLIENT_ID=xxx GOOGLE_CLIENT_SECRET=yyy ANTHROPIC_API_KEY=sk-ant-... npm run serve
   ```

Now the buttons connect; tap one to pick recent photos and import them into a draft.

> Google's OAuth requires `localhost` or an `https://` domain for the redirect — so **Google connect works from the desktop browser at `localhost`**, or from your phone once the app is deployed on a real `https://` domain. Over a plain `http://192.168.x.x` LAN address Google will refuse the redirect (this is Google's rule, not the app's). Photos added directly from the phone camera work over LAN regardless.

## Use it from your phone (web app)

Start the web app on any computer at home:

```sh
npm run serve
```

It prints two addresses:

- **This computer:** `http://localhost:3000` — open in any desktop browser
- **Phone (same Wi-Fi):** `http://192.168.x.x:3000` — open in Brave/Chrome on your phone

On the phone: type the item name, tap **Add photos** (opens the camera or gallery), tap **Create draft**. Photos are downscaled in the browser before upload, drafts are saved on the computer, and the **Download CSV** link gives you the review spreadsheet.

To try the UI without an API key: `npm run serve:mock`.

> The server has no login — only run it on your home Wi-Fi, don't expose the port to the internet.

## Daily workflow (CLI, batch mode)

1. Make one folder per item and drop that item's photos in it. Name the folder what you'd call the item — the name is given to the AI as a hint:

   ```
   photos/
     nike hoodie XL/
       front.jpg
       back.jpg
       tag.jpg
     levis 501 jeans 34x32/
       front.jpg
       tag.jpg
   ```

2. Run the drafter:

   ```sh
   node src/cli.js photos
   ```

3. Open `drafts/drafts.csv` (Excel/Google Sheets) to review everything at once, or the per-item `.json` files. Each draft includes a **"Verify Before Publishing"** column listing anything the AI wasn't sure about — check those before listing.

4. Create the listings in eBay, then crosslist via Flyp as usual.

## Options

| Flag | Default | What it does |
|---|---|---|
| `--out <dir>` | `drafts` | Where to write the JSON + CSV output |
| `--max-photos <n>` | `8` | Max photos sent to the AI per item (more photos = better drafts but higher cost) |
| `--mock` | off | Test the pipeline without an API key or cost |

Environment variables: `AUTODRAFT_MODEL` overrides the model (default `claude-opus-4-8`).

## What each draft contains

- **Title** — max 80 characters, search-term optimized
- **Condition** — eBay condition grade, judged from the photos (graded conservatively)
- **Category** — suggested eBay category path
- **Item specifics** — brand, size, color, material, etc. as visible in the photos
- **Description** — honest buyer-facing text including all visible flaws
- **Price** — suggested price plus a low/high range
- **Verify Before Publishing** — things the AI couldn't confirm from the photos

The AI is instructed to never invent details it can't see (sizes, model numbers, materials) — anything uncertain lands in the verify column instead.

## Cost

Each item costs roughly 1–3 cents in API usage with 3–8 photos (Claude Opus 4.8 pricing). Drafting 150 listings/week lands around $2–5/week.

## Roadmap

- [ ] Push drafts directly to eBay as draft listings via the eBay Sell API (needs an eBay developer account)
- [ ] Watch folder mode: auto-draft as soon as photos land in the folder
- [ ] Mobile companion (photos on phone → drafts on desktop) — see `../BUSINESS_NOTES.md`
