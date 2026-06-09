"""测试 data_filter 模块在无降雨数据时的行为"""

import shutil
import tempfile
from pathlib import Path

import pandas as pd

project_root = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(project_root))

from src.pipeline.data_filter.filter import _load_rainfall_daily


def test_load_rainfall_daily_no_file():
    """测试降雨文件不存在时返回空 Series"""
    result = _load_rainfall_daily(Path("/nonexistent/file.csv"))
    assert isinstance(result, pd.Series)
    assert result.empty
    print("[PASS] 降雨文件不存在时返回空 Series")


def test_run_data_filter_without_rainfall():
    """测试无降雨数据时运行完整筛选流程"""
    from src.core.config import Config
    from src.core.logger import setup_logger
    from src.pipeline.data_filter.runner import run as run_data_filter
    import logging

    # 创建临时输出目录
    tmpdir = Path(tempfile.mkdtemp())

    try:
        # 复制流量数据到临时目录
        src_flow_dir = project_root / "data" / "flow"
        tmp_flow_dir = tmpdir / "flow"
        shutil.copytree(src_flow_dir, tmp_flow_dir)

        # 指向不存在的降雨文件
        nonexistent_rain = tmpdir / "nonexistent_rain.csv"

        # 创建临时 config
        config = Config.for_testing(
            output_dir=tmpdir,
            flow_data_dir=tmp_flow_dir,
            rainfall_data_path=nonexistent_rain,
        )

        setup_logger(config.output_dir)
        logger = logging.getLogger("test_no_rain")

        # 运行筛选
        result = run_data_filter(config, logger)

        # 验证结果
        assert "selected" in result
        assert len(result["selected"]) > 0

        # 验证输出文件
        output_file = config.filter_result_path
        assert output_file.exists()

        # 读取 Excel 验证雨量行存在但为空
        df = pd.read_excel(output_file, sheet_name="筛选结果", index_col=0)
        assert "当天雨量" in df.index, "当天雨量行应存在"
        rain_row = df.loc["当天雨量"]
        # 排除最后一列（筛选说明）
        rain_data = rain_row.iloc[:-1]
        # 检查是否全为空
        assert rain_data.isna().all(), f"无降雨数据时，雨量行应为空，实际值: {list(rain_data.values[:5])}"
        print(f"[PASS] 无降雨数据时正确运行筛选")
        print(f"  点位数: {len(result['selected'])}")
        print(f"  '当天雨量'行存在但为空")

    finally:
        # 尝试清理，忽略错误
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception:
            pass


if __name__ == "__main__":
    test_load_rainfall_daily_no_file()
    test_run_data_filter_without_rainfall()
    print("\n所有测试通过!")
