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
import logging
from typing import Dict, Any

from api.db.services.system_settings_service import SystemSettingsService


def get_dynamic_oauth_config() -> Dict[str, Any]:
    """
    从数据库读取动态OAuth配置，合并静态配置
    返回格式与settings.OAUTH_CONFIG相同
    """
    configs = {}

    try:
        # 先获取所有以.oauth结尾的配置
        # SystemSettingsService.get_by_name返回列表，但实际应该是单个记录
        oauth_configs = [
            ("dingtalk.oauth", "dingtalk"),
            ("github.oauth", "github"),
            ("feishu.oauth", "feishu"),
            # 添加其他可能的OAuth配置
        ]

        for config_key, channel_name in oauth_configs:
            records = SystemSettingsService.get_by_name(config_key)
            if records:
                record = records[0] if records else None
                if record and record.value:
                    try:
                        config_data = json.loads(record.value)
                        # 检查是否启用（默认为True）
                        if config_data.get("enabled", True):
                            # 确保有必要的字段
                            if "type" in config_data and "client_id" in config_data and "client_secret" in config_data:
                                configs[channel_name] = config_data
                                logging.debug(f"Loaded dynamic OAuth config for {channel_name}")
                    except json.JSONDecodeError as e:
                        logging.error(f"Failed to parse OAuth config for {config_key}: {e}")
                    except Exception as e:
                        logging.error(f"Error processing OAuth config for {config_key}: {e}")

    except Exception as e:
        logging.error(f"Error loading dynamic OAuth config: {e}")
        # 发生错误时返回空配置，不影响系统运行

    return configs


def get_combined_oauth_config() -> Dict[str, Any]:
    """
    获取合并后的OAuth配置：静态配置 + 动态配置
    动态配置会覆盖静态配置
    """
    from common import settings

    # 获取静态配置
    static_config = getattr(settings, 'OAUTH_CONFIG', {}) or {}

    # 获取动态配置
    dynamic_config = get_dynamic_oauth_config()

    # 合并配置（动态配置优先）
    combined_config = static_config.copy()
    combined_config.update(dynamic_config)

    return combined_config


def refresh_oauth_config():
    """
    刷新settings.OAUTH_CONFIG，使动态配置立即生效
    """
    from common import settings

    try:
        combined_config = get_combined_oauth_config()
        settings.OAUTH_CONFIG = combined_config
        logging.info(f"Refreshed OAuth config, total channels: {len(combined_config)}")
        return combined_config
    except Exception as e:
        logging.error(f"Failed to refresh OAuth config: {e}")
        return getattr(settings, 'OAUTH_CONFIG', {})