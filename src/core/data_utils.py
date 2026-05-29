"""数据处理工具函数

提供通用的数据读取、列名检测等功能，避免代码重复。
"""

from pathlib import Path
from typing import Optional

import pandas as pd


def read_csv_with_fallback(path: Path) -> pd.DataFrame:
    """尝试多种编码读取 CSV 文件

    Args:
        path: CSV 文件路径

    Returns:
        读取成功的 DataFrame

    Raises:
        Exception: 所有编码都失败时抛出最后一个异常
    """
    last_err: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "gbk", "gb2312"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except Exception as err:
            last_err = err
    if last_err:
        raise last_err
    raise RuntimeError(f"无法读取 CSV: {path}")


def detect_flow_columns(df: pd.DataFrame) -> tuple[str, str, str, Optional[str]]:
    """检测流量数据 CSV 的列名

    自动识别时间、流量、液位、流速列。

    Args:
        df: 包含流量数据的 DataFrame

    Returns:
        (time_col, flow_col, level_col, velocity_col)

    Raises:
        ValueError: 无法识别必需列时抛出
    """
    cols = [str(c).strip() for c in df.columns]

    # 检测时间列
    time_col = "数据时间" if "数据时间" in cols else next((c for c in cols if "时间" in c), None)
    if time_col is None:
        raise ValueError(f"无法识别时间列，可用列: {cols}")

    # 检测流量列
    flow_col = "流量(L/s)(均值)" if "流量(L/s)(均值)" in cols else next((c for c in cols if "流量" in c), None)
    if flow_col is None:
        raise ValueError(f"无法识别流量列，可用列: {cols}")

    # 检测液位列（可选）
    level_col = "液位(m)(均值)" if "液位(m)(均值)" in cols else next((c for c in cols if "液位" in c), None)

    # 检测流速列（可选）
    velocity_col = "流速(m/s)(均值)" if "流速(m/s)(均值)" in cols else next((c for c in cols if "流速" in c), None)

    return time_col, flow_col, level_col, velocity_col


def parse_point_name(file_path: Path) -> str:
    """从流量数据文件名解析点位编号

    Args:
        file_path: 流量数据 CSV 文件路径

    Returns:
        点位编号（文件名去掉扩展名）
    """
    return file_path.stem


def detect_site_info_columns(df: pd.DataFrame) -> dict[str, Optional[str]]:
    """检测点位信息 Excel 的列名

    通过关键词识别各列，而非硬编码索引。

    Args:
        df: 包含点位信息的 DataFrame

    Returns:
        {
            "point_name": 列名,
            "device_id": 列名,
            "diameter": 列名,
            "depth": 列名,
            "pipe_type": 列名,
        }
    """
    col_mapping: dict[str, Optional[str]] = {
        "point_name": None,
        "device_id": None,
        "diameter": None,
        "depth": None,
        "pipe_type": None,
    }

    for col in df.columns:
        col_str = str(col).strip()
        if "点位" in col_str or "监测点" in col_str or "名称" in col_str:
            if col_mapping["point_name"] is None:
                col_mapping["point_name"] = col
        elif "设备" in col_str or "编号" in col_str:
            if col_mapping["device_id"] is None:
                col_mapping["device_id"] = col
        elif "管径" in col_str:
            col_mapping["diameter"] = col
        elif "井深" in col_str or "深度" in col_str:
            col_mapping["depth"] = col
        elif "管道类型" in col_str or "管类型" in col_str:
            col_mapping["pipe_type"] = col

    return col_mapping
