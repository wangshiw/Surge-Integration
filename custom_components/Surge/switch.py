"""Surge 功能开关实体（适配Config Flow）"""

import logging
from typing import List, Dict

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DOMAIN,
    API_CLIENT,
    CONF_UPDATE_INTERVAL,
    DEVICE_MANUFACTURER,
    DEVICE_MODEL,
    DEVICE_NAME,
)
from .__init__ import get_common_device_info
from .surge_api import SurgeAPIClient, SurgeAPIError

_LOGGER = logging.getLogger(__name__)

# 支持的功能开关（通用+Mac专属）
SUPPORTED_FEATURES = ["mitm", "capture", "rewrite", "scripting"]
MAC_ONLY_FEATURES = ["system_proxy", "enhanced_mode"]


class SurgeFeatureSwitch(SwitchEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api_client: SurgeAPIClient,
        update_interval: int,
        feature: str,
        is_mac_only: bool = False,
    ):
        self.hass = hass
        self.entry = entry
        self._api_client = api_client
        self._update_interval = update_interval
        self._feature = feature  # 功能名称（如mitm、system_proxy）
        self._is_mac_only = is_mac_only  # 是否为Mac专属功能

        # 实体基础属性
        self._attr_unique_id = f"{entry.entry_id}_feature_{feature}"
        self._attr_name = f"Surge {feature.replace('_', ' ').title()}"  # 显示名称（如"Surge System Proxy"）
        self._attr_device_info = get_common_device_info(entry)  # 统一设备信息
        self._attr_is_on = False  # 初始状态：关闭
        self._attr_available = True

        # 初始化更新协调器
        self._coordinator = DataUpdateCoordinator(
            self.hass,
            _LOGGER,
            name=self._attr_name,
            update_method=self._async_update_data,
            update_interval=self._update_interval,
        )

    async def async_added_to_hass(self) -> None:
        """实体添加到HA时启动协调器"""
        await super().async_added_to_hass()
        await self._coordinator.async_config_entry_first_refresh()

    async def _async_update_data(self) -> None:
        """从API刷新功能状态"""
        try:
            self._attr_is_on = await self._api_client.get_feature_status(self._feature)
        except ConnectionError:
            _LOGGER.warning(f"无法连接Surge设备（功能：{self._feature}）")
            self._attr_available = False
        except Exception as exc:
            # Mac专属功能在非Mac设备上会返回404，特殊处理
            if self._is_mac_only and "404" in str(exc):
                _LOGGER.warning(f"Mac专属功能{self._feature}在当前设备不支持")
            else:
                _LOGGER.error(f"更新{self._feature}状态失败: {str(exc)}")
            self._attr_available = False
        else:
            self._attr_available = True

    async def async_turn_on(self, **kwargs) -> None:
        """启用功能"""
        try:
            await self._api_client.set_feature_status(self._feature, True)
            await self._coordinator.async_request_refresh()  # 立即刷新状态
        except Exception as exc:
            _LOGGER.error(f"启用{self._feature}失败: {str(exc)}")

    async def async_turn_off(self, **kwargs) -> None:
        """禁用功能"""
        try:
            await self._api_client.set_feature_status(self._feature, False)
            await self._coordinator.async_request_refresh()
        except Exception as exc:
            _LOGGER.error(f"禁用{self._feature}失败: {str(exc)}")

    @property
    def is_on(self) -> bool:
        """返回当前开关状态"""
        return self._attr_is_on

    @property
    def available(self) -> bool:
        """返回实体是否可用"""
        return self._attr_available


# ------------------------------ 平台注册入口 ------------------------------
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """从Config Entry注册功能开关实体"""
    # 从全局存储获取API客户端
    domain_data = hass.data[DOMAIN][entry.entry_id]
    api_client = domain_data[API_CLIENT]
    update_interval = entry.data[CONF_UPDATE_INTERVAL]

    entities = []

    # 1. 添加通用功能开关（iOS/Mac均支持）
    for feature in SUPPORTED_FEATURES:
        entities.append(
            SurgeFeatureSwitch(hass, entry, api_client, update_interval, feature)
        )

    # 2. 添加Mac专属功能开关
    for feature in MAC_ONLY_FEATURES:
        entities.append(
            SurgeFeatureSwitch(
                hass, entry, api_client, update_interval, feature, is_mac_only=True
            )
        )

    # 注册所有开关实体
    async_add_entities(entities, update_before_add=True)
