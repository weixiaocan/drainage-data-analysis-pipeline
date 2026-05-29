"""LLM 报告文字生成模块

使用 LLM 生成复杂的报告段落，包括：
- 充满度分段描述
- 溢流风险分段描述
- 淤积风险分段描述
- 雨天风险描述
- 风险分析总结
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from src.core.llm_client import LLMClient


@dataclass
class RiskSegment:
    """风险分段统计"""
    level: str           # 风险等级描述
    threshold: str       # 阈值范围
    count: int           # 点位数
    point_names: List[str]  # 点位名称列表


class LLMReportWriter:
    """LLM 报告文字生成器"""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Args:
            llm_client: LLM 客户端，为 None 时使用降级策略
        """
        self.llm = llm_client
        self.prompts_dir = Path(__file__).parent.parent.parent / "prompts"

    def generate_fullness_description(
        self,
        dry_risk_df: pd.DataFrame,
        monitoring_round: str = "第一轮",
    ) -> str:
        """
        生成最大充满度分段描述。

        Args:
            dry_risk_df: 旱天风险 DataFrame
            monitoring_round: 监测轮次

        Returns:
            生成的描述文字
        """
        if dry_risk_df.empty:
            return ""

        # 统计各档位点位
        segments = self._classify_fullness(dry_risk_df)

        # 构建 prompt
        prompt = self._build_fullness_prompt(segments, monitoring_round)

        # 调用 LLM
        result = self._call_llm(prompt)

        if result:
            return result

        # 降级：使用模板生成
        return self._fallback_fullness_description(segments, monitoring_round)

    def generate_overflow_description(
        self,
        dry_risk_df: pd.DataFrame,
        monitoring_round: str = "第一轮",
    ) -> str:
        """生成溢流风险分段描述"""
        if dry_risk_df.empty:
            return ""

        segments = self._classify_overflow(dry_risk_df)
        prompt = self._build_overflow_prompt(segments, monitoring_round)

        result = self._call_llm(prompt)
        if result:
            return result

        return self._fallback_overflow_description(segments, monitoring_round)

    def generate_silting_description(
        self,
        dry_risk_df: pd.DataFrame,
        monitoring_round: str = "第一轮",
    ) -> str:
        """生成淤积风险分段描述"""
        if dry_risk_df.empty:
            return ""

        segments = self._classify_silting(dry_risk_df)
        prompt = self._build_silting_prompt(segments, monitoring_round)

        result = self._call_llm(prompt)
        if result:
            return result

        return self._fallback_silting_description(segments, monitoring_round)

    def generate_rainy_risk_description(
        self,
        rainy_risk_df: pd.DataFrame,
        event_info: Dict,
        monitoring_round: str = "第一轮",
    ) -> str:
        """
        生成雨天风险描述。

        Args:
            rainy_risk_df: 雨天溢流风险 DataFrame
            event_info: 降雨事件信息，包含：
                - date: 降雨日期
                - rainfall: 降雨量(mm)
                - level: 降雨等级
            monitoring_round: 监测轮次
        """
        if rainy_risk_df.empty:
            return ""

        prompt = self._build_rainy_risk_prompt(rainy_risk_df, event_info, monitoring_round)

        result = self._call_llm(prompt)
        if result:
            return result

        return self._fallback_rainy_risk_description(rainy_risk_df, event_info, monitoring_round)

    def generate_risk_summary(
        self,
        dry_risk_df: pd.DataFrame,
        rainy_risk_df: Optional[pd.DataFrame] = None,
        event_info: Optional[Dict] = None,
    ) -> str:
        """生成风险分析本章小结"""
        if dry_risk_df.empty:
            return ""

        prompt = self._build_summary_prompt(dry_risk_df, rainy_risk_df, event_info)

        result = self._call_llm(prompt)
        if result:
            return result

        return self._fallback_summary(dry_risk_df, rainy_risk_df)

    # === 分类统计方法 ===

    def _classify_fullness(self, df: pd.DataFrame) -> List[RiskSegment]:
        """按最大充满度分类统计点位"""
        segments = [
            RiskSegment("运行良好", "<0.75", 0, []),
            RiskSegment("运行低风险", "0.75-1.0", 0, []),
            RiskSegment("运行中风险", "1.0-2.0", 0, []),
            RiskSegment("运行高风险", ">2.0", 0, []),
        ]

        for _, row in df.iterrows():
            fullness = float(row.get("最大充满度", 0))
            name = str(row.get("点位编号", ""))

            if fullness < 0.75:
                segments[0].count += 1
                segments[0].point_names.append(name)
            elif fullness < 1.0:
                segments[1].count += 1
                segments[1].point_names.append(name)
            elif fullness <= 2.0:
                segments[2].count += 1
                segments[2].point_names.append(name)
            else:
                segments[3].count += 1
                segments[3].point_names.append(name)

        return segments

    def _classify_overflow(self, df: pd.DataFrame) -> List[RiskSegment]:
        """按溢流风险值分类统计点位"""
        segments = [
            RiskSegment("溢流低风险", "<0.7", 0, []),
            RiskSegment("溢流中风险", "0.7-0.9", 0, []),
            RiskSegment("溢流高风险", "0.9-1.0", 0, []),
            RiskSegment("已发生溢流", ">1.0", 0, []),
        ]

        for _, row in df.iterrows():
            value = float(row.get("溢流风险值", 0))
            name = str(row.get("点位编号", ""))

            if value < 0.7:
                segments[0].count += 1
                segments[0].point_names.append(name)
            elif value < 0.9:
                segments[1].count += 1
                segments[1].point_names.append(name)
            elif value <= 1.0:
                segments[2].count += 1
                segments[2].point_names.append(name)
            else:
                segments[3].count += 1
                segments[3].point_names.append(name)

        return segments

    def _classify_silting(self, df: pd.DataFrame) -> List[RiskSegment]:
        """按淤积风险分类统计点位"""
        segments = [
            RiskSegment("低淤积风险", ">最小流速", 0, []),
            RiskSegment("中淤积风险", "0.3-0.6m/s", 0, []),
            RiskSegment("高淤积风险", "<0.3m/s", 0, []),
        ]

        for _, row in df.iterrows():
            velocity = float(row.get("旱天流速(m/s)", 0))
            name = str(row.get("点位编号", ""))

            if velocity >= 0.6:
                segments[0].count += 1
                segments[0].point_names.append(name)
            elif velocity >= 0.3:
                segments[1].count += 1
                segments[1].point_names.append(name)
            else:
                segments[2].count += 1
                segments[2].point_names.append(name)

        return segments

    # === Prompt 构建方法 ===

    def _build_fullness_prompt(self, segments: List[RiskSegment], round_name: str) -> str:
        """构建充满度描述 prompt"""
        total = sum(s.count for s in segments)

        return f"""根据以下充满度统计数据，生成一段专业、简洁的描述文字。

监测期间，{total}处监测点的旱天最大充满度情况统计如下：
- 第1档（充满度<0.75，运行良好）：{segments[0].count}处，点位：{'、'.join(segments[0].point_names) if segments[0].point_names else '无'}
- 第2档（充满度0.75-1.0，低风险）：{segments[1].count}处，点位：{'、'.join(segments[1].point_names) if segments[1].point_names else '无'}
- 第3档（充满度1.0-2.0，中风险）：{segments[2].count}处，点位：{'、'.join(segments[2].point_names) if segments[2].point_names else '无'}
- 第4档（充满度>2.0，高风险）：{segments[3].count}处，点位：{'、'.join(segments[3].point_names) if segments[3].point_names else '无'}

输出要求：
1. 使用编号格式（①②③④）分段描述，只描述有点位的档位
2. 每段包含点位数量、风险等级、具体点位名称
3. 语言简洁专业，避免重复
4. 总字数控制在150-200字

示例格式：
"监测期间，XX处监测点的旱天最大充满度情况如下：
①X处监测点最大充满度小于0.75，运行良好，分别为...
②X处监测点位液位最大充满度为0.75-1.0，存在运行低风险..."

请直接输出描述文字，不要包含其他说明："""

    def _build_overflow_prompt(self, segments: List[RiskSegment], round_name: str) -> str:
        """构建溢流风险描述 prompt"""
        total = sum(s.count for s in segments)

        return f"""根据以下溢流风险统计数据，生成一段专业、简洁的描述文字。

{round_name}监测期间，{total}处监测点的旱天溢流风险值情况统计如下：
- 溢流风险值<0.7（低风险）：{segments[0].count}处
- 溢流风险值0.7-0.9（中风险）：{segments[1].count}处，点位：{'、'.join(segments[1].point_names) if segments[1].point_names else '无'}
- 溢流风险值0.9-1.0（高风险）：{segments[2].count}处，点位：{'、'.join(segments[2].point_names) if segments[2].point_names else '无'}
- 溢流风险值>1.0（已发生溢流）：{segments[3].count}处，点位：{'、'.join(segments[3].point_names) if segments[3].point_names else '无'}

输出要求：
1. 使用编号格式（①②）分段描述，只描述有点位的档位
2. 低风险档位只需说明数量，中风险及以上需列明点位名称
3. 语言简洁专业

请直接输出描述文字："""

    def _build_silting_prompt(self, segments: List[RiskSegment], round_name: str) -> str:
        """构建淤积风险描述 prompt"""
        total = sum(s.count for s in segments)

        return f"""根据以下淤积风险统计数据，生成一段专业、简洁的描述文字。

{round_name}监测期间，{total}处监测点的淤积风险情况统计如下：
- 流速>=0.6m/s（低淤积风险）：{segments[0].count}处
- 流速0.3-0.6m/s（中淤积风险）：{segments[1].count}处，点位：{'、'.join(segments[1].point_names) if segments[1].point_names else '无'}
- 流速<0.3m/s（高淤积风险）：{segments[2].count}处，点位：{'、'.join(segments[2].point_names) if segments[2].point_names else '无'}

输出要求：
1. 使用编号格式分段描述
2. 说明流速情况和淤积风险等级
3. 语言简洁专业

请直接输出描述文字："""

    def _build_rainy_risk_prompt(
        self,
        df: pd.DataFrame,
        event_info: Dict,
        round_name: str,
    ) -> str:
        """构建雨天风险描述 prompt"""
        # 统计风险等级
        low_count = len(df[df["溢流风险值"] < 0.7])
        mid_count = len(df[(df["溢流风险值"] >= 0.7) & (df["溢流风险值"] < 0.9)])
        high_count = len(df[df["溢流风险值"] >= 0.9])

        mid_points = df[(df["溢流风险值"] >= 0.7) & (df["溢流风险值"] < 0.9)]["点位编号"].tolist()
        high_points = df[df["溢流风险值"] >= 0.9]["点位编号"].tolist()

        event_date = event_info.get("date", "")
        rainfall = event_info.get("rainfall", 0)
        level = event_info.get("level", "小雨")

        return f"""根据以下雨天溢流风险统计数据，生成一段专业、简洁的描述文字。

监测期间，{len(df)}处监测点位在{event_date}发生的{rainfall}mm{level}事件下的溢流风险情况：
- 溢流风险值<0.7（低风险）：{low_count}处
- 溢流风险值0.7-0.9（中风险）：{mid_count}处，点位：{'、'.join(mid_points) if mid_points else '无'}
- 溢流风险值>=0.9（高风险）：{high_count}处，点位：{'、'.join(high_points) if high_points else '无'}

输出要求：
1. 使用编号格式分段描述
2. 语言简洁专业

请直接输出描述文字："""

    def _build_summary_prompt(
        self,
        dry_risk_df: pd.DataFrame,
        rainy_risk_df: Optional[pd.DataFrame],
        event_info: Optional[Dict],
    ) -> str:
        """构建风险分析总结 prompt"""
        # 统计各风险等级点位数
        fullness_seg = self._classify_fullness(dry_risk_df)
        overflow_seg = self._classify_overflow(dry_risk_df)
        silting_seg = self._classify_silting(dry_risk_df)

        summary_data = f"""请根据以下数据生成风险分析章节的小结：

一、最大充满度统计：
- 运行良好（<0.75）：{fullness_seg[0].count}处
- 运行低风险（0.75-1.0）：{fullness_seg[1].count}处
- 运行中风险（1.0-2.0）：{fullness_seg[2].count}处，点位：{'、'.join(fullness_seg[2].point_names) if fullness_seg[2].point_names else '无'}
- 运行高风险（>2.0）：{fullness_seg[3].count}处，点位：{'、'.join(fullness_seg[3].point_names) if fullness_seg[3].point_names else '无'}

二、溢流风险统计：
- 低风险：{overflow_seg[0].count}处
- 中风险：{overflow_seg[1].count}处，点位：{'、'.join(overflow_seg[1].point_names) if overflow_seg[1].point_names else '无'}
- 高风险及以上：{overflow_seg[2].count + overflow_seg[3].count}处

三、淤积风险统计：
- 低淤积风险：{silting_seg[0].count}处
- 中淤积风险：{silting_seg[1].count}处
- 高淤积风险：{silting_seg[2].count}处

输出要求：
1. 分点总结（1）（2）（3）（4），分别对应最大充满度、溢流风险、淤积风险、综合建议
2. 每点包含关键数据和简要建议
3. 语言专业简洁，总字数300-400字

请直接输出小结内容："""

        return summary_data

    # === 降级方法 ===

    def _fallback_fullness_description(
        self,
        segments: List[RiskSegment],
        round_name: str,
    ) -> str:
        """降级：模板生成充满度描述"""
        total = sum(s.count for s in segments)
        lines = [f"监测期间，{total}处监测点的旱天最大充满度情况如下："]

        labels = ["①", "②", "③", "④"]
        thresholds = ["小于0.75", "为0.75-1.0", "为1.0~2.0", "大于2.0"]
        risk_desc = ["运行良好", "存在运行低风险", "存在运行中风险", "存在运行高风险"]

        for i, seg in enumerate(segments):
            if seg.count > 0:
                names = "、".join(seg.point_names)
                lines.append(
                    f"{labels[i]}{seg.count}处监测点最大充满度{thresholds[i]}，"
                    f"{risk_desc[i]}，分别为{names}。"
                )

        return "\n".join(lines)

    def _fallback_overflow_description(
        self,
        segments: List[RiskSegment],
        round_name: str,
    ) -> str:
        """降级：模板生成溢流风险描述"""
        total = sum(s.count for s in segments)
        lines = [f"{round_name}监测期间，{total}处监测点的旱天溢流风险值情况如下："]

        if segments[0].count > 0:
            lines.append(f"①{segments[0].count}处监测点的溢流风险值小于0.7，溢流风险低。")

        if segments[1].count > 0:
            names = "、".join(segments[1].point_names)
            lines.append(f"②{segments[1].count}处监测点位的溢流风险值为0.7-0.9，为溢流中风险点位，该处点位为{names}。")

        if segments[2].count > 0:
            names = "、".join(segments[2].point_names)
            lines.append(f"③{segments[2].count}处监测点位溢流风险值0.9-1.0，为溢流高风险，点位为{names}。")

        return "\n".join(lines)

    def _fallback_silting_description(
        self,
        segments: List[RiskSegment],
        round_name: str,
    ) -> str:
        """降级：模板生成淤积风险描述"""
        total = sum(s.count for s in segments)
        lines = [f"{round_name}监测期间，{total}处监测点的淤积风险情况如下："]

        if segments[2].count > 0:
            lines.append(f"①{segments[2].count}处监测点的平均流速小于0.3m/s，淤积风险较高。")

        if segments[1].count > 0:
            names = "、".join(segments[1].point_names)
            lines.append(f"②{segments[1].count}处监测点的平均流速为0.3-0.6m/s，{segments[1].count}处点位为{names}。")

        if segments[0].count > 0:
            lines.append(f"③{segments[0].count}处监测点的平均流速大于0.6m/s，淤积风险低。")

        return "\n".join(lines)

    def _fallback_rainy_risk_description(
        self,
        df: pd.DataFrame,
        event_info: Dict,
        round_name: str,
    ) -> str:
        """降级：模板生成雨天风险描述"""
        low_count = len(df[df["溢流风险值"] < 0.7])
        mid_count = len(df[(df["溢流风险值"] >= 0.7) & (df["溢流风险值"] < 0.9)])
        mid_points = df[(df["溢流风险值"] >= 0.7) & (df["溢流风险值"] < 0.9)]["点位编号"].tolist()

        lines = [f"监测期间，{len(df)}处监测点位在{event_info.get('date', '')}小雨事件下的溢流风险情况如下所示："]
        lines.append(f"①{low_count}处监测点的溢流风险值小于0.7，溢流风险低。")

        if mid_count > 0:
            lines.append(f"②{mid_count}处监测点的溢流风险值为0.7-0.9，有溢流中风险，点位是{'、'.join(mid_points)}。")

        return "\n".join(lines)

    def _fallback_summary(
        self,
        dry_risk_df: pd.DataFrame,
        rainy_risk_df: Optional[pd.DataFrame],
    ) -> str:
        """降级：模板生成风险分析总结"""
        fullness_seg = self._classify_fullness(dry_risk_df)
        overflow_seg = self._classify_overflow(dry_risk_df)
        silting_seg = self._classify_silting(dry_risk_df)

        total = len(dry_risk_df)

        lines = [
            f"本章从最大充满度、溢流风险和淤积风险三个维度，对监测点位的污水系统运行风险进行了评估。主要结论如下：",
            f"（1）最大充满度方面，{total}个点位中，{fullness_seg[0].count}处运行良好，{fullness_seg[3].count}处为运行高风险。",
            f"（2）溢流风险方面，{overflow_seg[0].count}处点位溢流风险低，{overflow_seg[1].count}处为中风险，需重点关注。",
            f"（3）淤积风险方面，{silting_seg[2].count}处点位为高淤积风险，建议及时对管网进行清淤。",
            f"（4）综合来看，建议优先对高风险管段进行整改。",
        ]

        return "\n".join(lines)

    def _call_llm(self, prompt: str) -> Optional[str]:
        """调用 LLM"""
        if not self.llm:
            return None

        try:
            result = self.llm.chat(prompt, temperature=0.2)
            return result.strip() if result else None
        except Exception as e:
            print(f"LLM 调用失败: {e}")
            return None
