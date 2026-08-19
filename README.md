# The Modern Game ⚽

**More goals, fewer draws — and what changed in the VAR era? A 30-year look at European football.**

A data visualization project for the Data Visualization course, analyzing 30 years of match
data across Europe's "big 5" football leagues (Premier League, La Liga, Bundesliga, Serie A,
Ligue 1), 1993/94–2025/26 — 59,079 matches after cleaning, across 33 seasons.

## The question 🥅

"The modern game is more attacking," "there are fewer draws than there used to be," "VAR
changed refereeing" — all common claims in football media, usually backed by feeling and
memory rather than data. This project tests them against three decades of real match results,
focusing on two main aspects: how match outcomes and attacking play have shifted over time, and
whether officiating patterns changed measurably after VAR's introduction. A complementary chapter
in the Story also revisits how home-field advantage moved over the same period, including its
sharpest single drop during COVID-19's fanless matches.

## Data

Source: [`github.com/datasets/football-datasets`](https://github.com/datasets/football-datasets)
(built from football-data.co.uk) — match-level results for all five leagues, 1993/94–2025/26.
165 raw season files merged into one dataset; detailed shot/card statistics are available
consistently across all 5 leagues from the 2005/06 season onward.

## Project structure

- `notebook/` — Python/pandas preprocessing (Google Colab notebook): merges all 5 leagues,
  cleans and type-casts the data, engineers attacking, disciplinary, and home-advantage metrics,
  and produces the analysis-ready CSVs below.
- `data/processed/` — output CSVs used directly by the Tableau workbook, plus `PROCESSING_LOG.txt`
  documenting every preprocessing step and design decision.
- `docs/` — build guide mapping processed data to Tableau worksheets, dashboards, and the story.
- `report/` — final project report, including Tableau screenshots (submitted separately per
  course requirements).

## Visualization 🏟️

Built in Tableau — two linked dashboards plus a story:

1. **Dashboard 1 — "30 Years of Change: Goals & Draws"**: draw rate and goals per match, season
   by season across all 33 seasons and 5 leagues — no smoothing into multi-year buckets, so real
   in-period swings stay visible. A supporting chart on attacking efficiency (goals per shot)
   digs into *why* scoring is rising. Finding: draw rate fell from ~28.5% to ~25.4%, while goals
   per match rose from ~2.62 to ~2.81, over the full period.
2. **Dashboard 2 — "Before vs. After VAR: Refereeing Patterns"**: cards issued per foul
   committed, compared before and after each league's real VAR introduction date (Bundesliga/
   Serie A 2017/18, La Liga/Ligue 1 2018/19, Premier League 2019/20). Finding: all 5 leagues
   show an increase, ranging from ~6% to ~45% depending on the league.
3. **Story — "How 30 Years Changed European Football"**: six steps connecting both dashboards
   — the big question, the goals/draws trend, what changed in attack, entering the VAR era —
   then a complementary chapter on the decline of home-field advantage and its collapse during
   COVID's fanless matches.

**Live workbook:** _link to be added once published to Tableau Public_

## Team 🏆

Yousef Shihade & Shada Esawi & Fidaa Arrabi — Data Visualization, final project.
