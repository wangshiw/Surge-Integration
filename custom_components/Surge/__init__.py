"""Surge Integration 初始化（适配Config Flow）"""

import logging
from typing import Dict, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_PORT,
    CONF_UPDATE_INTERVAL,
    CONF_USE_HTTPS,
    CONF_VERIFY_SSL,
    DOMAIN,
    DEVICE_MANUFACTURER,
    DEVICE_MODEL,
    DEVICE_NAME,
)
from .surge_api import SurgeAPIClient, SurgeAPIError

_LOGGER = logging.getLogger(__name__)

# 全局存储键（用于传递API客户端和配置）
API_CLIENT = "api_client"
UPDATE_COORDINATOR = "update_coordinator"


async def async_setup(hass: HomeAssistant, config: Dict[str, Any]) -> bool:
    """废弃：原yaml配置入口，现在通过Config Flow初始化"""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """从Config Entry初始化组件（核心入口）"""
    # 1. 从Config Entry获取用户配置
    config_data = entry.data
    host = config_data[CONF_HOST]
    port = config_data[CONF_PORT]
    api_key = config_data[CONF_API_KEY]
    use_https = config_data[CONF_USE_HTTPS]
    verify_ssl = config_data[CONF_VERIFY_SSL]
    update_interval = config_data[CONF_UPDATE_INTERVAL]

    # 2. 初始化API客户端
    session = async_get_clientsession(hass)
    try:
        api_client = SurgeAPIClient(
            host=host,
            port=port,
            api_key=api_key,
            session=session,
            use_https=use_https,
            verify_ssl=verify_ssl,
        )
        # 测试API连接（确保配置有效）
        await api_client.get_profiles()
    except Exception as exc:
        _LOGGER.error(f"初始化Surge API客户端失败: {str(exc)}")
        return False

    # 3. 创建全局数据存储（供其他平台使用）
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    hass.data[DOMAIN][entry.entry_id] = {
        API_CLIENT: api_client,
    }

    # 4. 注册实体平台（select/switch/sensor）
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setups(entry, ["select", "switch", "sensor"])
    )

    # 5. 监听配置更新（如需支持修改配置）
    entry.async_on_unload(entry.add_update_listener(async_update_entry))

    _LOGGER.info(f"Surge组件初始化成功（设备：{host}:{port}）")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """卸载配置项（清理资源）"""
    # 卸载所有平台实体
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["select", "switch", "sensor"])
    # 删除全局存储的API客户端
    if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
        del hass.data[DOMAIN][entry.entry_id]
    # 若没有其他配置项，删除整个DOMAIN存储
    if not hass.data[DOMAIN]:
        del hass.data[DOMAIN]
    return unload_ok


async def async_update_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """配置项更新时重新初始化（暂不实现，如需修改配置可扩展）"""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


# ------------------------------ 通用实体工具函数 ------------------------------
def get_common_device_info(entry: ConfigEntry) -> Dict[str, Any]:
    """获取统一的设备信息（所有实体共享，确保在HA中显示为同一设备）"""
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    return {
        "identifiers": {(DOMAIN, f"{entry.entry_id}_{host}_{port}")},  # 唯一设备标识
        "name": DEVICE_NAME,
        "manufacturer": DEVICE_MANUFACTURER,
        "model": DEVICE_MODEL,
        "sw_version": "1.1.0",  # 组件版本
        "configuration_url": f"http://{host}:{port}" if not entry.data[CONF_USE_HTTPS] else f"https://{host}:{port}",
    }
