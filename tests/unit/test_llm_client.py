"""
tests/unit/test_llm_client.py - LLMClient 单元测试
"""

import pytest
from unittest.mock import Mock, patch
from src.core import Config, LLMClient, LLMDisabledError, LLMFailedAfterRetry


class TestLLMClientDisabled:
    """测试 LLM 禁用场景"""

    def test_disabled_raises_error(self):
        """禁用时调用抛出异常"""
        config = Config.for_testing(llm_enabled=False)
        client = LLMClient(config)
        with pytest.raises(LLMDisabledError):
            client.chat("test prompt")

    def test_no_api_key_raises_error(self):
        """无 API 密钥时抛出异常"""
        config = Config.for_testing(llm_enabled=True, llm_api_key="")
        client = LLMClient(config)
        with pytest.raises(LLMDisabledError):
            client.chat("test prompt")

    def test_json_disabled_raises_error(self):
        """禁用时调用 json 方法也抛出异常"""
        config = Config.for_testing(llm_enabled=False)
        client = LLMClient(config)
        with pytest.raises(LLMDisabledError):
            client.chat_json("test prompt")


class TestLLMClientRetry:
    """测试重试机制"""

    def test_retry_on_failure(self):
        """失败后重试"""
        config = Config.for_testing(
            llm_enabled=True,
            llm_api_key="test-key",
        )
        client = LLMClient(config)

        # Mock OpenAI client
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        client._client = mock_client

        with pytest.raises(LLMFailedAfterRetry):
            client.chat("test prompt")

        # 验证调用了 3 次
        assert mock_client.chat.completions.create.call_count == 3

    def test_success_after_retry(self):
        """重试后成功"""
        config = Config.for_testing(
            llm_enabled=True,
            llm_api_key="test-key",
        )
        client = LLMClient(config)

        # Mock: 前两次失败，第三次成功
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="success"))]

        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = [
            Exception("API Error"),
            Exception("API Error"),
            mock_response,
        ]
        client._client = mock_client

        result = client.chat("test prompt")
        assert result == "success"
        assert mock_client.chat.completions.create.call_count == 3


class TestLoadPrompt:
    """测试 Prompt 加载"""

    def test_missing_prompt_file(self):
        """Prompt 文件不存在"""
        with pytest.raises(FileNotFoundError):
            LLMClient.load_prompt("nonexistent_prompt")
