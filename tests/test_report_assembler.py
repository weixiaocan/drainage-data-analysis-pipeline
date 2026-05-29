"""测试 report_assembler 模块"""
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).parent.parent


class TestReportAssembler:
    """报告组装模块测试"""

    @pytest.fixture
    def template_file(self) -> Path:
        return PROJECT_ROOT / "监测数据分析报告模板-更新.docx"

    @pytest.fixture
    def analysis_results_file(self) -> Path:
        return PROJECT_ROOT / "outputs" / "分析结果.xlsx"

    @pytest.fixture
    def site_info_file(self) -> Path:
        return PROJECT_ROOT / "点位信息.xlsx"

    @pytest.fixture
    def dry_curve_file(self) -> Path:
        return PROJECT_ROOT / "outputs" / "旱天特征曲线.pickle"

    @pytest.fixture
    def output_dir(self, tmp_path: Path) -> Path:
        return tmp_path

    def test_run_report_assembler_import(self):
        """测试模块可导入"""
        from src.pipeline.report_assembler import run_report_assembler
        assert callable(run_report_assembler)

    def test_run_report_assembler_runs(
        self,
        template_file: Path,
        analysis_results_file: Path,
        site_info_file: Path,
        dry_curve_file: Path,
        output_dir: Path,
    ):
        """测试运行不报错"""
        from src.pipeline.report_assembler import run_report_assembler

        result = run_report_assembler(
            template_file=template_file,
            analysis_results_file=analysis_results_file,
            site_info_file=site_info_file,
            dry_curve_file=dry_curve_file,
            output_dir=output_dir,
        )

        assert result is not None

    def test_run_report_assembler_returns_dict(
        self,
        template_file: Path,
        analysis_results_file: Path,
        site_info_file: Path,
        dry_curve_file: Path,
        output_dir: Path,
    ):
        """测试返回结果格式"""
        from src.pipeline.report_assembler import run_report_assembler

        result = run_report_assembler(
            template_file=template_file,
            analysis_results_file=analysis_results_file,
            site_info_file=site_info_file,
            dry_curve_file=dry_curve_file,
            output_dir=output_dir,
        )

        assert "output_file" in result
        assert "stats" in result
        assert isinstance(result["output_file"], Path)
        assert isinstance(result["stats"], dict)

    def test_output_file_created(
        self,
        template_file: Path,
        analysis_results_file: Path,
        site_info_file: Path,
        dry_curve_file: Path,
        output_dir: Path,
    ):
        """测试输出文件创建"""
        from src.pipeline.report_assembler import run_report_assembler

        result = run_report_assembler(
            template_file=template_file,
            analysis_results_file=analysis_results_file,
            site_info_file=site_info_file,
            dry_curve_file=dry_curve_file,
            output_dir=output_dir,
        )

        assert result["output_file"].exists()
        assert result["output_file"].name == "监测数据分析报告.docx"

    def test_stats_structure(
        self,
        template_file: Path,
        analysis_results_file: Path,
        site_info_file: Path,
        dry_curve_file: Path,
        output_dir: Path,
    ):
        """测试统计信息结构"""
        from src.pipeline.report_assembler import run_report_assembler

        result = run_report_assembler(
            template_file=template_file,
            analysis_results_file=analysis_results_file,
            site_info_file=site_info_file,
            dry_curve_file=dry_curve_file,
            output_dir=output_dir,
        )

        stats = result["stats"]
        assert "tables_filled" in stats
        assert "images_generated" in stats
        assert "points_processed" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
