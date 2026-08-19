# The Twelfth Player ⚽

**Testing football's oldest cliché — is the crowd really an extra player?**

A data visualization project for the Data Visualization course , analyzing home-field
advantage across Europe's "big 5" football leagues (Premier League, La Liga, Bundesliga, Serie A,
Ligue 1) from 1993/94 to 2025/26 and using COVID-19's fanless, behind-closed-doors matches as
a natural experiment to test how much of that advantage actually comes from the crowd.

## The question 🏟️

Home-field advantage is one of the most consistent patterns in sports, but *why* it exists is
debated ,crowd pressure on referees, travel fatigue, pitch familiarity. COVID accidentally
created a natural experiment: same teams, same competitions, same rules, just no fans. This
project uses that experiment to test the "it's the crowd" theory directly, across five different
football cultures.

## Data

Source: [`github.com/datasets/football-datasets`](https://github.com/datasets/football-datasets)
(built from football-data.co.uk) — match-level results for all five leagues, 1993/94–2025/26.

## Project structure

- `notebook/` — Python/pandas preprocessing (Google Colab notebook): merges all 5 leagues,
  cleans and type-casts the data, engineers home-advantage and shot-efficiency metrics, and
  produces the analysis-ready CSVs below.
- `data/processed/` — output CSVs used directly by the Tableau workbook, plus `PROCESSING_LOG.txt`
  documenting every preprocessing step.
- `docs/` — build guide mapping processed data to Tableau worksheets/dashboards/story.
- `report/` — final project report (submitted separately per course requirements).

## Visualization 🥅

Built in Tableau, two linked dashboards plus a story:

1. **"The 30-Year Decline"** — home advantage trend across all 5 leagues, 1993–2025.
2. **"Where Advantage Still Lives"** — league comparison, shot efficiency, team form, and the
   COVID-era drop in home advantage by league.
3. **Story: "It Really Was the Fans"** — narrative walkthrough from the historical trend through
   the COVID collapse to the partial post-COVID recovery.

**Live workbook:** _link to be added once published to Tableau Public_

## Team 🏆

Yousef Shihade & Shada Essawi & Fidaa Arrabi — Data Visualization, final project.
