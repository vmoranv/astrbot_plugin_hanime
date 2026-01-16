# Hanime1.me AstrBot 插件

一个用于查询 hanime1.me 视频信息的 AstrBot 插件。

## 功能特性

- 🔍 **视频搜索** - 支持关键词搜索视频
- 📺 **视频详情** - 获取视频的详细信息（标题、观看数、时长、标签等）
- 🏷️ **标签筛选** - 按标签/分类浏览视频
- 🆕 **最新视频** - 获取最新上传的视频
- 🔥 **热门视频** - 获取最受欢迎的视频
- 🎲 **随机视频** - 随机获取一个视频
- 🔗 **相关视频** - 查看与指定视频相关的推荐

## 命令列表

| 命令 | 说明 | 示例 |
|------|------|------|
| `/hv <ID>` | 获取视频详细信息 | `/hv 12345` |
| `/hs <关键词> [页码]` | 搜索视频 | `/hs 中文字幕` 或 `/hs 中文字幕 2` |
| `/htag <标签> [页码]` | 按标签查询视频 | `/htag NTR` 或 `/htag NTR 2` |
| `/hlatest [页码]` | 获取最新视频 | `/hlatest` 或 `/hlatest 2` |
| `/hpopular [页码]` | 获取热门视频 | `/hpopular` 或 `/hpopular 2` |
| `/hrandom` | 获取随机视频 | `/hrandom` |
| `/hrelated <ID>` | 获取相关视频 | `/hrelated 12345` |
| `/htags <ID>` | 获取视频标签 | `/htags 12345` |
| `/hcategories` | 显示所有分类 | `/hcategories` |

## 配置说明

在 AstrBot 管理面板中可配置以下选项：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `proxy` | 代理服务器地址 | 空（不使用代理） |
| `blur_level` | 缩略图模糊程度 (0-100) | 0（不模糊） |
| `max_search_results` | 搜索结果最大显示数量 | 10 |

### 代理配置示例

```
http://127.0.0.1:7890
socks5://127.0.0.1:1080
```

## 安装

1. 将插件目录放入 AstrBot 的 `data/plugins/` 目录
2. 在 AstrBot 管理面板中启用插件
3. 根据需要配置代理和其他选项

## 依赖

- aiohttp >= 3.8.0
- Pillow >= 9.0.0

## 注意事项

- 本插件仅用于信息查询，不提供下载功能
- 请遵守当地法律法规使用本插件
- 建议在需要时配置代理以确保访问稳定性
- 缩略图会在发送后自动清理缓存

## 目录结构

```
astrbot_plugin_hanime/
├── main.py              # 插件主文件
├── metadata.yaml        # 插件元数据
├── requirements.txt     # 依赖列表
├── _conf_schema.json    # 配置模式
├── README.md            # 说明文档
└── modules/             # 核心模块
    ├── __init__.py
    ├── consts.py        # 常量定义
    ├── utils.py         # 工具函数
    ├── video.py         # Video 类
    └── client.py        # Client 客户端
```

## License

MIT License
