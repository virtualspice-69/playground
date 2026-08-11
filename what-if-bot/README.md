# $IF Guy — Telegram Bot

Community meme/art bot for **What If ($IF)**. Two art paths, both effectively
free to run:

1. **Library mode** (`/meme`, `/random`, `/gif`) — serves pieces you (or the
   community) already made, from `assets/templates/`. Zero cost, instant.
2. **AI generation** (`/art`, `/variations`) — generates new on-brand art on
   demand via [Pollinations.ai](https://pollinations.ai), which is free and
   requires no API key.

Price data (`/price`, `/chart`) comes from the free [DexScreener](https://dexscreener.com)
API, looked up by your token's contract address — it works regardless of
which chain or exchange has the deepest liquidity, so you don't need to
hardcode a specific DEX.

## Commands

| Command | What it does |
|---|---|
| `/start`, `/help` | Overview + quick links |
| `/price`, `/chart` | Live price, 24h change, liquidity, market cap |
| `/meme top text \| bottom text` | Classic meme text on a random template (or reply to a photo with `/meme ...` to use that image) |
| `/variations` | Buttons to generate the $IF Guy in a preset scene (moon, boxing ring, cosmic flight, etc.) |
| `/art a rocket made of gold` | Freeform AI art — mascot description + your prompt |
| `/random` | Random piece from the community art library |
| `/gif` | Random animation from the library |
| `/buy`, `/links` | Buy links / socials |

## Setup

1. **Create the bot**: message [@BotFather](https://t.me/BotFather) on
   Telegram, `/newbot`, copy the token it gives you.
2. **Configure**:
   ```bash
   cp .env.example .env
   ```
   Fill in `BOT_TOKEN` and `TOKEN_CONTRACT_ADDRESS` at minimum. Add
   `WEBSITE_URL` / `TWITTER_URL` / `TELEGRAM_GROUP_URL` / `UNISWAP_BUY_URL` /
   `BLOFIN_URL` for the link buttons.
3. **Add art** (optional but recommended): drop your existing meme templates
   into `assets/templates/memes/` and finished pieces/animations into
   `assets/templates/gallery/`. See the READMEs in those folders. Run:
   ```bash
   python scripts/build_manifest.py
   ```
   to check what got indexed (the bot also auto-detects new files at
   startup/runtime).
4. **Run locally**:
   ```bash
   pip install -r requirements.txt
   python bot.py
   ```
5. **Try it**: message your bot on Telegram, send `/start`.

## Deploying so it stays online

Pick one:

- **Railway / Render** (easiest): connect this repo, set the `.env` values
  as environment variables in their dashboard, deploy. They'll run
  `python bot.py` (or use the included `Dockerfile`) and keep it alive.
- **A VPS**: `docker build -t if-bot . && docker run -d --restart unless-stopped --env-file .env if-bot`
- **Your own machine**: fine for testing, but the bot only responds while
  `python bot.py` is running.

## Tuning the mascot's look

`CHARACTER_PROMPT` in `.env` (or `config.py`'s default) describes the $IF
Guy mascot so every AI generation stays visually consistent. If you want a
different look, edit that description — e.g. add "wearing sunglasses" or
swap "anime illustration style" for "photorealistic digital painting" — and
re-test with `/variations`.

`PRESET_SCENES` in `services/image_gen.py` is the list of scenes behind
`/variations`. Add/remove entries there as the community's favorite bits
(moon landing, boxing ring, etc.) evolve.

## Cost

- Library commands (`/meme`, `/random`, `/gif`): **$0**, no external calls.
- `/price`, `/chart`: **$0**, DexScreener's public API is free.
- `/art`, `/variations`: **$0** by default via Pollinations.ai's free tier.
  It's rate-limited and quality/consistency can vary run to run — that's
  the tradeoff for zero cost. If you outgrow it, swap `IMAGE_GEN_PROVIDER`
  in `services/image_gen.py` for a paid provider (Replicate/Together SDXL
  is a fraction of a cent per image) once you have a budget and API key.
- `COMMAND_COOLDOWN_SECONDS` in `.env` throttles per-user AI requests so a
  few enthusiastic users can't burn through rate limits for everyone else.
