"""Tests for the lightweight schema layer."""

from pathlib import Path

import pandas as pd

from src.core.schema import (
    normalize_flow_df,
    normalize_rainfall_df,
    normalize_sheet_df,
    parse_flow_filename,
    to_display_columns,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_parse_flow_filename_with_hash_point_id():
    info = parse_flow_filename("35891_#1.csv")

    assert info.device_id == "35891"
    assert info.point_id == "#1"


def test_parse_flow_filename_with_plain_point_id():
    info = parse_flow_filename("35943_13.csv")

    assert info.device_id == "35943"
    assert info.point_id == "13"


def test_normalize_flow_df_current_columns():
    df = pd.DataFrame(
        {
            "数据时间": ["2026-03-07 00:00:00"],
            "1分钟内记录总数": [1],
            "设备编号": [17620135],
            "流量(L/s)(均值)": [37.759],
            "流速(m/s)(均值)": [0.032],
            "液位(m)(均值)": [2.664],
        }
    )

    normalized = normalize_flow_df(df, "35891_#1.csv")

    assert list(normalized.columns) == [
        "timestamp",
        "device_id",
        "point_id",
        "flow_lps",
        "level_m",
        "velocity_mps",
    ]
    assert normalized.loc[0, "point_id"] == "#1"
    assert normalized.loc[0, "device_id"] == "35891"
    assert normalized.loc[0, "flow_lps"] == 37.759


def test_normalize_rainfall_df_date_rain_columns():
    df = pd.DataFrame({"date": ["2026/2/1 0:00"], "rain": [1.2]})

    normalized = normalize_rainfall_df(df)

    assert list(normalized.columns) == ["timestamp", "rain_mm"]
    assert normalized.loc[0, "rain_mm"] == 1.2


def test_normalize_sheet_df_rainfall_events():
    df = pd.DataFrame(
        {
            "场次编号": [8],
            "开始时间": ["2026-03-10 00:00"],
            "总降雨量(mm)": [10.5],
            "降雨等级": ["小雨"],
        }
    )

    logical_name, normalized = normalize_sheet_df("降雨场次分析", df)

    assert logical_name == "rainfall_events"
    assert normalized.loc[0, "event_id"] == 8
    assert normalized.loc[0, "total_rain_mm"] == 10.5


def test_to_display_columns_keeps_chinese_output_names():
    df = pd.DataFrame({"event_id": [8], "total_rain_mm": [10.5], "rain_level": ["小雨"]})

    display = to_display_columns(df, "rainfall_events")

    assert "场次编号" in display.columns
    assert "总降雨量(mm)" in display.columns
    assert "降雨等级" in display.columns
