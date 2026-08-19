# The Twelfth Man

**30 Years of European Football: More Goals, Fewer Draws — and What Changed in the VAR Era?**

A data visualization project for the Data Visualization course (תשפ״ו), analyzing how European
football changed across the "big 5" leagues — Premier League, La Liga, Bundesliga, Serie A, and
Ligue 1 — from 1993/94 to 2025/26.

The project focuses on two main dimensions of change:

- **How the game itself changed** — draw rate, goals per match, and attacking efficiency over time.
- **How refereeing patterns changed in the VAR era** — using cards per foul as a normalized measure
  and comparing each league before and after VAR was introduced.

A supporting story also looks at **home-field advantage** and the COVID-19 period, when many matches
were played without crowds, as additional context for understanding changes in the match environment.

## Research questions

The main question is:

> **How has European football changed over the last three decades in terms of match outcomes,
> attacking trends, and refereeing patterns in the VAR era?**

Supporting questions include:

- Has the draw rate declined over time across the five leagues?
- Has the average number of goals per match increased?
- Is the increase in goals associated with changes in shot volume or finishing efficiency?
- Did the cards-per-foul ratio change after VAR was introduced?
- Are the observed patterns consistent across leagues?
- As a supporting question, how did home advantage change over time, and what happened during the
  COVID-19 season?

## Data

Source: [`github.com/datasets/football-datasets`](https://github.com/datasets/football-datasets)
(built from football-data.co.uk).

After preprocessing, the project contains:

- **59,079 matches**
- **5 leagues**
- **33 seasons**
- **1993/94–2025/26**

The raw data includes match results and, where available, detailed statistics such as shots,
shots on target, fouls, and yellow/red cards.

Because detailed shot/card data is incomplete in some early seasons, analyses based on those fields
use the common period in which the required variables are consistently available.

## Preprocessing

Data preparation was performed in **Python / pandas** in **Google Colab**.

The preprocessing pipeline:

- merges the season files for all five leagues;
- adds `League`, `Season`, and `SeasonStartYear` fields;
- cleans and type-casts dates and numeric columns;
- checks missing values in the core match fields;
- creates derived fields such as `TotalGoals`, `GoalDiff`, `HomeWin`, `AwayWin`, and `Draw`;
- calculates shot-accuracy and shot-conversion metrics;
- aggregates data at league-season level;
- calculates home-advantage measures;
- adds the actual VAR introduction season for each league;
- creates `Pre-VAR` / `Post-VAR` periods;
- calculates `CardsPerFoul` using total yellow + red cards divided by total fouls;
- generates analysis-ready CSV files and a processing log.

VAR introduction seasons used in the analysis:

| League | VAR introduced |
|---|---|
| Bundesliga | 2017/18 |
| Serie A | 2017/18 |
| La Liga | 2018/19 |
| Ligue 1 | 2018/19 |
| Premier League | 2019/20 |

## Project structure

- `notebook/` — Python/pandas preprocessing notebook used in Google Colab.
- `data/processed/` — analysis-ready CSV files used by Tableau, plus `PROCESSING_LOG.txt`.
- `docs/` — supporting documentation and Tableau build notes.
- `report/` — project report submitted according to the course requirements.

## Tableau visualizations

The project is built in Tableau and contains **two dashboards plus a story**.

### Dashboard 1 — 30 Years of Change: Goals & Draws

Examines how match outcomes and attacking patterns changed over time.

Main views include:

- draw rate by season;
- average goals per match;
- attacking / finishing efficiency;
- league-level filtering and interactive tooltips.

The purpose of this dashboard is to answer **what changed in the game itself**, and then use
attacking-efficiency measures to explore part of the "why" behind the trend.

### Dashboard 2 — Before vs. After VAR: Refereeing Patterns

Examines whether refereeing patterns changed after VAR was introduced in each league.

The main measure is:

`CardsPerFoul = (Yellow Cards + Red Cards) / Total Fouls`

This normalization helps distinguish a change in sanctioning intensity from a simple change in the
number of fouls committed.

Supporting views include fouls per match and the VAR introduction timeline. Linked highlighting is
used to follow the same league across multiple views.

> The analysis is observational. A before/after difference is treated as an association with the VAR
> era, not as proof that VAR alone caused the change.

### Story — How 30 Years Changed European Football

The story connects the dashboards into one narrative:

1. How match outcomes changed over three decades.
2. What changed in attacking efficiency.
3. What changed around the introduction of VAR.
4. How home advantage evolved as a supporting theme.
5. What happened to home advantage during the COVID-19 period with reduced or absent crowds.

COVID is therefore used as **supporting context for the home-advantage / crowd-effect analysis**, not
as the central explanation for the VAR or attacking findings.

## Tableau Public

- **Story / main project:** https://public.tableau.com/views/European_Football_30_Years_Project/Story1
- **Additional published view:** https://public.tableau.com/shared/6NJ55Y5GN
- **VAR dashboard:** https://public.tableau.com/views/Viz2VARDashBoard2/Dashboard3

## Tools

- Python 3
- pandas
- Google Colab
- Tableau Desktop
- Tableau Public

## Team

Yousef Shihade · Shada Essawi · Fidaa Arrabi  
Data Visualization — Final Project, תשפ״ו
