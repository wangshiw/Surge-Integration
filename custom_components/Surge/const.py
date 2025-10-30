"""Surge Integration 常量定义"""

# 组件域名
DOMAIN = "surge"

# 配置字段（与UI表单对应）
CONF_HOST = "host"  # Surge设备IP
CONF_PORT = "port"  # API端口（默认6171）
CONF_API_KEY = "api_key"  # Surge HTTP-API Key
CONF_USE_HTTPS = "use_https"  # 是否启用HTTPS（默认false）
CONF_VERIFY_SSL = "verify_ssl"  # 是否验证SSL（默认true）
CONF_UPDATE_INTERVAL = "update_interval"  # 刷新间隔（默认30秒）

# 默认配置值
DEFAULT_PORT = 6171
DEFAULT_UPDATE_INTERVAL = 30
DEFAULT_USE_HTTPS = False
DEFAULT_VERIFY_SSL = True

# 实体相关常量
DEVICE_MANUFACTURER = "Surge"
DEVICE_MODEL = "Surge Mac/iOS"
DEVICE_NAME = "Surge Controller"
