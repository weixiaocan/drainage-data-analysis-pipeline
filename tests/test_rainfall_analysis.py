"""测试 rainfall_analysis 模块"""
from pathlib import Path
import pickle

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).parent.parent


class TestRainfallAnalysis:
    """降雨分析模块测试"""

    @pytest.fixture
    def rainfall_file(self) -> Path:
        return PROJECT_ROOT / "data" / "rainfall" / "降雨数据.csv"

    @pytest.fixture
    def output_dir(self, tmp_path: Path) -> Path:
        return tmp_path

    def test_run_rainfall_analysis_import(self):
        """测试模块可导入"""
        from src.pipeline.rainfall_analysis import run_rainfall_analysis
        assert callable(run_rainfall_analysis)

    def test_run_rainfall_analysis_generates_outputs(
        self,
        rainfall_file: Path,
        output_dir: Path,
    ):
        """测试生成输出文件"""
        from src.pipeline.rainfall_analysis import run_rainfall_analysis

        result = run_rainfall_analysis(
            rainfall_file=rainfall_file,
            output_dir=output_dir,
        )

        # 检查 xlsx 文件
        xlsx_file = output_dir / "分析结果.xlsx"
        assert xlsx_file.exists()

        # 检查 pickle 文件
        pickle_file = output_dir / "场次降雨数据.pickle"
        assert pickle_file.exists()

    def test_run_rainfall_analysis_returns_dict(
        self,
        rainfall_file: Path,
        output_dir: Path,
    ):
        """测试返回结果格式"""
        from src.pipeline.rainfall_analysis import run_rainfall_analysis

        result = run_rainfall_analysis(
            rainfall_file=rainfall_file,
            output_dir=output_dir,
        )

        assert "daily_rain" in result
        assert "event_rain" in result
        assert "rain_data" in result

        assert isinstance(result["daily_rain"], pd.DataFrame)
        assert isinstance(result["event_rain"], pd.DataFrame)
        assert isinstance(result["rain_data"], pd.DataFrame)

    def test_daily_rain_format(
        self,
        rainfall_file: Path,
        output_dir: Path,
    ):
        """测试日降雨量统计格式"""
        from src.pipeline.rainfall_analysis import run_rainfall_analysis

        result = run_rainfall_analysis(
            rainfall_file=rainfall_file,
            output_dir=output_dir,
        )

        daily = result["daily_rain"]
        assert "日期" in daily.columns
        assert "日降雨量(mm)" in daily.columns

    def test_event_rain_format(
        self,
        rainfall_file: Path,
        output_dir: Path,
    ):
        """测试场次降雨统计格式"""
        from src.pipeline.rainfall_analysis import run_rainfall_analysis

        result = run_rainfall_analysis(
            rainfall_file=rainfall_file,
            output_dir=output_dir,
        )

        events = result["event_rain"]
        required_cols = ["场次编号", "开始时间", "结束时间", "总降雨量(mm)", "降雨历时(h)", "降雨等级"]
        for col in required_cols:
            assert col in events.columns

    def test_pickle_loadable(
        self,
        rainfall_file: Path,
        output_dir: Path,
    ):
        """测试 pickle 文件可加载"""
        from src.pipeline.rainfall_analysis import run_rainfall_analysis

        result = run_rainfall_analysis(
            rainfall_file=rainfall_file,
            output_dir=output_dir,
        )

        pickle_file = output_dir / "场次降雨数据.pickle"
        with open(pickle_file, "rb") as f:
            loaded = pickle.load(f)

        assert isinstance(loaded, dict)

    def test_config_parameters(
        self,
        rainfall_file: Path,
        output_dir: Path,
    ):
        """测试配置参数"""
        from src.pipeline.rainfall_analysis import run_rainfall_analysis

        # 使用不同的配置参数
        result = run_rainfall_analysis(
            rainfall_file=rainfall_file,
            output_dir=output_dir,
            config={"min_interval": 6.0, "min_rainfall": 0.5},
        )

        assert result["event_rain"] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
