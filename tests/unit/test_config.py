"""
tests/unit/test_config.py - Config 类单元测试
"""

import pytest
from pathlib import Path
from core import Config, ConfigLoadError


class TestConfigForTesting:
    """测试 Config.for_testing() 工厂方法"""

    def test_basic_construction(self):
        """基本构造"""
        config = Config.for_testing(output_dir="/tmp/test")
        # Windows 下路径会被 resolve 成绝对路径
        assert str(config.output_dir).endswith("tmp/test") or str(config.output_dir).endswith("tmp\\test")

    def test_flow_data_dir(self):
        """流量数据目录"""
        config = Config.for_testing(flow_data_dir="data_sample/flow/")
        # 检查路径以正确后缀结尾
        path_str = str(config.flow_data_dir).replace("\\", "/")
        assert path_str.endswith("data_sample/flow") or path_str.endswith("data_sample/flow/")

    def test_llm_disabled_by_default(self):
        """默认禁用 LLM"""
        config = Config.for_testing(output_dir="/tmp/test")
        assert config.llm_enabled is False

    def test_llm_enabled_explicitly(self):
        """显式启用 LLM"""
        config = Config.for_testing(llm_enabled=True, llm_api_key="test-key")
        assert config.llm_enabled is True
        assert config.llm_api_key == "test-key"

    def test_analysis_parameters(self):
        """分析参数"""
        config = Config.for_testing(
            missing_rate_threshold=0.2,
            expected_rows_per_day=1000,
        )
        assert config.missing_rate_threshold == 0.2
        assert config.expected_rows_per_day == 1000

    def test_default_smooth_window(self):
        """默认平滑窗口"""
        config = Config.for_testing(output_dir="/tmp/test")
        # 从 baseinfo 默认值
        assert config.smooth_window_minutes == 20


class TestConfigLoad:
    """测试 Config.load()"""

    def test_load_real_config(self):
        """加载真实配置文件"""
        config = Config.load()
        assert config.llm_model == "deepseek-chat"
        assert config.missing_rate_threshold == 0.1

    def test_output_paths(self):
        """输出路径"""
        config = Config.load()
        assert config.combined_xlsx_path.name == "综合分析结果.xlsx"
        assert config.filter_result_path.name == "筛选结果.xlsx"

    def test_reload_baseinfo(self):
        """重新加载 baseinfo"""
        config = Config.load()
        original_events = config.selected_rainfall_events
        config.reload_baseinfo()
        assert config.selected_rainfall_events == original_events


class TestConfigExceptions:
    """测试配置异常"""

    def test_missing_config_file(self, tmp_path):
        """配置文件不存在"""
        with pytest.raises(ConfigLoadError):
            Config(config_path=tmp_path / "nonexistent.yaml")
