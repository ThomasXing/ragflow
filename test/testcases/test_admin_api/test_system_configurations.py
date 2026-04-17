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

def test_set_and_get_system_configuration(admin_session):
    """测试设置和获取系统配置"""
    # 1. 设置钉钉OAuth配置
    dingtalk_config = {
        "app_key": "test_app_key_123",
        "app_secret": "test_app_secret_456",
        "redirect_uri": "https://example.com/callback",
        "enabled": True
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

    # 2. 获取钉钉OAuth配置
    response = admin_session.get(
        f"{admin_session.base_url}/api/v1/admin/variables",
        json={"var_name": "dingtalk.oauth"}
    )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["code"] == 0
    assert "data" in response_data

    data = response_data["data"]
    assert len(data) == 1
    config = data[0]

    assert config["name"] == "dingtalk.oauth"
    assert config["source"] == "admin"
    assert config["data_type"] == "json"

    parsed_config = json.loads(config["value"])
    assert parsed_config["app_key"] == "test_app_key_123"
    assert parsed_config["app_secret"] == "test_app_secret_456"
    assert parsed_config["redirect_uri"] == "https://example.com/callback"
    assert parsed_config["enabled"] is True

def test_set_and_get_model_provider_configuration(admin_session):
    """测试设置和获取模型提供商配置"""
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
    assert "Set variable successfully" in response_data["message"]

    # 2. 获取模型提供商配置
    response = admin_session.get(
        f"{admin_session.base_url}/api/v1/admin/variables",
        json={"var_name": "default_model_provider"}
    )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["code"] == 0
    assert "data" in response_data

    data = response_data["data"]
    assert len(data) == 1
    config = data[0]

    assert config["name"] == "default_model_provider"
    assert config["source"] == "admin"
    assert config["data_type"] == "json"

    parsed_config = json.loads(config["value"])
    assert parsed_config["provider"] == "openai"
    assert parsed_config["api_key"] == "sk-test-api-key-1234567890"
    assert parsed_config["base_url"] == "https://api.openai.com/v1"
    assert parsed_config["default_model"] == "gpt-4o-mini"
    assert parsed_config["enabled"] is True

def test_update_existing_configuration(admin_session):
    """测试更新现有配置"""
    # 1. 第一次设置配置
    initial_config = {
        "app_key": "initial_key",
        "app_secret": "initial_secret",
        "redirect_uri": "https://initial.com/callback",
        "enabled": False
    }

    response = admin_session.put(
        f"{admin_session.base_url}/api/v1/admin/variables",
        json={
            "var_name": "dingtalk.oauth",
            "var_value": json.dumps(initial_config)
        }
    )

    assert response.status_code == 200

    # 2. 更新配置
    updated_config = {
        "app_key": "updated_key",
        "app_secret": "updated_secret",
        "redirect_uri": "https://updated.com/callback",
        "enabled": True
    }

    response = admin_session.put(
        f"{admin_session.base_url}/api/v1/admin/variables",
        json={
            "var_name": "dingtalk.oauth",
            "var_value": json.dumps(updated_config)
        }
    )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["code"] == 0

    # 3. 验证更新后的值
    response = admin_session.get(
        f"{admin_session.base_url}/api/v1/admin/variables",
        json={"var_name": "dingtalk.oauth"}
    )

    assert response.status_code == 200
    response_data = response.json()
    parsed_config = json.loads(response_data["data"][0]["value"])

    assert parsed_config["app_key"] == "updated_key"
    assert parsed_config["app_secret"] == "updated_secret"
    assert parsed_config["redirect_uri"] == "https://updated.com/callback"
    assert parsed_config["enabled"] is True

def test_list_all_variables(admin_session):
    """测试列出所有变量"""
    # 1. 设置一些配置
    configs = [
        ("dingtalk.oauth", {"app_key": "test1", "app_secret": "secret1", "redirect_uri": "https://test1.com", "enabled": True}),
        ("default_model_provider", {"provider": "openai", "api_key": "key1", "enabled": True}),
        ("some.other.config", {"value": "test_value"})
    ]

    for name, value in configs:
        response = admin_session.put(
            f"{admin_session.base_url}/api/v1/admin/variables",
            json={
                "var_name": name,
                "var_value": json.dumps(value)
            }
        )
        assert response.status_code == 200

    # 2. 列出所有变量
    response = admin_session.get(f"{admin_session.base_url}/api/v1/admin/variables")

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["code"] == 0
    assert "data" in response_data

    variables = response_data["data"]
    variable_names = {var["name"] for var in variables}

    # 检查我们设置的配置都在列表中
    for name, _ in configs:
        assert name in variable_names

def test_invalid_json_configuration(admin_session):
    """测试无效的JSON配置"""
    response = admin_session.put(
        f"{admin_session.base_url}/api/v1/admin/variables",
        json={
            "var_name": "dingtalk.oauth",
            "var_value": "invalid_json{"
        }
    )

    # 注意：当前API只是将值作为字符串存储，所以不会验证JSON格式
    # 这里测试API接受任何字符串值
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["code"] == 0

def test_missing_required_fields(admin_session):
    """测试缺少必需字段"""
    # 测试缺少var_name
    response = admin_session.put(
        f"{admin_session.base_url}/api/v1/admin/variables",
        json={
            "var_value": "some_value"
        }
    )

    assert response.status_code == 400
    response_data = response.json()
    assert response_data["code"] == 400
    assert "Var name is required" in response_data["message"]

    # 测试缺少var_value
    response = admin_session.put(
        f"{admin_session.base_url}/api/v1/admin/variables",
        json={
            "var_name": "test.config"
        }
    )

    assert response.status_code == 400
    response_data = response.json()
    assert response_data["code"] == 400
    assert "Var value is required" in response_data["message"]

def test_empty_request_body(admin_session):
    """测试空请求体"""
    response = admin_session.put(
        f"{admin_session.base_url}/api/v1/admin/variables",
        json={}
    )

    assert response.status_code == 400
    response_data = response.json()
    assert response_data["code"] == 400
    assert "Var name is required" in response_data["message"]