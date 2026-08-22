# Global Seagrass News Radar

A GitHub Pages site that searches global news every day for seagrass stories, with explicit multilingual coverage.

## What it searches

### GDELT
The harvester queries GDELT DOC 2.0 for seagrass, eelgrass, marine angiosperms/phanerogams and major seagrass taxa. GDELT's translingual system allows English queries to match monitored articles published in many other languages.

### Google News RSS
The harvester also runs native-language searches across multiple Google News editions. Current routes include English, Spanish, Portuguese, French, German, Italian, Dutch, Danish, Swedish, Norwegian, Finnish, Polish, Greek, Turkish, Russian, Arabic, Hindi, Indonesian, Malay, Vietnamese, Thai, Japanese, Korean, Chinese and Swahili.

Examples include:
- Spanish: `pastos marinos`, `praderas marinas`
- French: `herbiers marins`
- German: `Seegras`, `Seegraswiesen`
- Indonesian / Malay: `lamun`, `padang lamun`
- Vietnamese: `cỏ biển`, `thảm cỏ biển`
- Thai: `หญ้าทะเล`
- Japanese: `アマモ`, `アマモ場`
- Korean: `잘피`, `잘피밭`
- Chinese: `海草床`

Latin taxonomic names are also searched because they cross language barriers.

## First deployment

1. Create a new GitHub repository, e.g. `seagrassnewsradar`.
2. Upload the **contents** of this package to the repository root.
3. Go to **Settings → Pages**.
4. Choose **Deploy from a branch**.
5. Choose branch `main`, folder `/docs`, and save.
6. Go to **Actions → Daily Global Seagrass News Radar**.
7. Click **Run workflow** once.

No API keys are required.

The first run looks back 30 days and marks those stories as a baseline. They will not all be labelled `NEW TODAY`. Subsequent runs look back four days and only newly discovered records receive that badge.

## Daily schedule

The workflow runs at 05:42 UTC every day.

## Files

- `harvest_news.py` — multilingual harvesting, tagging and deduplication
- `.github/workflows/daily-update.yml` — daily GitHub Action
- `docs/index.html` — webpage
- `docs/app.js` — filtering/dashboard logic
- `docs/styles.css` — site design
- `docs/data/news.json` — harvested stories
- `docs/data/status.json` — source health and coverage metadata

## Caveats

No news system indexes every media outlet. Local outlets can be missed, paywalls can block full article access, language metadata can be imperfect, and Google News RSS is an aggregation route rather than a publisher database. The multi-source approach is intended to reduce those gaps rather than claim universal coverage.
