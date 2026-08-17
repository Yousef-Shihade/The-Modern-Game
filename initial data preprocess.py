"""
The Twelfth Man - Football Data Preprocessing

Prepares European Big Five football data for Tableau analysis.

Outputs:
- match_level_full.csv
- season_league_summary.csv
- match_level_detailed.csv
- team_season_summary.csv
- referee_summary.csv
- covid_league_comparison.csv
"""

import os
import pandas as pd
import numpy as np


# ============================================================
# CONFIGURATION
# ============================================================

OUT = "processed_data"
os.makedirs(OUT, exist_ok=True)


def log(message):
    """Print preprocessing progress."""
    print(message)


# ============================================================
# MATCH-LEVEL FEATURE ENGINEERING
# ============================================================

def engineer_match_features(raw):
    """
    Add derived variables required for the football analysis.
    """

    raw = raw.copy()

    raw["TotalGoals"] = raw["FTHG"] + raw["FTAG"]

    raw["GoalDiff_HomeMinusAway"] = (
        raw["FTHG"] - raw["FTAG"]
    )

    raw["HomeWin"] = (
        raw["FTR"] == "H"
    ).astype(int)

    raw["AwayWin"] = (
        raw["FTR"] == "A"
    ).astype(int)

    raw["Draw"] = (
        raw["FTR"] == "D"
    ).astype(int)

    # Availability flags
    raw["HasShotStats"] = (
        raw["HS"].notna()
        & raw["AS"].notna()
    )

    raw["HasShotsOnTargetStats"] = (
        raw["HST"].notna()
        & raw["AST"].notna()
    )

    raw["HasCardStats"] = (
        raw["HY"].notna()
        & raw["AY"].notna()
    )

    raw["HasFoulStats"] = (
        raw["HF"].notna()
        & raw["AF"].notna()
    )

    raw["HasDetailedStats"] = (
        raw["HasShotStats"]
        & raw["HasShotsOnTargetStats"]
        & raw["HasCardStats"]
        & raw["HasFoulStats"]
    )

    log("Engineered match-level features.")

    return raw


# ============================================================
# FULL MATCH-LEVEL DATASET
# ============================================================

def create_match_level_dataset(raw):

    match_cols = [
        "Date",
        "League",
        "Season",
        "SeasonStartYear",
        "HomeTeam",
        "AwayTeam",
        "FTHG",
        "FTAG",
        "FTR",
        "HTHG",
        "HTAG",
        "HTR",
        "TotalGoals",
        "GoalDiff_HomeMinusAway",
        "HomeWin",
        "AwayWin",
        "Draw",
        "HasShotStats",
        "HasShotsOnTargetStats",
        "HasCardStats",
        "HasFoulStats",
        "HasDetailedStats",
        "Referee",
        "HS",
        "AS",
        "HST",
        "AST",
        "HF",
        "AF",
        "HC",
        "AC",
        "HY",
        "AY",
        "HR",
        "AR",
    ]

    match_level = (
        raw[match_cols]
        .sort_values(["League", "Date"])
        .reset_index(drop=True)
    )

    output_path = os.path.join(
        OUT,
        "match_level_full.csv"
    )

    match_level.to_csv(
        output_path,
        index=False
    )

    log(
        f"Saved match_level_full.csv "
        f"({len(match_level):,} rows)."
    )

    return match_level


# ============================================================
# LEAGUE-SEASON SUMMARY
# ============================================================

def create_season_summary(raw):

    season_summary = (
        raw.groupby(
            [
                "League",
                "Season",
                "SeasonStartYear"
            ]
        )
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

    season_summary["HomeWinPct"] = (
        season_summary["HomeWins"]
        / season_summary["MatchesPlayed"]
        * 100
    ).round(2)

    season_summary["AwayWinPct"] = (
        season_summary["AwayWins"]
        / season_summary["MatchesPlayed"]
        * 100
    ).round(2)

    season_summary["DrawPct"] = (
        season_summary["Draws"]
        / season_summary["MatchesPlayed"]
        * 100
    ).round(2)

    # Main home-advantage metric
    season_summary["HomeAdvantage_WinPctGap"] = (
        season_summary["HomeWinPct"]
        - season_summary["AwayWinPct"]
    ).round(2)

    # Alternative goal-based home-advantage metric
    season_summary["HomeAdvantage_GoalGap"] = (
        season_summary["AvgHomeGoals"]
        - season_summary["AvgAwayGoals"]
    ).round(3)

    season_summary = (
        season_summary
        .sort_values(
            ["League", "SeasonStartYear"]
        )
        .reset_index(drop=True)
    )

    season_summary.to_csv(
        os.path.join(
            OUT,
            "season_league_summary.csv"
        ),
        index=False
    )

    log(
        f"Saved season_league_summary.csv "
        f"({len(season_summary):,} rows)."
    )

    return season_summary


# ============================================================
# DETAILED MATCH STATISTICS
# ============================================================

def create_detailed_dataset(raw):

    # Find the first season in each league where detailed
    # statistics are available.
    detail_start = (
        raw[raw["HasDetailedStats"]]
        .groupby("League")["SeasonStartYear"]
        .min()
        .to_dict()
    )

    common_detail_start = max(
        detail_start.values()
    )

    log(
        f"Common detailed era starts in "
        f"{common_detail_start}/"
        f"{str(common_detail_start + 1)[-2:]}"
    )

    detailed = raw[
        raw["SeasonStartYear"]
        >= common_detail_start
    ].copy()

    detailed = detailed[
        detailed["HasDetailedStats"]
    ].copy()

    # Shooting efficiency
    detailed["HomeShotAccuracy"] = (
        detailed["HST"]
        / detailed["HS"]
    ).replace(
        [np.inf, -np.inf],
        np.nan
    )

    detailed["AwayShotAccuracy"] = (
        detailed["AST"]
        / detailed["AS"]
    ).replace(
        [np.inf, -np.inf],
        np.nan
    )

    detailed["HomeShotConversion"] = (
        detailed["FTHG"]
        / detailed["HS"]
    ).replace(
        [np.inf, -np.inf],
        np.nan
    )

    detailed["AwayShotConversion"] = (
        detailed["FTAG"]
        / detailed["AS"]
    ).replace(
        [np.inf, -np.inf],
        np.nan
    )

    detail_cols = [
        "Date",
        "League",
        "Season",
        "SeasonStartYear",
        "HomeTeam",
        "AwayTeam",
        "Referee",
        "FTHG",
        "FTAG",
        "FTR",
        "HS",
        "AS",
        "HST",
        "AST",
        "HF",
        "AF",
        "HC",
        "AC",
        "HY",
        "AY",
        "HR",
        "AR",
        "HomeShotAccuracy",
        "AwayShotAccuracy",
        "HomeShotConversion",
        "AwayShotConversion",
    ]

    detailed = (
        detailed[detail_cols]
        .sort_values(["League", "Date"])
        .reset_index(drop=True)
    )

    detailed.to_csv(
        os.path.join(
            OUT,
            "match_level_detailed.csv"
        ),
        index=False
    )

    log(
        f"Saved match_level_detailed.csv "
        f"({len(detailed):,} rows)."
    )

    return detailed


# ============================================================
# TEAM-SEASON SUMMARY
# ============================================================

def create_team_summary(detailed):

    home_side = (
        detailed
        .groupby(
            ["League", "Season", "HomeTeam"]
        )
        .agg(
            HomeMatches=("FTR", "count"),
            HomeGoalsFor=("FTHG", "mean"),
            HomeGoalsAgainst=("FTAG", "mean"),
            HomeShots=("HS", "mean"),
            HomeShotsOnTarget=("HST", "mean"),
            HomeCards=("HY", "mean"),
        )
        .reset_index()
        .rename(
            columns={"HomeTeam": "Team"}
        )
    )

    away_side = (
        detailed
        .groupby(
            ["League", "Season", "AwayTeam"]
        )
        .agg(
            AwayMatches=("FTR", "count"),
            AwayGoalsFor=("FTAG", "mean"),
            AwayGoalsAgainst=("FTHG", "mean"),
            AwayShots=("AS", "mean"),
            AwayShotsOnTarget=("AST", "mean"),
            AwayCards=("AY", "mean"),
        )
        .reset_index()
        .rename(
            columns={"AwayTeam": "Team"}
        )
    )

    team_season = pd.merge(
        home_side,
        away_side,
        on=["League", "Season", "Team"],
        how="outer"
    )

    # Useful Tableau home-vs-away differences
    team_season["GoalScoringHomeGap"] = (
        team_season["HomeGoalsFor"]
        - team_season["AwayGoalsFor"]
    )

    team_season["ShotHomeGap"] = (
        team_season["HomeShots"]
        - team_season["AwayShots"]
    )

    team_season.to_csv(
        os.path.join(
            OUT,
            "team_season_summary.csv"
        ),
        index=False
    )

    log(
        f"Saved team_season_summary.csv "
        f"({len(team_season):,} rows)."
    )

    return team_season


# ============================================================
# REFEREE SUMMARY
# ============================================================

def create_referee_summary(detailed):

    ref = detailed.dropna(
        subset=["Referee"]
    ).copy()

    ref = ref[
        ref["Referee"]
        .astype(str)
        .str.strip()
        != ""
    ]

    ref["TotalYellows"] = (
        ref["HY"] + ref["AY"]
    )

    ref["TotalReds"] = (
        ref["HR"] + ref["AR"]
    )

    ref["TotalFouls"] = (
        ref["HF"] + ref["AF"]
    )

    referee_summary = (
        ref.groupby(
            ["Referee", "League"]
        )
        .agg(
            MatchesOfficiated=(
                "FTR",
                "count"
            ),
            AvgYellowsPerMatch=(
                "TotalYellows",
                "mean"
            ),
            AvgRedsPerMatch=(
                "TotalReds",
                "mean"
            ),
            AvgFoulsPerMatch=(
                "TotalFouls",
                "mean"
            ),
        )
        .reset_index()
    )

    # Avoid conclusions based on very small samples.
    referee_summary = referee_summary[
        referee_summary[
            "MatchesOfficiated"
        ] >= 30
    ].copy()

    referee_summary[
        "AvgYellowsPerMatch"
    ] = referee_summary[
        "AvgYellowsPerMatch"
    ].round(2)

    referee_summary[
        "AvgRedsPerMatch"
    ] = referee_summary[
        "AvgRedsPerMatch"
    ].round(3)

    referee_summary[
        "AvgFoulsPerMatch"
    ] = referee_summary[
        "AvgFoulsPerMatch"
    ].round(2)

    referee_summary = (
        referee_summary
        .sort_values(
            "AvgYellowsPerMatch",
            ascending=False
        )
    )

    referee_summary.to_csv(
        os.path.join(
            OUT,
            "referee_summary.csv"
        ),
        index=False
    )

    log(
        f"Saved referee_summary.csv "
        f"({len(referee_summary):,} referees)."
    )

    return referee_summary


# ============================================================
# COVID-19 NATURAL EXPERIMENT
# ============================================================

def create_covid_comparison(season_summary):
    """
    Compare home advantage before COVID with the
    largely closed-door 2020/21 season.
    """

    pre_covid = (
        season_summary[
            season_summary["Season"].isin(
                ["2017/18", "2018/19"]
            )
        ]
        .groupby("League")[
            "HomeAdvantage_WinPctGap"
        ]
        .mean()
        .rename("PreCovid_Avg_Gap")
    )

    covid = (
        season_summary[
            season_summary["Season"] == "2020/21"
        ]
        .groupby("League")[
            "HomeAdvantage_WinPctGap"
        ]
        .mean()
        .rename("Covid_2020_21_Gap")
    )

    comparison = pd.concat(
        [pre_covid, covid],
        axis=1
    ).reset_index()

    comparison["Drop_Points"] = (
        comparison["PreCovid_Avg_Gap"]
        - comparison["Covid_2020_21_Gap"]
    ).round(2)

    comparison["Drop_Pct"] = (
        comparison["Drop_Points"]
        / comparison["PreCovid_Avg_Gap"]
        * 100
    ).round(1)

    comparison["PreCovid_Avg_Gap"] = (
        comparison["PreCovid_Avg_Gap"]
        .round(2)
    )

    comparison["Covid_2020_21_Gap"] = (
        comparison["Covid_2020_21_Gap"]
        .round(2)
    )

    comparison = (
        comparison
        .sort_values(
            "Drop_Points",
            ascending=False
        )
        .reset_index(drop=True)
    )

    comparison.to_csv(
        os.path.join(
            OUT,
            "covid_league_comparison.csv"
        ),
        index=False
    )

    log(
        "Saved covid_league_comparison.csv."
    )

    return comparison