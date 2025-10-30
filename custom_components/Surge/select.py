from typing import Dict, Optional, List
import logging
from homeassistant.components.select import SelectEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.entity import DeviceInfo

from .surge_api import SurgeAPIClient
from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

# ------------------------------ 原有：配置选择实体 ------------------------------
class SurgeProfileSelect(SelectEntity):
    def __init__(self, api: SurgeAPIClient, update_interval: int):
        self._api = api
        self._update_interval = update_interval
        self._options = []
        self._current_option = None
        self._attr_unique_id = f"{DOMAIN}_profile_select"
        self._attr_name = "Surge 活跃配置"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{self._api._host}:{self._api._port}")},
            name="Surge 控制器",
            model="Surge Mac/iOS",
            manufacturer="Surge"
        )

        self._coordinator = DataUpdateCoordinator(
            self.hass, _LOGGER, name=self._attr_name,
            update_method=self._async_update_data, update_interval=update_interval
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        await self._coordinator.async_config_entry_first_refresh()

    async def _async_update_data(self) -> None:
        try:
            self._options = await self._api.get_profiles()
            self._current_option = await self._api.get_current_profile()
        except Exception as e:
            _LOGGER.error(f"更新配置列表失败：{str(e)}")
            self._attr_available = False
        else:
            self._attr_available = True

    @property
    def options(self) -> list[str]:
        return self._options

    @property
    def current_option(self) -> Optional[str]:
        return self._current_option

    async def async_select_option(self, option: str) -> None:
        try:
            await self._api.switch_profile(option)
            await self._coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error(f"切换配置 {option} 失败：{str(e)}")

    @property
    def available(self) -> bool:
        return self._attr_available

# ------------------------------ 新增：出站模式选择实体 ------------------------------
class SurgeOutboundSelect(SelectEntity):
    def __init__(self, api: SurgeAPIClient, update_interval: int):
        self._api = api
        self._update_interval = update_interval
        self._options = ["direct", "proxy", "rule"]  # 固定出站模式选项
        self._current_option = None
        self._attr_unique_id = f"{DOMAIN}_outbound_select"
        self._attr_name = "Surge 出站模式"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{self._api._host}:{self._api._port}")},
            name="Surge 控制器",
            model="Surge Mac/iOS",
            manufacturer="Surge"
        )

        self._coordinator = DataUpdateCoordinator(
            self.hass, _LOGGER, name=self._attr_name,
            update_method=self._async_update_data, update_interval=update_interval
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        await self._coordinator.async_config_entry_first_refresh()

    async def _async_update_data(self) -> None:
        try:
            self._current_option = await self._api.get_outbound_mode()
        except Exception as e:
            _LOGGER.error(f"更新出站模式失败：{str(e)}")
            self._attr_available = False
        else:
            self._attr_available = True

    @property
    def options(self) -> list[str]:
        return self._options

    @property
    def current_option(self) -> Optional[str]:
        return self._current_option

    async def async_select_option(self, option: str) -> None:
        try:
            await self._api.set_outbound_mode(option)
            await self._coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error(f"切换出站模式 {option} 失败：{str(e)}")

    @property
    def available(self) -> bool:
        return self._attr_available

# ------------------------------ 新增：策略组选择实体（动态创建） ------------------------------
class SurgePolicyGroupSelect(SelectEntity):
    def __init__(self, api: SurgeAPIClient, update_interval: int, group_name: str):
        self._api = api
        self._update_interval = update_interval
        self._group_name = group_name  # 当前策略组名称（如 "Proxy"）
        self._options = []  # 该策略组的所有可用策略
        self._current_option = None
        self._attr_unique_id = f"{DOMAIN}_policy_group_{group_name.lower().replace(' ', '_')}"
        self._attr_name = f"Surge 策略组 - {group_name}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{self._api._host}:{self._api._port}")},
            name="Surge 控制器",
            model="Surge Mac/iOS",
            manufacturer="Surge"
        )

        self._coordinator = DataUpdateCoordinator(
            self.hass, _LOGGER, name=self._attr_name,
            update_method=self._async_update_data, update_interval=update_interval
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        await self._coordinator.async_config_entry_first_refresh()

    async def _async_update_data(self) -> None:
        try:
            # 获取该策略组的可用策略和当前策略
            self._options = await self._api.get_policy_group_policies(self._group_name)
            self._current_option = await self._api.get_policy_group_current_policy(self._group_name)
        except Exception as e:
            _LOGGER.error(f"更新策略组 {self._group_name} 失败：{str(e)}")
            self._attr_available = False
        else:
            self._attr_available = True

    @property
    def options(self) -> list[str]:
        return self._options

    @property
    def current_option(self) -> Optional[str]:
        return self._current_option

    async def async_select_option(self, option: str) -> None:
        try:
            await self._api.set_policy_group_policy(self._group_name, option)
            await self._coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error(f"策略组 {self._group_name} 切换到 {option} 失败：{str(e)}")

    @property
    def available(self) -> bool:
        return self._attr_available
