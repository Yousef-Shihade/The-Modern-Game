"""
30 Years of European Football — Data Preprocessing Pipeline
===========================================================

Builds the analysis-ready tables behind the Tableau dashboards and story for the
Data Visualization final project.

The pipeline merges raw season files for Europe's "big five" leagues (Premier
League, La Liga, Bundesliga, Serie A, Ligue 1) covering 1993/94-2025/26, cleans
and type-casts them, engineers the match-, season- and team-level features used
by the visualizations, and writes one CSV per analysis table plus a full
processing log.

Data source
-----------
https://github.com/datasets/football-datasets (built from football-data.co.uk)

Usage
-----
    python football_preprocessing.py
    python football_preprocessing.py --data-dir ./football-datasets --out-dir ./processed_data

By default the raw dataset repository is cloned automatically into ``./raw_data``
if it is not already present.

Outputs
-------
Tables consumed directly by the Tableau workbook:
    season_league_summary.csv    Dashboard 1 + story (draw rate, goals, home advantage)
    match_level_detailed.csv     Dashboard 1 (shot efficiency drill-down)
    var_technology_effect.csv    Dashboard 2 (cards per foul, pre vs post VAR)
    covid_league_comparison.csv  Story (home advantage during closed-doors season)
    var_home_bias_footnote.csv   Story (secondary cross-check: home/away card gap)

Supplementary tables (produced for completeness and reproducibility):
    match_level_full.csv, team_season_summary.csv, referee_summary.csv,
    attacking_evolution_summary.csv

Also written:
    PROCESSING_LOG.txt           Full step-by-step log and data-quality summary
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATASET_REPO_URL = "https://github.com/datasets/football-datasets.git"

#: Folder name in the source repository -> display name used across the project.
LEAGUES: dict[str, str] = {
    "premier-league": "Premier League (England)",
    "la-liga": "La Liga (Spain)",
    "bundesliga": "Bundesliga (Germany)",
    "serie-a": "Serie A (Italy)",
    "ligue-1": "Ligue 1 (France)",
}

#: Season in which VAR became active in each league. This is an external,
#: documented fact - it is NOT part of the source dataset - and is used only to
#: split matches into Pre-VAR / Post-VAR periods.
VAR_INTRODUCTION_YEAR: dict[str, int] = {
    "Bundesliga (Germany)": 2017,      # 2017/18
    "Serie A (Italy)": 2017,           # 2017/18
    "La Liga (Spain)": 2018,           # 2018/19
    "Ligue 1 (France)": 2018,          # 2018/19
    "Premier League (England)": 2019,  # 2019/20
}

#: Seasons affected by COVID-19 crowd restrictions.
COVID_SEASONS: tuple[str, ...] = ("2019/20", "2020/21")

#: Season played almost entirely behind closed doors, used as the "no crowd" case.
CLOSED_DOORS_SEASON = "2020/21"

#: Normal seasons immediately before COVID, used as the comparison baseline.
PRE_COVID_BASELINE_SEASONS: tuple[str, ...] = ("2017/18", "2018/19")

#: Five-year era buckets, used only for summary/KPI views (never for trend lines,
#: so that real season-to-season swings stay visible).
ERA_BIN_EDGES: list[int] = [1992, 1999, 2004, 2009, 2014, 2019, 2026]
ERA_LABELS: list[str] = ["1993-99", "2000-04", "2005-09", "2010-14", "2015-19", "2020-26"]

#: Columns that must be present for a match to be usable at all.
CORE_MATCH_FIELDS: list[str] = ["FTHG", "FTAG", "HomeTeam", "AwayTeam"]

#: Columns cast to numeric during cleaning (missing values are expected in the
#: earlier seasons, which is why detailed analyses are restricted to a common era).
NUMERIC_MATCH_COLUMNS: list[str] = [
    "FTHG", "FTAG", "HTHG", "HTAG",
    "HS", "AS", "HST", "AST",
    "HF", "AF", "HC", "AC",
    "HY", "AY", "HR", "AR",
]

#: Minimum matches officiated before a referee is included in the referee summary,
#: so that averages are not driven by tiny samples.
MIN_MATCHES_PER_REFEREE = 30

LOGGER = logging.getLogger("football_preprocessing")


# ---------------------------------------------------------------------------
# Season-code helpers
# ---------------------------------------------------------------------------

def season_code_to_label(code: str) -> str:
    """Convert a file's season code to a display label.

    >>> season_code_to_label("9394")
    '1993/94'
    >>> season_code_to_label("2526")
    '2025/26'
    """
    start, end = code[:2], code[2:]
    century = "19" if start >= "93" else "20"
    return f"{century}{start}/{end}"


def season_code_to_start_year(code: str) -> int:
    """Return the calendar year in which a season started.

    >>> season_code_to_start_year("0001")
    2000
    """
    start = code[:2]
    century = "19" if start >= "93" else "20"
    return int(f"{century}{start}")


def format_season(start_year: int) -> str:
    """Format a season start year as a ``YYYY/YY`` label."""
    return f"{start_year}/{str(start_year + 1)[-2:]}"


# ---------------------------------------------------------------------------
# Step 0 - acquire raw data
# ---------------------------------------------------------------------------

def _run_git(arguments: list[str], description: str) -> None:
    """Run a git command, surfacing git's own error message if it fails."""
    # core.longpaths is required on Windows: the source repository contains
    # dataset folders whose names exceed the default 260-character path limit.
    command = ["git", "-c", "core.longpaths=true", *arguments]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{description} failed:\n{result.stderr.strip()}")


def download_raw_data(target_dir: Path) -> Path:
    """Clone the public dataset repository if it is not already available.

    Only the five league folders are checked out (via a sparse checkout), which
    keeps the download small and avoids unrelated datasets in the same
    repository whose long folder names break checkout on Windows.

    Returns the path to the directory holding the per-league season folders.
    """
    datasets_dir = target_dir / "datasets"
    if datasets_dir.is_dir():
        LOGGER.info("STEP 0 - Using existing raw data at %s", datasets_dir.resolve())
        return datasets_dir

    LOGGER.info("STEP 0 - Cloning %s into %s", DATASET_REPO_URL, target_dir.resolve())
    _run_git(
        ["clone", "--depth", "1", "--filter=blob:none", "--sparse",
         DATASET_REPO_URL, str(target_dir)],
        "Cloning the dataset repository",
    )
    _run_git(
        ["-C", str(target_dir), "sparse-checkout", "set",
         *(f"datasets/{folder}" for folder in LEAGUES)],
        "Selecting the five league folders",
    )

    if not datasets_dir.is_dir():
        raise FileNotFoundError(f"Expected {datasets_dir} after cloning the dataset repository.")
    LOGGER.info("STEP 0 - Checked out %s league folders.", len(LEAGUES))
    return datasets_dir


# ---------------------------------------------------------------------------
# Step 1 - load and merge
# ---------------------------------------------------------------------------

def load_raw_matches(datasets_dir: Path) -> pd.DataFrame:
    """Merge every season file for all five leagues into a single table."""
    frames: list[pd.DataFrame] = []
    unreadable: list[tuple[str, str]] = []

    for folder, league_name in LEAGUES.items():
        season_files = sorted((datasets_dir / folder).glob("season-*.csv"))
        if not season_files:
            raise FileNotFoundError(f"No season files found for league folder {folder!r}.")

        for path in season_files:
            code = path.stem.replace("season-", "")
            try:
                season_df = pd.read_csv(path)
            except (pd.errors.ParserError, UnicodeDecodeError) as exc:
                unreadable.append((path.name, str(exc)))
                continue

            season_df["League"] = league_name
            season_df["Season"] = season_code_to_label(code)
            season_df["SeasonStartYear"] = season_code_to_start_year(code)
            frames.append(season_df)

    raw = pd.concat(frames, ignore_index=True, sort=False)
    LOGGER.info(
        "STEP 1 - Merged %s season files: %s matches across %s leagues and %s seasons (%s-%s).",
        f"{len(frames):,}", f"{len(raw):,}", raw["League"].nunique(), raw["Season"].nunique(),
        raw["SeasonStartYear"].min(), raw["SeasonStartYear"].max() + 1,
    )
    if unreadable:
        LOGGER.warning("STEP 1 - %s file(s) could not be parsed: %s", len(unreadable), unreadable)
    return raw


# ---------------------------------------------------------------------------
# Step 2 - clean and type-cast
# ---------------------------------------------------------------------------

def clean_matches(raw: pd.DataFrame) -> pd.DataFrame:
    """Parse dates, coerce numeric columns and drop rows missing core fields."""
    matches = raw.copy()

    matches["Date"] = pd.to_datetime(matches["Date"], errors="coerce", dayfirst=False)
    LOGGER.info("STEP 2 - Parsed Date column. Unparseable dates: %s", matches["Date"].isna().sum())

    for column in NUMERIC_MATCH_COLUMNS:
        matches[column] = pd.to_numeric(matches[column], errors="coerce")

    before = len(matches)
    matches = matches.dropna(subset=CORE_MATCH_FIELDS)
    LOGGER.info(
        "STEP 2 - Dropped %s row(s) missing core result/team fields. Remaining: %s",
        before - len(matches), f"{len(matches):,}",
    )

    for column in ("HomeTeam", "AwayTeam"):
        matches[column] = matches[column].astype(str).str.strip()

    return matches.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Step 3 - match-level feature engineering
# ---------------------------------------------------------------------------

def engineer_match_features(matches: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Add derived match-level fields and determine the common "detailed" era.

    Returns the enriched table and the first season start year in which every
    league reports shots, fouls and cards.
    """
    enriched = matches.copy()

    enriched["TotalGoals"] = enriched["FTHG"] + enriched["FTAG"]
    enriched["GoalDiff_HomeMinusAway"] = enriched["FTHG"] - enriched["FTAG"]
    enriched["HomeWin"] = (enriched["FTR"] == "H").astype(int)
    enriched["AwayWin"] = (enriched["FTR"] == "A").astype(int)
    enriched["Draw"] = (enriched["FTR"] == "D").astype(int)

    # Detailed statistics are absent in the earliest seasons, and the different
    # statistic families start at different times, so availability is tracked
    # per family rather than with a single blanket flag.
    enriched["HasShotStats"] = enriched[["HS", "AS", "HST", "AST"]].notna().all(axis=1)
    enriched["HasFoulStats"] = enriched[["HF", "AF"]].notna().all(axis=1)
    enriched["HasCardStats"] = enriched[["HY", "AY"]].notna().all(axis=1)

    # The "detailed era" is defined by shot availability, which is the earliest
    # point at which all five leagues report match statistics at all.
    enriched["HasDetailedStats"] = enriched["HasShotStats"]

    detailed_count = int(enriched["HasDetailedStats"].sum())
    LOGGER.info(
        "STEP 3 - Engineered match-level fields. Matches with shot statistics: %s / %s (%.1f%%).",
        f"{detailed_count:,}", f"{len(enriched):,}", detailed_count / len(enriched) * 100,
    )

    first_detailed_season = (
        enriched.loc[enriched["HasDetailedStats"]]
        .groupby("League")["SeasonStartYear"].min()
        .to_dict()
    )
    LOGGER.info("STEP 3 - First season with shot statistics per league: %s", first_detailed_season)

    common_detail_start = max(first_detailed_season.values())
    LOGGER.info(
        "STEP 3 - Common detailed era across all five leagues starts in %s.",
        format_season(common_detail_start),
    )

    # Known caveat: fouls appear later than shots in some leagues (Ligue 1 has
    # shots from 2005/06 but no fouls before 2007/08). Foul-based measures such
    # as cards per foul therefore simply skip those matches, rather than
    # shortening the detailed era for every other league.
    first_foul_season = (
        enriched.loc[enriched["HasFoulStats"]]
        .groupby("League")["SeasonStartYear"].min()
        .to_dict()
    )
    LOGGER.info("STEP 3 - First season with foul statistics per league: %s", first_foul_season)

    return enriched, common_detail_start


# ---------------------------------------------------------------------------
# Step 4 - analysis tables
# ---------------------------------------------------------------------------

def build_match_level_full(matches: pd.DataFrame) -> pd.DataFrame:
    """Cleaned match-level table covering the full 33-season range."""
    columns = [
        "Date", "League", "Season", "SeasonStartYear", "HomeTeam", "AwayTeam",
        "FTHG", "FTAG", "FTR", "HTHG", "HTAG", "HTR",
        "TotalGoals", "GoalDiff_HomeMinusAway", "HomeWin", "AwayWin", "Draw",
        "HasShotStats", "HasFoulStats", "HasCardStats", "HasDetailedStats", "Referee",
        "HS", "AS", "HST", "AST", "HF", "AF", "HC", "AC", "HY", "AY", "HR", "AR",
    ]
    return matches[columns].sort_values(["League", "Date"]).reset_index(drop=True)


def build_season_league_summary(matches: pd.DataFrame) -> pd.DataFrame:
    """League-by-season aggregates: draw rate, goals per match and home advantage.

    This is the main source for Dashboard 1 and for the home-advantage chapter of
    the story.
    """
    summary = (
        matches.groupby(["League", "Season", "SeasonStartYear"])
        .agg(
            MatchesPlayed=("FTR", "count"),
            HomeWins=("HomeWin", "sum"),
            AwayWins=("AwayWin", "sum"),
            Draws=("Draw", "sum"),
            AvgHomeGoals=("FTHG", "mean"),
            AvgAwayGoals=("FTAG", "mean"),
            AvgTotalGoals=("TotalGoals", "mean"),
        )
        .reset_index()
    )

    summary["HomeWinPct"] = (summary["HomeWins"] / summary["MatchesPlayed"] * 100).round(2)
    summary["AwayWinPct"] = (summary["AwayWins"] / summary["MatchesPlayed"] * 100).round(2)
    summary["DrawPct"] = (summary["Draws"] / summary["MatchesPlayed"] * 100).round(2)

    # Home advantage expressed two ways: as a win-rate gap and as a goals gap.
    summary["HomeAdvantage_WinPctGap"] = (summary["HomeWinPct"] - summary["AwayWinPct"]).round(2)
    summary["HomeAdvantage_GoalGap"] = (summary["AvgHomeGoals"] - summary["AvgAwayGoals"]).round(3)

    return summary.sort_values(["League", "SeasonStartYear"]).reset_index(drop=True)


def build_detailed_matches(matches: pd.DataFrame, common_detail_start: int) -> pd.DataFrame:
    """Match-level table restricted to the era with complete shot/foul/card data.

    Adds shot accuracy (on target per shot) and shot conversion (goals per shot),
    which drive the attacking-efficiency drill-down.
    """
    detailed = matches[
        (matches["SeasonStartYear"] >= common_detail_start) & matches["HasDetailedStats"]
    ].copy()

    ratios = {
        "HomeShotAccuracy": ("HST", "HS"),
        "AwayShotAccuracy": ("AST", "AS"),
        "HomeShotConversion": ("FTHG", "HS"),
        "AwayShotConversion": ("FTAG", "AS"),
    }
    for name, (numerator, denominator) in ratios.items():
        detailed[name] = (
            (detailed[numerator] / detailed[denominator])
            .replace([np.inf, -np.inf], np.nan)
        )

    columns = [
        "Date", "League", "Season", "SeasonStartYear", "HomeTeam", "AwayTeam", "Referee",
        "FTHG", "FTAG", "FTR",
        "HS", "AS", "HST", "AST", "HF", "AF", "HC", "AC", "HY", "AY", "HR", "AR",
        "HomeShotAccuracy", "AwayShotAccuracy", "HomeShotConversion", "AwayShotConversion",
    ]
    return detailed[columns].sort_values(["League", "Date"]).reset_index(drop=True)


def build_team_season_summary(detailed: pd.DataFrame) -> pd.DataFrame:
    """Per-team, per-season averages, split into home and away performance."""
    home = (
        detailed.groupby(["League", "Season", "HomeTeam"])
        .agg(
            HomeMatches=("FTR", "count"),
            HomeGoalsFor=("FTHG", "mean"),
            HomeGoalsAgainst=("FTAG", "mean"),
            HomeShots=("HS", "mean"),
            HomeShotsOnTarget=("HST", "mean"),
            HomeCards=("HY", "mean"),
        )
        .reset_index()
        .rename(columns={"HomeTeam": "Team"})
    )

    away = (
        detailed.groupby(["League", "Season", "AwayTeam"])
        .agg(
            AwayMatches=("FTR", "count"),
            AwayGoalsFor=("FTAG", "mean"),
            AwayGoalsAgainst=("FTHG", "mean"),
            AwayShots=("AS", "mean"),
            AwayShotsOnTarget=("AST", "mean"),
            AwayCards=("AY", "mean"),
        )
        .reset_index()
        .rename(columns={"AwayTeam": "Team"})
    )

    team_season = home.merge(away, on=["League", "Season", "Team"], how="outer")
    team_season["GoalScoringHomeGap"] = team_season["HomeGoalsFor"] - team_season["AwayGoalsFor"]
    team_season["ShotHomeGap"] = team_season["HomeShots"] - team_season["AwayShots"]
    return team_season


def build_referee_summary(detailed: pd.DataFrame) -> pd.DataFrame:
    """Per-referee discipline averages, filtered to reliable sample sizes."""
    referees = detailed.dropna(subset=["Referee"]).copy()
    referees = referees[referees["Referee"].astype(str).str.strip() != ""]

    referees["TotalYellows"] = referees["HY"] + referees["AY"]
    referees["TotalReds"] = referees["HR"] + referees["AR"]
    referees["TotalFouls"] = referees["HF"] + referees["AF"]

    summary = (
        referees.groupby(["Referee", "League"])
        .agg(
            MatchesOfficiated=("FTR", "count"),
            AvgYellowsPerMatch=("TotalYellows", "mean"),
            AvgRedsPerMatch=("TotalReds", "mean"),
            AvgFoulsPerMatch=("TotalFouls", "mean"),
        )
        .reset_index()
    )

    summary = summary[summary["MatchesOfficiated"] >= MIN_MATCHES_PER_REFEREE].copy()
    summary["AvgYellowsPerMatch"] = summary["AvgYellowsPerMatch"].round(2)
    summary["AvgRedsPerMatch"] = summary["AvgRedsPerMatch"].round(3)
    summary["AvgFoulsPerMatch"] = summary["AvgFoulsPerMatch"].round(2)
    return summary.sort_values("AvgYellowsPerMatch", ascending=False).reset_index(drop=True)


def add_era_column(season_summary: pd.DataFrame) -> pd.DataFrame:
    """Attach a five-year era bucket to each league-season row."""
    with_era = season_summary.copy()
    with_era["Era"] = pd.cut(
        with_era["SeasonStartYear"], bins=ERA_BIN_EDGES, labels=ERA_LABELS
    )
    return with_era


def build_attacking_evolution_summary(season_summary: pd.DataFrame) -> pd.DataFrame:
    """Draw rate and goals per match, averaged per league per five-year era.

    Used only for the summary/KPI view - the dashboard trend lines read the
    season-level table so that individual-season swings remain visible.
    """
    with_era = add_era_column(season_summary)
    evolution = (
        with_era.groupby(["League", "Era"], observed=True)
        .agg(
            AvgDrawPct=("DrawPct", "mean"),
            AvgTotalGoals=("AvgTotalGoals", "mean"),
            Seasons=("Season", "count"),
        )
        .reset_index()
    )
    evolution["AvgDrawPct"] = evolution["AvgDrawPct"].round(2)
    evolution["AvgTotalGoals"] = evolution["AvgTotalGoals"].round(3)
    return evolution


def build_covid_league_comparison(season_summary: pd.DataFrame) -> pd.DataFrame:
    """Home advantage before COVID versus the behind-closed-doors season.

    Compares the average home-advantage gap across the two normal seasons
    preceding COVID with the gap in the season played almost entirely without
    crowds, per league.
    """
    baseline = (
        season_summary[season_summary["Season"].isin(PRE_COVID_BASELINE_SEASONS)]
        .groupby("League")["HomeAdvantage_WinPctGap"].mean()
        .rename("PreCovid_Avg_Gap")
    )
    closed_doors = (
        season_summary[season_summary["Season"] == CLOSED_DOORS_SEASON]
        .groupby("League")["HomeAdvantage_WinPctGap"].mean()
        .rename("Covid_2020_21_Gap")
    )

    comparison = pd.concat([baseline, closed_doors], axis=1).reset_index()
    comparison["Drop_Points"] = (
        comparison["PreCovid_Avg_Gap"] - comparison["Covid_2020_21_Gap"]
    ).round(2)
    comparison["Drop_Pct"] = (
        comparison["Drop_Points"] / comparison["PreCovid_Avg_Gap"] * 100
    ).round(1)
    comparison["PreCovid_Avg_Gap"] = comparison["PreCovid_Avg_Gap"].round(2)
    comparison["Covid_2020_21_Gap"] = comparison["Covid_2020_21_Gap"].round(2)

    return comparison.sort_values("Drop_Points", ascending=False).reset_index(drop=True)


def _add_var_period(detailed: pd.DataFrame) -> pd.DataFrame:
    """Label each match Pre-VAR or Post-VAR using its league's introduction year."""
    labelled = detailed.copy()
    labelled["VARIntroYear"] = labelled["League"].map(VAR_INTRODUCTION_YEAR)
    labelled["Period"] = np.where(
        labelled["SeasonStartYear"] >= labelled["VARIntroYear"], "Post-VAR", "Pre-VAR"
    )
    return labelled


def build_var_technology_effect(detailed: pd.DataFrame) -> pd.DataFrame:
    """Refereeing strictness before and after VAR, per league.

    The headline measure is cards per foul rather than raw card counts: a raw
    count cannot distinguish "more cards because more fouls were committed" from
    "more cards for the same number of fouls".
    """
    var_matches = _add_var_period(detailed)
    var_matches["TotalCards"] = (
        var_matches["HY"] + var_matches["AY"] + var_matches["HR"] + var_matches["AR"]
    )
    var_matches["TotalFouls"] = var_matches["HF"] + var_matches["AF"]
    var_matches["CardsPerFoul"] = (
        (var_matches["TotalCards"] / var_matches["TotalFouls"])
        .replace([np.inf, -np.inf], np.nan)
    )

    summary = (
        var_matches.groupby(["League", "Period"])
        .agg(
            Matches=("CardsPerFoul", "count"),
            AvgCardsPerFoul=("CardsPerFoul", "mean"),
            AvgCardsPerMatch=("TotalCards", "mean"),
            AvgFoulsPerMatch=("TotalFouls", "mean"),
        )
        .reset_index()
    )
    summary["AvgCardsPerFoul"] = summary["AvgCardsPerFoul"].round(4)
    summary["AvgCardsPerMatch"] = summary["AvgCardsPerMatch"].round(3)
    summary["AvgFoulsPerMatch"] = summary["AvgFoulsPerMatch"].round(3)
    summary["VARIntroYear"] = summary["League"].map(VAR_INTRODUCTION_YEAR)
    return summary


def build_var_home_bias_footnote(detailed: pd.DataFrame) -> pd.DataFrame:
    """Average home/away card gap before and after VAR, per league.

    Secondary cross-check only: this sits alongside the main cards-per-foul
    measure as a supporting footnote in the story, not as a headline finding.
    """
    bias = _add_var_period(detailed)
    bias["AwayCardGap"] = (bias["AY"] + bias["AR"]) - (bias["HY"] + bias["HR"])

    return (
        bias.groupby(["League", "Period"])["AwayCardGap"].mean()
        .round(3)
        .reset_index()
        .rename(columns={"AwayCardGap": "AvgAwayCardGap"})
    )


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def save_table(frame: pd.DataFrame, out_dir: Path, filename: str, description: str) -> None:
    """Write one analysis table to CSV and log what was produced."""
    frame.to_csv(out_dir / filename, index=False)
    LOGGER.info(
        "SAVED %-32s %6s rows x %2s cols  - %s",
        filename, f"{len(frame):,}", frame.shape[1], description,
    )


def build_data_quality_summary(
    matches: pd.DataFrame, common_detail_start: int
) -> list[str]:
    """Collect the data-quality facts reported in the written report."""
    return [
        f"Total matches after cleaning: {len(matches):,}",
        f"Date range: {matches['Date'].min().date()} to {matches['Date'].max().date()}",
        f"Leagues: {', '.join(LEAGUES.values())}",
        f"Seasons per league: {matches.groupby('League')['Season'].nunique().to_dict()}",
        f"Missing Referee field: {matches['Referee'].isna().sum():,} rows "
        f"({matches['Referee'].isna().mean() * 100:.1f}%)",
        f"Missing shot statistics (HS): {matches['HS'].isna().sum():,} rows "
        f"({matches['HS'].isna().mean() * 100:.1f}%)",
        f"Common detailed era starts: {format_season(common_detail_start)}",
    ]


def report_key_findings(
    season_summary: pd.DataFrame, var_effect: pd.DataFrame
) -> list[str]:
    """Reproduce the headline numbers quoted in the report and the dashboards."""
    with_era = add_era_column(season_summary)
    by_era = with_era.groupby("Era", observed=True)[["DrawPct", "AvgTotalGoals"]].mean()

    first_era, last_era = ERA_LABELS[0], ERA_LABELS[-1]
    findings = [
        f"Draw rate: {by_era.loc[first_era, 'DrawPct']:.1f}% ({first_era}) -> "
        f"{by_era.loc[last_era, 'DrawPct']:.1f}% ({last_era})",
        f"Goals per match: {by_era.loc[first_era, 'AvgTotalGoals']:.2f} ({first_era}) -> "
        f"{by_era.loc[last_era, 'AvgTotalGoals']:.2f} ({last_era})",
    ]

    cards = var_effect.pivot(index="League", columns="Period", values="AvgCardsPerFoul")
    change = ((cards["Post-VAR"] - cards["Pre-VAR"]) / cards["Pre-VAR"] * 100).sort_values()
    for league, pct in change.items():
        findings.append(f"Cards per foul, {league}: {pct:+.1f}% Post-VAR")

    return findings


def log_section(title: str, lines: list[str]) -> None:
    """Log a titled block of summary lines to the console and the log file."""
    separator = "=" * 78
    body = "\n".join(f"  {line}" for line in lines)
    LOGGER.info("\n%s\n%s\n%s\n%s", separator, title, separator, body)


def configure_logging(out_dir: Path) -> None:
    """Send log output to both the console and PROCESSING_LOG.txt."""
    log_path = out_dir / "PROCESSING_LOG.txt"
    log_path.write_text(
        "DATA PREPROCESSING LOG\n" + "=" * 78 + "\n\n", encoding="utf-8"
    )

    LOGGER.setLevel(logging.INFO)
    LOGGER.handlers.clear()

    formatter = logging.Formatter("%(message)s")
    for handler in (logging.StreamHandler(sys.stdout), logging.FileHandler(log_path, encoding="utf-8")):
        handler.setFormatter(formatter)
        LOGGER.addHandler(handler)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the analysis-ready tables for the 30 Years of European Football project.",
    )
    parser.add_argument(
        "--data-dir", type=Path, default=Path("raw_data"),
        help="Directory holding (or to receive) the football-datasets repository.",
    )
    parser.add_argument(
        "--out-dir", type=Path, default=Path("processed_data"),
        help="Directory to write the processed CSV files and the processing log into.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    configure_logging(args.out_dir)

    datasets_dir = download_raw_data(args.data_dir)

    raw = load_raw_matches(datasets_dir)
    matches = clean_matches(raw)
    matches, common_detail_start = engineer_match_features(matches)

    season_summary = build_season_league_summary(matches)
    detailed = build_detailed_matches(matches, common_detail_start)
    var_effect = build_var_technology_effect(detailed)

    LOGGER.info("STEP 4 - Writing analysis tables to %s", args.out_dir.resolve())

    # Tables consumed directly by the Tableau workbook.
    save_table(season_summary, args.out_dir, "season_league_summary.csv",
               "Dashboard 1 + story: draw rate, goals, home advantage")
    save_table(detailed, args.out_dir, "match_level_detailed.csv",
               "Dashboard 1: shot efficiency drill-down")
    save_table(var_effect, args.out_dir, "var_technology_effect.csv",
               "Dashboard 2: cards per foul, pre vs post VAR")
    save_table(build_covid_league_comparison(season_summary), args.out_dir,
               "covid_league_comparison.csv", "Story: home advantage without crowds")
    save_table(build_var_home_bias_footnote(detailed), args.out_dir,
               "var_home_bias_footnote.csv", "Story: secondary cross-check (see docstring)")

    # Supplementary tables kept for completeness and reproducibility.
    save_table(build_match_level_full(matches), args.out_dir, "match_level_full.csv",
               "Supplementary: cleaned match-level data, full range")
    save_table(build_team_season_summary(detailed), args.out_dir, "team_season_summary.csv",
               "Supplementary: per-team season averages")
    save_table(build_referee_summary(detailed), args.out_dir, "referee_summary.csv",
               "Supplementary: per-referee discipline averages")
    save_table(build_attacking_evolution_summary(season_summary), args.out_dir,
               "attacking_evolution_summary.csv", "Supplementary: draw rate and goals per era")

    LOGGER.info("NOTE - COVID-affected seasons (crowd restrictions): %s", ", ".join(COVID_SEASONS))

    log_section("DATA QUALITY SUMMARY", build_data_quality_summary(matches, common_detail_start))
    log_section("KEY FINDINGS", report_key_findings(season_summary, var_effect))

    LOGGER.info("\nDone. Processed data and PROCESSING_LOG.txt written to %s", args.out_dir.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
