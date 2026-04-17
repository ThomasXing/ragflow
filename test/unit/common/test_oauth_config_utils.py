#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from common.oauth_config_utils import _standardize_oauth_config


def test_standardize_oauth_config_for_dingtalk_with_app_key_format():
    """测试钉钉OAuth配置格式转换：app_key/app_secret格式"""
    # GIVEN: 钉钉格式的配置（app_key/app_secret）
    dingtalk_config = {
        "app_key": "test_app_key_123",
        "app_secret": "test_app_secret_456",
        "redirect_uri": "https://example.com/callback",
        "enabled": True
    }

    # WHEN: 标准化配置
    result = _standardize_oauth_config("dingtalk", dingtalk_config)

    # THEN: 应该转换为标准格式
    assert result is not None
    assert result["client_id"] == "test_app_key_123"  # app_key 转换为 client_id
    assert result["client_secret"] == "test_app_secret_456"  # app_secret 转换为 client_secret
    assert result["redirect_uri"] == "https://example.com/callback"
    assert result["enabled"] is True
    assert result["type"] == "oauth2"
    assert result["display_name"] == "钉钉登录"
    assert result["icon"] == "sso"
    # 原字段应该被移除
    assert "app_key" not in result
    assert "app_secret" not in result


def test_standardize_oauth_config_for_dingtalk_with_client_id_format():
    """测试钉钉OAuth配置格式转换：client_id/client_secret格式"""
    # GIVEN: 标准格式的配置
    dingtalk_config = {
        "type": "oauth2",
        "client_id": "test_client_id_123",
        "client_secret": "test_client_secret_456",
        "redirect_uri": "https://example.com/callback",
        "enabled": True
    }

    # WHEN: 标准化配置
    result = _standardize_oauth_config("dingtalk", dingtalk_config)

    # THEN: 应该保持原样
    assert result is not None
    assert result["client_id"] == "test_client_id_123"
    assert result["client_secret"] == "test_client_secret_456"
    assert result["type"] == "oauth2"


def test_standardize_oauth_config_rejects_missing_required_fields():
    """测试标准化函数拒绝缺少必要字段的配置"""
    # GIVEN: 缺少client_id的配置
    invalid_config = {
        "app_secret": "test_secret",
        "redirect_uri": "https://example.com/callback"
    }

    # WHEN: 标准化配置
    result = _standardize_oauth_config("dingtalk", invalid_config)

    # THEN: 应该返回None
    assert result is None


def test_standardize_oauth_config_for_github():
    """测试GitHub OAuth配置格式转换"""
    # GIVEN: GitHub配置
    github_config = {
        "client_id": "github_client_id",
        "client_secret": "github_client_secret",
        "redirect_uri": "https://example.com/github-callback",
        "enabled": True
    }

    # WHEN: 标准化配置
    result = _standardize_oauth_config("github", github_config)

    # THEN: 应该标准化
    assert result is not None
    assert result["client_id"] == "github_client_id"
    assert result["client_secret"] == "github_client_secret"
    assert result["display_name"] == "GitHub登录"
    assert result["type"] == "oauth2"


def test_standardize_oauth_config_preserves_custom_display_name():
    """测试标准化函数保留自定义display_name"""
    # GIVEN: 有自定义display_name的配置
    config = {
        "client_id": "test_id",
        "client_secret": "test_secret",
        "display_name": "自定义登录名称",
        "enabled": True
    }

    # WHEN: 标准化配置
    result = _standardize_oauth_config("dingtalk", config)

    # THEN: 应该保留自定义名称
    assert result is not None
    assert result["display_name"] == "自定义登录名称"


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])