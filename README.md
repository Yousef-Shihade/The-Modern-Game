# The Modern Game ⚽

**Has European football become a more decisive game over 30 years — and how much of that shift can actually be explained, rather than just felt?**

A data visualization project for the Data Visualization course, analyzing 30 years of match
data across Europe's "big 5" football leagues (Premier League, La Liga, Bundesliga, Serie A,
Ligue 1), 1993/94–2025/26 — 59,079 matches after cleaning, across 33 seasons.

## The question 🥅

"The game is more attacking now" and "VAR killed the game's spontaneity" are two claims heard
constantly in football media — usually backed by feeling, not data. This project tests both
against three decades of real match results. The core trend: is the draw rate falling and goals
per match rising, consistently, across all 5 leagues? And rather than stopping at "the game
changed," the project uses two natural experiments already sitting in the data to test *why*:
VAR's staggered rollout by league (did officiating get measurably more consistent once it
arrived?), and COVID-19's fanless matches (a supporting look at how home-field advantage moved
over the same 30 years). Both are treated as evidence toward the main question, not separate
headline findings.

## Data

Source: [`github.com/datasets/football-datasets`](https://github.com/datasets/football-datasets)
(built from football-data.co.uk) — match-level results for all five leagues, 1993/94–2025/26.
165 raw season files merged into one dataset; detailed shot/card statistics are available from
the 2005/06 season onward league-wide.

## Project structure

- `notebook/` — Python/pandas preprocessing (Google Colab notebook): merges all 5 leagues,
  cleans and type-casts the data, engineers attacking, disciplinary, and home-advantage metrics,
  and produces the analysis-ready CSVs below.
- `data/processed/` — output CSVs used directly by the Tableau workbook, plus `PROCESSING_LOG.txt`
  documenting every preprocessing step and design decision.
- `docs/` — build guide mapping processed data to Tableau worksheets, dashboards, and the story.
- `report/` — final project report (submitted separately per course requirements).

## Visualization 🏟️

Built in Tableau — two linked dashboards plus a story:

1. **Dashboard A — "The Attacking Evolution"** (the headline): draw rate and goals per match,
   season by season across all 33 seasons and 5 leagues — no smoothing into multi-year buckets,
   so real in-period swings (like COVID's temporary dip) stay visible. A shot-efficiency
   drill-down answers *why* goals are rising: more shots, better finishing, or both.
2. **Dashboard B — "The VAR Effect"** (one explanatory mechanism): cards issued per foul
   committed, before vs. after each league's real VAR introduction date, testing whether
   technology is part of why officiating — and by extension the game — became more decisive.
3. **Story — "How 30 Years Changed Football"**: ties the attacking trend to VAR as one
   explanation, with a supporting chapter on the parallel decline of home-field advantage,
   including its sharpest single drop during COVID's fanless matches.

**Live workbook:** _link to be added once published to Tableau Public_

## Team 🏆

Yousef Shihade & Shada Esawi & Fidaa Arrabi — Data Visualization, final project.
