import aiohttp
import logging
from typing import Dict, List, Optional, Any

_LOGGER = logging.getLogger(__name__)

class SurgeAPIClient:
    def __init__(self, host: str, port: int, api_key: str, session: aiohttp.ClientSession, use_https: bool = False, verify_ssl: bool = True):
        self._host = host
        self._port = port
        self._api_key = api_key
        self._session = session
        self._use_https = use_https
        self._verify_ssl = verify_ssl
        # 新增：根据 use_https 选择协议前缀
        scheme = "https" if use_https else "http"
        self._base_url = f"{scheme}://{host}:{port}/v1"
        self._headers = {"X-Key": api_key, "Accept": "application/json"}

    async def _request(
        self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """通用请求封装（新增：HTTPS 证书验证）"""
        url = f"{self._base_url}/{endpoint.lstrip('/')}"
        try:
            async with self._session.request(
                method, url, headers=self._headers, json=data, params=params,
                verify=self._verify_ssl  # 新增：SSL 证书验证开关
            ) as response:
                if response.status == 401:
                    _LOGGER.error("Surge API 认证失败（无效 X-Key）")
                    raise ValueError("Invalid API Key")
                if response.status >= 500:
                    _LOGGER.error(f"Surge API 服务器错误（状态码：{response.status}）")
                    raise ConnectionError(f"Server error: {response.status}")
                
                response_data = await response.json()
                _LOGGER.debug(f"API 响应（{endpoint}）: {response_data}")
                return response_data

        except aiohttp.ClientConnectionError:
            _LOGGER.error(f"无法连接 Surge（地址：{self._host}:{self._port}）")
            raise ConnectionError("Could not connect to Surge")
        except Exception as e:
            _LOGGER.error(f"API 请求失败（{endpoint}）: {str(e)}")
            raise

    # ------------------------------ 新增：策略组接口 ------------------------------
    async def get_policy_groups(self) -> List[str]:
        """获取所有策略组名称"""
        data = await self._request("GET", "policy_groups")
        return data.get("groups", [])  # 响应格式：{"groups": ["Proxy", "Direct", "Rule"]}

    async def get_policy_group_current_policy(self, group_name: str) -> Optional[str]:
        """获取指定策略组的当前生效策略"""
        data = await self._request("GET", f"policy_groups/{group_name}")
        return data.get("current", "Unknown Policy")

    async def get_policy_group_policies(self, group_name: str) -> List[str]:
        """获取指定策略组的所有可用策略"""
        data = await self._request("GET", f"policy_groups/{group_name}")
        return data.get("policies", [])  # 响应格式：{"current": "Node1", "policies": ["Node1", "Node2"]}

    async def set_policy_group_policy(self, group_name: str, policy_name: str) -> None:
        """切换指定策略组的生效策略"""
        await self._request(
            "POST", f"policy_groups/{group_name}/select",
            data={"policy": policy_name}
        )

    # ------------------------------ 新增：出站模式接口（补充完整） ------------------------------
    async def get_outbound_mode(self) -> str:
        """获取当前出站模式（direct/proxy/rule）"""
        data = await self._request("GET", "outbound")
        return data.get("mode", "unknown")

    async def set_outbound_mode(self, mode: str) -> None:
        """设置出站模式（仅支持 direct/proxy/rule）"""
        if mode not in ["direct", "proxy", "rule"]:
            raise ValueError(f"无效出站模式：{mode}（仅支持 direct/proxy/rule）")
        await self._request("POST", "outbound", data={"mode": mode})

    # ------------------------------ 原有功能保持不变 ------------------------------
    async def get_profiles(self) -> List[str]:
        data = await self._request("GET", "profiles")
        return data.get("profiles", [])

    async def get_current_profile(self) -> Optional[str]:
        data = await self._request("GET", "profiles/current", params={"sensitive": 0})
        return data.get("profile_name") or "Unknown Profile"

    async def switch_profile(self, profile_name: str) -> None:
        await self._request("POST", "profiles/switch", data={"name": profile_name})

    async def reload_profile(self) -> None:
        await self._request("POST", "profiles/reload")

    async def get_feature_status(self, feature: str) -> bool:
        data = await self._request("GET", f"features/{feature}")
        return data.get("enabled", False)

    async def set_feature_status(self, feature: str, enabled: bool) -> None:
        await self._request("POST", f"features/{feature}", data={"enabled": enabled})

    async def get_traffic(self) -> Dict[str, float]:
        data = await self._request("GET", "traffic")
        return {
            "upload": round(data.get("upload", 0) / 1024, 2),
            "download": round(data.get("download", 0) / 1024, 2),
            "total": round((data.get("upload", 0) + data.get("download", 0)) / 1024, 2)
        }
