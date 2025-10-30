import logging
from typing import Dict, Any
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .surge_api import SurgeAPIClient
from .select import SurgeProfileSelect, SurgeOutboundSelect, SurgePolicyGroupSelect
from .switch import SurgeFeatureSwitch
from .sensor import SurgeTrafficSensor

_LOGGER = logging.getLogger(__name__)

DOMAIN = "surge"

# ------------------------------ 新增：HTTPS/SSL 配置字段 ------------------------------
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required("host"): cv.string,
                vol.Required("port"): cv.port,
                vol.Required("api_key"): cv.string,
                vol.Optional("features", default=["mitm", "capture", "rewrite", "scripting"]): cv.ensure_list,
                vol.Optional("mac_features", default=["system_proxy", "enhanced_mode"]): cv.ensure_list,
                vol.Optional("update_interval", default=30): cv.positive_int,
                vol.Optional("use_https", default=False): cv.boolean,  # 新增：是否启用 HTTPS
                vol.Optional("verify_ssl", default=True): cv.boolean   # 新增：是否验证 SSL 证书
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

API_CLIENT = "api_client"
UPDATE_INTERVAL = "update_interval"

async def async_setup(
    hass: HomeAssistant, config: ConfigType
) -> bool:
    if DOMAIN not in config:
        return True

    # 读取用户配置（新增：use_https 和 verify_ssl）
    surge_config = config[DOMAIN]
    host = surge_config["host"]
    port = surge_config["port"]
    api_key = surge_config["api_key"]
    features = surge_config["features"]
    mac_features = surge_config["mac_features"]
    update_interval = surge_config["update_interval"]
    use_https = surge_config["use_https"]  # 新增
    verify_ssl = surge_config["verify_ssl"]  # 新增

    # 创建 API 客户端（新增：传入 HTTPS/SSL 参数）
    session = async_get_clientsession(hass)
    try:
        api_client = SurgeAPIClient(
            host, port, api_key, session,
            use_https=use_https, verify_ssl=verify_ssl
        )
        await api_client.get_profiles()  # 测试连接
    except Exception as e:
        _LOGGER.error(f"初始化 Surge API 客户端失败：{str(e)}")
        return False

    # 存储全局数据（新增：HTTPS 配置）
    hass.data[DOMAIN] = {
        API_CLIENT: api_client,
        UPDATE_INTERVAL: update_interval,
        "features": features,
        "mac_features": mac_features,
        "use_https": use_https,
        "verify_ssl": verify_ssl
    }

    # ------------------------------ 新增：动态注册策略组实体 ------------------------------
    async def async_setup_entities(
        hass: HomeAssistant,
        config: ConfigType,
        async_add_entities: AddEntitiesCallback,
        discovery_info: DiscoveryInfoType = None,
    ):
        api = hass.data[DOMAIN][API_CLIENT]
        interval = hass.data[DOMAIN][UPDATE_INTERVAL]
        entities = []

        # 1. 原有实体：配置选择、出站模式、功能开关、流量传感器
        entities.append(SurgeProfileSelect(api, interval))
        entities.append(SurgeOutboundSelect(api, interval))  # 新增：出站模式实体

        for feature in hass.data[DOMAIN]["features"]:
            entities.append(SurgeFeatureSwitch(api, feature, interval))
        for feature in hass.data[DOMAIN]["mac_features"]:
            entities.append(SurgeFeatureSwitch(api, feature, interval, is_mac_only=True))
        entities.append(SurgeTrafficSensor(api, interval))

        # 2. 新增：动态创建策略组实体（获取所有策略组，每个组对应一个实体）
        try:
            policy_groups = await api.get_policy_groups()
            for group in policy_groups:
                entities.append(SurgePolicyGroupSelect(api, interval, group))
            _LOGGER.info(f"成功加载 {len(policy_groups)} 个策略组实体")
        except Exception as e:
            _LOGGER.warning(f"加载策略组实体失败：{str(e)}（可能 Surge 版本不支持）")

        async_add_entities(entities, update_before_add=True)

    # 注册所有实体平台
    hass.helpers.discovery.async_load_platform("select", DOMAIN, {}, async_setup_entities)
    hass.helpers.discovery.async_load_platform("switch", DOMAIN, {}, async_setup_entities)
    hass.helpers.discovery.async_load_platform("sensor", DOMAIN, {}, async_setup_entities)

    _LOGGER.info("Surge 组件（含扩展功能）初始化成功")
    return True
