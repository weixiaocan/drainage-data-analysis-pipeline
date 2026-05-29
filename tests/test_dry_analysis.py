"""测试 dry_analysis 模块"""
from pathlib import Path
import pickle

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).parent.parent


class TestDryAnalysis:
    """旱天分析模块测试"""

    @pytest.fixture
    def flow_dir(self) -> Path:
        return PROJECT_ROOT / "data" / "flow"

    @pytest.fixture
    def filter_result(self) -> Path:
        return PROJECT_ROOT / "outputs" / "筛选结果.xlsx"

    @pytest.fixture
    def output_dir(self, tmp_path: Path) -> Path:
        return tmp_path

    @pytest.fixture
    def site_info(self) -> Path:
        return PROJECT_ROOT / "点位信息.xlsx"

    def test_run_dry_analysis_import(self):
        """测试模块可导入"""
        from src.pipeline.dry_analysis import run_dry_analysis
        assert callable(run_dry_analysis)

    def test_run_dry_analysis_generates_outputs(
        self,
        flow_dir: Path,
        filter_result: Path,
        output_dir: Path,
        site_info: Path,
    ):
        """测试生成输出文件"""
        from src.pipeline.dry_analysis import run_dry_analysis

        result = run_dry_analysis(
            flow_dir=flow_dir,
            filter_result=filter_result,
            output_dir=output_dir,
            site_info=site_info,
        )

        # 检查 pickle 文件
        pickle_file = output_dir / "旱天特征曲线.pickle"
        assert pickle_file.exists()

        # 检查 xlsx 文件
        xlsx_file = output_dir / "分析结果.xlsx"
        assert xlsx_file.exists()

    def test_run_dry_analysis_returns_dict(
        self,
        flow_dir: Path,
        filter_result: Path,
        output_dir: Path,
        site_info: Path,
    ):
        """测试返回结果格式"""
        from src.pipeline.dry_analysis import run_dry_analysis

        result = run_dry_analysis(
            flow_dir=flow_dir,
            filter_result=filter_result,
            output_dir=output_dir,
            site_info=site_info,
        )

        assert "dry_curve_data" in result
        assert "statistics" in result
        assert "day_num" in result

        # 检查 dry_curve_data 格式
        assert isinstance(result["dry_curve_data"], dict)
        assert len(result["dry_curve_data"]) > 0

        for point_name, df in result["dry_curve_data"].items():
            assert isinstance(point_name, str)
            assert isinstance(df, pd.DataFrame)
            assert df.shape[0] == 1440  # 一天 1440 分钟

    def test_dry_curve_data_structure(
        self,
        flow_dir: Path,
        filter_result: Path,
        output_dir: Path,
        site_info: Path,
    ):
        """测试特征曲线数据结构"""
        from src.pipeline.dry_analysis import run_dry_analysis

        result = run_dry_analysis(
            flow_dir=flow_dir,
            filter_result=filter_result,
            output_dir=output_dir,
            site_info=site_info,
        )

        dry_curve = result["dry_curve_data"]

        # 取第一个点位检查
        first_point = list(dry_curve.keys())[0]
        df = dry_curve[first_point]

        # 检查列
        assert "f" in df.columns  # 流量
        assert "l" in df.columns  # 液位

    def test_statistics_format(
        self,
        flow_dir: Path,
        filter_result: Path,
        output_dir: Path,
        site_info: Path,
    ):
        """测试统计值格式"""
        from src.pipeline.dry_analysis import run_dry_analysis

        result = run_dry_analysis(
            flow_dir=flow_dir,
            filter_result=filter_result,
            output_dir=output_dir,
            site_info=site_info,
        )

        stats = result["statistics"]
        assert isinstance(stats, pd.DataFrame)

        # 检查必需列
        required_cols = ["点位编号", "日均流量(m³/d)", "日最大流量(L/s)", "最大液位(m)"]
        for col in required_cols:
            assert col in stats.columns

    def test_pickle_loadable(
        self,
        flow_dir: Path,
        filter_result: Path,
        output_dir: Path,
        site_info: Path,
    ):
        """测试 pickle 文件可加载"""
        from src.pipeline.dry_analysis import run_dry_analysis

        result = run_dry_analysis(
            flow_dir=flow_dir,
            filter_result=filter_result,
            output_dir=output_dir,
            site_info=site_info,
        )

        pickle_file = output_dir / "旱天特征曲线.pickle"
        with open(pickle_file, "rb") as f:
            loaded = pickle.load(f)

        assert loaded.keys() == result["dry_curve_data"].keys()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
