"""Surge HTTP API 客户端（适配Config Flow）"""

import aiohttp
import logging
from typing import Dict, List, Optional, Any

from homeassistant.exceptions import HomeAssistantError

from .const import DEFAULT_PORT

_LOGGER = logging.getLogger(__name__)


class SurgeAPIError(HomeAssistantError):
    """Surge API请求异常基类（供Config Flow捕获）"""


class SurgeAPIClient:
    def __init__(
        self,
        host: str,
        port: int = DEFAULT_PORT,
        api_key: str = "",
        session: aiohttp.ClientSession = None,
        use_https: bool = False,
        verify_ssl: bool = True,
    ):
        self._host = host
        self._port = port
        self._api_key = api_key
        self._session = session or aiohttp.ClientSession()
        self._use_https = use_https
        self._verify_ssl = verify_ssl  # 控制SSL证书验证
        self._base_url = self._get_base_url()
        self._headers = {"X-Key": self._api_key, "Accept": "application/json"}

    def _get_base_url(self) -> str:
        """生成API基础URL（根据HTTPS配置切换协议）"""
        scheme = "https" if self._use_https else "http"
        return f"{scheme}://{self._host}:{self._port}/v1"

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """通用API请求封装（含错误处理）"""
        url = f"{self._base_url}/{endpoint.lstrip('/')}"
        try:
            async with self._session.request(
                method,
                url,
                headers=self._headers,
                json=data,
                params=params,
                verify=self._verify_ssl,  # 传入SSL验证配置
            ) as response:
                # 处理HTTP状态码
                if response.status == 401:
                    _LOGGER.error("Surge API 认证失败（无效X-Key）")
                    raise ValueError("Invalid API Key")  # 会被Config Flow转为InvalidAuth
                if response.status >= 500:
                    _LOGGER.error(f"Surge API 服务器错误（状态码：{response.status}）")
                    raise SurgeAPIError(f"Server error: {response.status}")
                if 400 <= response.status < 500:
                    _LOGGER.error(f"Surge API 请求参数错误（状态码：{response.status}）")
                    raise SurgeAPIError(f"Bad request: {response.status}")

                # 解析响应（处理非JSON响应）
                try:
                    return await response.json()
                except aiohttp.ContentTypeError:
                    _LOGGER.error("Surge API 返回非JSON数据")
                    raise SurgeAPIError("Invalid API response (not JSON)")

        except aiohttp.ClientConnectionError as exc:
            _LOGGER.error(f"无法连接Surge设备（{self._host}:{self._port}）")
            raise ConnectionError from exc  # 会被Config Flow转为CannotConnect
        except Exception as exc:
            _LOGGER.error(f"API请求失败（{endpoint}）: {str(exc)}")
            raise SurgeAPIError from exc

    # ------------------------------ 配置管理 ------------------------------
    async def get_profiles(self) -> List[str]:
        """获取所有可用配置名称"""
        data = await self._request("GET", "profiles")
        return data.get("profiles", [])

    async def get_current_profile(self) -> Optional[str]:
        """获取当前活跃配置名称"""
        data = await self._request("GET", "profiles/current", params={"sensitive": 0})
        return data.get("profile_name") or "Unknown Profile"

    async def switch_profile(self, profile_name: str) -> None:
        """切换到指定配置"""
        await self._request("POST", "profiles/switch", data={"name": profile_name})

    async def reload_profile(self) -> None:
        """重新加载当前配置"""
        await self._request("POST", "profiles/reload")

    # ------------------------------ 功能开关 ------------------------------
    async def get_feature_status(self, feature: str) -> bool:
        """获取指定功能的启用状态（如mitm、capture）"""
        data = await self._request("GET", f"features/{feature}")
        return data.get("enabled", False)

    async def set_feature_status(self, feature: str, enabled: bool) -> None:
        """设置指定功能的启用状态"""
        await self._request("POST", f"features/{feature}", data={"enabled": enabled})

    # ------------------------------ 流量监控 ------------------------------
    async def get_traffic(self) -> Dict[str, float]:
        """获取当前流量（上传/下载，单位：MB）"""
        data = await self._request("GET", "traffic")
        return {
            "upload": round(data.get("upload", 0) / 1024, 2),
            "download": round(data.get("download", 0) / 1024, 2),
            "total": round((data.get("upload", 0) + data.get("download", 0)) / 1024, 2),
        }

    # ------------------------------ 出站模式 ------------------------------
    async def get_outbound_mode(self) -> str:
        """获取当前出站模式（direct/proxy/rule）"""
        data = await self._request("GET", "outbound")
        return data.get("mode", "unknown")

    async def set_outbound_mode(self, mode: str) -> None:
        """设置出站模式（仅支持direct/proxy/rule）"""
        if mode not in ["direct", "proxy", "rule"]:
            raise SurgeAPIError(f"无效出站模式：{mode}（仅支持direct/proxy/rule）")
        await self._request("POST", "outbound", data={"mode": mode})

    # ------------------------------ 策略组控制 ------------------------------
    async def get_policy_groups(self) -> List[str]:
        """获取所有策略组名称"""
        data = await self._request("GET", "policy_groups")
        return data.get("groups", [])

    async def get_policy_group_current_policy(self, group_name: str) -> Optional[str]:
        """获取指定策略组的当前生效策略"""
        data = await self._request("GET", f"policy_groups/{group_name}")
        return data.get("current", "Unknown Policy")

    async def get_policy_group_policies(self, group_name: str) -> List[str]:
        """获取指定策略组的所有可用策略"""
        data = await self._request("GET", f"policy_groups/{group_name}")
        return data.get("policies", [])

    async def set_policy_group_policy(self, group_name: str, policy_name: str) -> None:
        """切换指定策略组的生效策略"""
        await self._request(
            "POST", f"policy_groups/{group_name}/select", data={"policy": policy_name}
        )
