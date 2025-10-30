# Surge-Integration   HomeAssistant集成

Home Assistant 配置步骤

1.编辑 config.yaml在 Home Assistant 的 config.yaml 中添加以下配置（根据实际环境修改参数）

surge:
  host: 192.168.1.100  # Surge 设备的局域网 IP（如 Mac 的 IP）
  port: 6171            # Surge 配置中 http-api 的端口（默认 6171）
  api_key: examplekey   # Surge 配置中 http-api 的 key（如 examplekey@0.0.0.0:6171 中的 examplekey）
  features:             # 要控制的通用功能（iOS/Mac 均支持）
    - mitm
    - capture
    - rewrite
    - scripting
  mac_features:         # 要控制的 Mac 专属功能
    - system_proxy
    - enhanced_mode
  update_interval: 30   # 状态刷新间隔（秒）
2.重启 Home Assistant 使组件生效。
3.添加实体到仪表盘
  在 Home Assistant 仪表盘（Dashboard）中添加以下实体：
  选择框：select.surge_active_profile（切换 Surge 配置）
  开关：switch.surge_mitm、switch.surge_system_proxy 等（控制功能）
  传感器：sensor.surge_total_traffic（查看流量）
