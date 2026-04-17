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

import json
import pytest
from test.testcases.test_admin_api.conftest import admin_session


def test_set_dingtalk_config_and_verify_login_channels(admin_session):
    """测试设置钉钉OAuth配置后，登录通道列表应包含钉钉"""
    # 1. 设置钉钉OAuth配置
    dingtalk_config = {
        "type": "dingtalk",
        "display_name": "钉钉登录",
        "icon": "dingtalk",
        "client_id": "test_app_key_123",
        "client_secret": "test_app_secret_456",
        "redirect_uri": "https://example.com/callback",
        "authorization_url": "https://login.dingtalk.com/oauth2/auth",
        "token_url": "https://api.dingtalk.com/v1.0/oauth2/userAccessToken",
        "userinfo_url": "https://api.dingtalk.com/v1.0/contact/users/me",
        "scope": "openid profile"
    }

    response = admin_session.put(
        f"{admin_session.base_url}/api/v1/admin/variables",
        json={
            "var_name": "dingtalk.oauth",
            "var_value": json.dumps(dingtalk_config)
        }
    )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["code"] == 0
    assert "Set variable successfully" in response_data["message"]

    # 2. 测试登录通道API应包含钉钉（此测试应该会失败，因为配置还没集成到OAUTH_CONFIG）
    response = admin_session.get(
        f"{admin_session.base_url}/v1/user/login/channels"
    )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["code"] == 0

    channels = response_data.get("data", [])
    channel_names = [channel["channel"] for channel in channels]

    # 这里会失败，因为配置还没集成到OAUTH_CONFIG
    assert "dingtalk" in channel_names, f"钉钉未出现在登录通道中: {channel_names}"


def test_dingtalk_config_disabled_should_not_appear(admin_session):
    """测试禁用钉钉OAuth配置后，登录通道列表不应包含钉钉"""
    # 1. 设置禁用的钉钉OAuth配置
    dingtalk_config = {
        "type": "dingtalk",
        "display_name": "钉钉登录",
        "icon": "dingtalk",
        "client_id": "test_app_key_123",
        "client_secret": "test_app_secret_456",
        "redirect_uri": "https://example.com/callback",
        "authorization_url": "https://login.dingtalk.com/oauth2/auth",
        "token_url": "https://api.dingtalk.com/v1.0/oauth2/userAccessToken",
        "userinfo_url": "https://api.dingtalk.com/v1.0/contact/users/me",
        "scope": "openid profile",
        "enabled": False  # 禁用状态
    }

    response = admin_session.put(
        f"{admin_session.base_url}/api/v1/admin/variables",
        json={
            "var_name": "dingtalk.oauth",
            "var_value": json.dumps(dingtalk_config)
        }
    )

    assert response.status_code == 200

    # 2. 测试登录通道API不应包含钉钉（配置禁用）
    response = admin_session.get(
        f"{admin_session.base_url}/v1/user/login/channels"
    )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["code"] == 0

    channels = response_data.get("data", [])
    channel_names = [channel["channel"] for channel in channels]

    # 这里也会失败，因为配置集成逻辑还没实现
    assert "dingtalk" not in channel_names, f"禁用的钉钉配置仍出现在登录通道中: {channel_names}"


def test_default_model_provider_config_affects_new_dataset(admin_session):
    """测试默认模型提供商配置应影响新创建的数据集"""
    # 1. 设置默认模型提供商配置
    model_provider_config = {
        "provider": "openai",
        "api_key": "sk-test-api-key-1234567890",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "enabled": True
    }

    response = admin_session.put(
        f"{admin_session.base_url}/api/v1/admin/variables",
        json={
            "var_name": "default_model_provider",
            "var_value": json.dumps(model_provider_config)
        }
    )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["code"] == 0

    # 2. 创建一个测试用户来测试数据集创建（需要先简化，测试配置读取）
    # 这里我们需要一个API来获取系统配置，但当前没有
    # 所以这个测试暂时注释掉，等有相应API后再实现

    # TODO: 实现测试逻辑，当创建数据集时，应该使用配置的默认模型


def test_system_config_api_exists(admin_session):
    """测试系统配置API是否存在并可用"""
    # 当前系统没有专门的配置API，需要添加
    # 这个测试会失败，因为没有/system/config API
    response = admin_session.get(
        f"{admin_session.base_url}/v1/system/config"
    )

    # 这里会失败，因为API不存在
    assert response.status_code == 200, f"系统配置API不存在: {response.status_code}"

    response_data = response.json()
    assert response_data["code"] == 0
    assert "data" in response_data

    # 检查是否包含钉钉配置
    config = response_data["data"]
    assert "dingtalk_config" in config
    assert "default_model_provider" in config