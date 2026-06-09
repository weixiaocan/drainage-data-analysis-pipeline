"""
排污规律分类器

根据旱天特征曲线数据进行分类判断：
- 第1类：符合典型生活用水排放规律
- 第2类：不符合典型规律（泵控/工业/公建等）
- 第3类：曲线平坦/异常

使用方法：
    from classifier import classify_pattern
    result = classify_pattern(curve_df)
"""

import numpy as np
import pandas as pd
from scipy.signal import find_peaks
from dataclasses import dataclass
from typing import Tuple, Dict, Any


@dataclass
class PatternFeatures:
    """特征值"""
    kz: float                    # 时变化系数
    mean_flow: float             # 日均流量
    max_flow: float              # 最大流量
    min_flow: float              # 最小流量
    fluctuation: float           # 波动范围 (max-min)/mean
    peak_count: int              # 波峰数量
    peak_times: list             # 波峰时间列表
    night_mean: float            # 夜间平均流量
    morning_mean: float          # 早上平均流量
    noon_mean: float             # 中午平均流量
    evening_mean: float          # 晚上平均流量
    morning_max: float           # 早上峰值
    evening_max: float           # 晚上峰值
    night_is_lowest: bool        # 夜间是否最低
    evening_has_peak: bool       # 晚上是否有明显高峰
    morning_has_peak: bool       # 早上是否有小高峰
    has_periodic_pattern: bool   # 是否有周期性规律


def calculate_features(curve: pd.DataFrame) -> PatternFeatures:
    """
    计算特征值

    Args:
        curve: 特征曲线 DataFrame，需包含 'f' 列（流量），index 为时间

    Returns:
        PatternFeatures 对象
    """
    flow = curve["f"].values

    # 基础统计
    mean_flow = float(flow.mean())
    max_flow = float(flow.max())
    min_flow = float(flow.min())
    kz = max_flow / mean_flow if mean_flow > 0 else 0
    fluctuation = (max_flow - min_flow) / mean_flow if mean_flow > 0 else 0

    # 峰识别
    prominence = mean_flow * 0.15
    distance = 120  # 分钟
    peaks, _ = find_peaks(flow, prominence=prominence, distance=distance)
    peak_count = len(peaks)
    peak_times = [f"{curve.index[p].hour:02d}:{curve.index[p].minute:02d}" for p in peaks] if len(peaks) > 0 else []

    # 时段统计 (按分钟计算索引)
    # 夜间 0-7点 (0-419), 早上 7-10点 (420-599), 中午 11-15点 (660-899), 晚上 18-24点 (1080-1439)
    night_mean = float(flow[0:420].mean())
    morning_mean = float(flow[420:600].mean())
    noon_mean = float(flow[660:900].mean())
    evening_mean = float(flow[1080:1440].mean()) if len(flow) >= 1440 else float(flow[1080:].mean())

    morning_max = float(flow[420:600].max())
    evening_max = float(flow[1080:1440].max()) if len(flow) >= 1440 else float(flow[1080:].max())

    # 判断条件
    night_is_lowest = night_mean < morning_mean and night_mean < noon_mean and night_mean < evening_mean
    evening_has_peak = evening_max > mean_flow * 1.15
    morning_has_peak = morning_max > mean_flow

    # 周期性规律判断：>=4个波峰 且 有显著深夜波峰
    has_periodic_pattern = _check_periodic_pattern(peak_times, peak_count, curve, mean_flow)

    return PatternFeatures(
        kz=kz,
        mean_flow=mean_flow,
        max_flow=max_flow,
        min_flow=min_flow,
        fluctuation=fluctuation,
        peak_count=peak_count,
        peak_times=peak_times,
        night_mean=night_mean,
        morning_mean=morning_mean,
        noon_mean=noon_mean,
        evening_mean=evening_mean,
        morning_max=morning_max,
        evening_max=evening_max,
        night_is_lowest=night_is_lowest,
        evening_has_peak=evening_has_peak,
        morning_has_peak=morning_has_peak,
        has_periodic_pattern=has_periodic_pattern,
    )


def _check_periodic_pattern(peak_times: list, peak_count: int, curve: pd.DataFrame, mean_val: float) -> bool:
    """
    检查是否有周期性规律（泵站调控特征）

    条件：>=4个波峰，且有显著深夜波峰（0-5点，波峰值>日均）
    """
    if peak_count < 4:
        return False

    night_peaks = []
    for t in peak_times:
        if "00:" <= t <= "04:59":
            hour, minute = int(t[:2]), int(t[3:5])
            idx = hour * 60 + minute
            if idx < len(curve):
                val = curve["f"].iloc[idx]
                if val > mean_val:
                    night_peaks.append(t)

    return len(night_peaks) > 0


def classify_pattern(curve: pd.DataFrame) -> Tuple[int, PatternFeatures, str]:
    """
    执行分类判断

    Args:
        curve: 特征曲线 DataFrame

    Returns:
        (category, features, reason)
        - category: 分类编号 (1/2/3)
        - features: 特征值对象
        - reason: 分类原因
    """
    features = calculate_features(curve)

    # 规则1: Kz < 1.2
    if features.kz < 1.2:
        if features.has_periodic_pattern:
            return 2, features, f"Kz={features.kz:.2f}<1.2但有周期性规律，疑似泵站调控"
        else:
            return 3, features, f"Kz={features.kz:.2f}<1.2，波动范围{features.fluctuation*100:.0f}%<30%，曲线平坦"

    # 规则2: Kz >= 1.2，先检查周期性规律
    if features.has_periodic_pattern:
        return 2, features, f"一天内出现{features.peak_count}个波峰，呈锯齿状规律涨落，疑似泵站调控"

    # 规则3: 检查是否符合第1类条件
    if features.night_is_lowest and features.evening_has_peak and features.morning_has_peak:
        return 1, features, f"夜间流量最低，晚上高峰明显，早上有小高峰，符合典型生活用水排放规律"

    # 规则4: 不符合第1类，归为第2类
    return 2, features, f"不符合典型生活用水排放规律"


def generate_description_prompt(point_name: str, features: PatternFeatures, category: int) -> str:
    """
    生成用于LLM的描述生成prompt

    Args:
        point_name: 点位名称
        features: 特征值
        category: 分类编号

    Returns:
        prompt字符串
    """
    category_names = {
        1: "符合典型生活用水排放规律",
        2: "不符合典型生活用水排放规律",
        3: "曲线平坦/异常"
    }

    # 计算48个半小时平均值
    halfhourly = []
    for i in range(48):
        start = i * 30
        end = (i + 1) * 30
        # 这里假设curve是1440分钟的数据

    prompt = f"""请根据以下特征数据生成排污规律描述（50-80字）。

点位编号：{point_name}
分类：第{category}类 - {category_names[category]}

特征数据：
- Kz值：{features.kz:.2f}
- 日均流量：{features.mean_flow:.2f} L/s
- 波峰数量：{features.peak_count}
- 波峰时间：{', '.join(features.peak_times[:5]) if features.peak_times else '无'}
- 夜间(0-7点)平均：{features.night_mean:.2f} L/s
- 早上(7-10点)平均：{features.morning_mean:.2f} L/s，峰值：{features.morning_max:.2f} L/s
- 晚上(18-24点)平均：{features.evening_mean:.2f} L/s，峰值：{features.evening_max:.2f} L/s

描述要求：
- 说明曲线特征和波峰波谷出现时段
- 第2类仅在有明显特征时说明疑似原因（泵控/工业/公建）
- 简洁专业，50-80字

只输出描述文本，不要其他内容。
"""
    return prompt


if __name__ == "__main__":
    # 测试示例
    import sys
    print("排污规律分类器")
    print("使用方法: from classifier import classify_pattern")
