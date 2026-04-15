#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
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

from common.http_client import async_request, sync_request
from .oauth import OAuthClient, UserInfo


class DingTalkOAuthClient(OAuthClient):
    def __init__(self, config):
        """
        Initialize the DingTalkOAuthClient with the provider's configuration.
        """
        # 钉钉 OAuth 2.0 配置
        config.update({
            "authorization_url": "https://login.dingtalk.com/oauth2/auth",
            "token_url": "https://api.dingtalk.com/v1.0/oauth2/userAccessToken",
            "userinfo_url": "https://api.dingtalk.com/v1.0/contact/users/me",
            "scope": config.get("scope", "openid profile")
        })
        super().__init__(config)

    def fetch_user_info(self, access_token, **kwargs):
        """
        Fetch DingTalk user info (synchronous).
        钉钉 API 返回的用户信息格式：
        {
            "nick": "张三",
            "unionid": "xxxx",
            "openid": "xxxx",
            "main_org_auth_high_level": true,
            "avatar_url": "https://xxx",
            "email": "zhangsan@example.com"
        }
        """
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "x-acs-dingtalk-access-token": access_token
            }
            response = sync_request("GET", self.userinfo_url, headers=headers, timeout=self.http_request_timeout)
            response.raise_for_status()
            user_info = response.json()

            # 钉钉返回的数据结构
            return self.normalize_user_info(user_info)
        except Exception as e:
            raise ValueError(f"Failed to fetch DingTalk user info: {e}")

    async def async_fetch_user_info(self, access_token, **kwargs):
        """Async variant of fetch_user_info using httpx."""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "x-acs-dingtalk-access-token": access_token
        }
        try:
            response = await async_request(
                "GET",
                self.userinfo_url,
                headers=headers,
                timeout=self.http_request_timeout,
            )
            response.raise_for_status()
            user_info = response.json()

            return self.normalize_user_info(user_info)
        except Exception as e:
            raise ValueError(f"Failed to fetch DingTalk user info: {e}")

    def normalize_user_info(self, user_info):
        """
        标准化钉钉用户信息。
        钉钉返回字段：nick, unionid, openid, avatar_url, email
        """
        # 钉钉可能返回不同的字段名，我们尝试多个可能的字段
        email = user_info.get("email") or user_info.get("emailAddress")

        # 使用 nick 作为昵称，没有则使用其他字段
        nickname = user_info.get("nick") or user_info.get("name") or user_info.get("nickName")

        # 用户名可以使用邮箱前缀或钉钉ID
        username = user_info.get("openid") or user_info.get("unionid")
        if not username and email:
            username = str(email).split("@")[0]

        avatar_url = user_info.get("avatar_url") or user_info.get("avatarUrl") or user_info.get("avatar")

        return UserInfo(
            email=email,
            username=username or "dingtalk_user",
            nickname=nickname or username or "钉钉用户",
            avatar_url=avatar_url or ""
        )