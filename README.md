<div align="center">

# ForgeRSS

### 将任意网站转换为 RSS 订阅源 | 多引擎抓取 + 反爬突破 + 社交媒体支持 | 完全开源免费

**完全开源 | 免费使用 | 自动更新 | 多引擎抓取 | 政府网站反爬突破 | Docker 支持**

[![GitHub stars](https://img.shields.io/github/stars/tmwgsicp/ForgeRSS?style=for-the-badge&logo=github)](https://github.com/tmwgsicp/ForgeRSS/stargazers)
[![License](https://img.shields.io/badge/License-AGPL%203.0-blue?style=for-the-badge)](LICENSE)
[![Docker Pulls](https://img.shields.io/docker/pulls/tmwgsicp/forgerss?style=for-the-badge&logo=docker&logoColor=white)](https://hub.docker.com/r/tmwgsicp/forgerss)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)

> **100% 开源，100% 免费。** 代码完全公开，私有化部署无任何限制，不搞"开源"之名行收费之实。

</div>

---

## 功能特性

- **多引擎抓取** — curl_cffi + Selenium + DrissionPage，自动选择最优方案
- **政府网站反爬突破** — 支持绕过瑞数信息等商用反爬系统（需桌面环境）
- **智能去重** — 基于 URL 哈希，避免重复文章
- **双存储方案** — JSON 缓存 (GitHub 托管) + SQLite (本地/Docker)
- **标准 RSS 2.0** — CDATA 包裹 + 内联样式，兼容 Readwise、FreshRSS 等阅读器
- **GitHub Actions** — 每 6 小时自动更新，零运维
- **Docker 支持** — 一键部署，适合自托管

---

## 可用 RSS 订阅源

以下是已部署的 RSS 源，可直接在 RSS 阅读器中订阅：

| 信息源 | 订阅链接 |
|--------|----------|
| **Anthropic News** | [订阅](https://cdn.jsdelivr.net/gh/tmwgsicp/ForgeRSS@main/feeds/feed_anthropic_news.xml) |
| **Anthropic Research** | [订阅](https://cdn.jsdelivr.net/gh/tmwgsicp/ForgeRSS@main/feeds/feed_anthropic_research.xml) |
| **Anthropic Engineering** | [订阅](https://cdn.jsdelivr.net/gh/tmwgsicp/ForgeRSS@main/feeds/feed_anthropic_engineering.xml) |
| **OpenAI Research** | [订阅](https://cdn.jsdelivr.net/gh/tmwgsicp/ForgeRSS@main/feeds/feed_openai_research.xml) |
| **IDSociety Science Speaks** | [订阅](https://cdn.jsdelivr.net/gh/tmwgsicp/ForgeRSS@main/feeds/feed_idsociety.xml) |
| **国家药监局药品公告** | 需本地运行（见下方说明） |
| **知乎热榜** | 需本地运行（见下方说明） |
| **知乎用户动态** | 需本地运行（见下方说明） |

> Feed 每 6 小时自动更新，包含完整文章内容。使用 jsDelivr CDN 托管，兼容所有 RSS 阅读器。

### 详细信息源列表

| 信息源 | 分类 | 抓取方式 | Feed 文件 | 运行环境 |
|--------|------|----------|-----------|----------|
| Anthropic News | AI | curl_cffi | `feed_anthropic_news.xml` | CI/本地 |
| Anthropic Research | AI | curl_cffi | `feed_anthropic_research.xml` | CI/本地 |
| Anthropic Engineering | AI | curl_cffi | `feed_anthropic_engineering.xml` | CI/本地 |
| OpenAI Research | AI | curl_cffi | `feed_openai_research.xml` | CI/本地 |
| IDSociety Science Speaks | 医学 | Selenium | `feed_idsociety.xml` | CI/本地 |
| **国家药监局 (NMPA)** | 政府 | **DrissionPage** | `feed_nmpa_drug.xml` | **仅本地** |
| **知乎热榜** | 社交媒体 | **DrissionPage + 登录** | `feed_zhihu_hot.xml` | **仅本地** |
| **知乎用户动态** | 社交媒体 | **DrissionPage + 登录** | `feed_zhihu_user.xml` | **仅本地** |

---

## 快速使用

### 方式一：直接订阅（推荐）

复制上方订阅链接到你的 RSS 阅读器即可使用。

如需自定义，可 Fork 本项目，启用 GitHub Actions，Feed 会自动生成到 `feeds/` 目录：

```
https://cdn.jsdelivr.net/gh/你的用户名/ForgeRSS@main/feeds/feed_anthropic_news.xml
```

> 使用 jsDelivr CDN 链接可确保正确的 Content-Type，兼容 FreshRSS、Inoreader 等阅读器。

### 方式二：Docker 部署

```bash
# 方式一：使用 docker-compose（推荐）
git clone https://github.com/tmwgsicp/ForgeRSS.git
cd forgerss
docker-compose up

# 方式二：直接运行
docker run -v ./feeds:/app/feeds tmwgsicp/ForgeRSS:latest
```

### 方式三：本地运行

```bash
# 克隆项目
git clone https://github.com/tmwgsicp/ForgeRSS.git
cd forgerss

# 安装依赖
pip install -r requirements.txt

# 运行所有生成器
python scripts/run_all.py

# 运行单个生成器
python scripts/run_single.py anthropic_news --max 20

# 验证 Feed
python scripts/validate_feeds.py
```

---

## 抓取策略

### 多引擎抓取

| 方案 | 速度 | 适用场景 | 运行环境 |
|------|------|----------|----------|
| **curl_cffi** | ~5秒 | SSR/静态网站，模拟 Chrome TLS 指纹 | 任意 |
| **Selenium** | ~30秒 | 需要 JS 渲染的网站 | CI/本地 |
| **DrissionPage** | ~30秒 | 政府网站/强反爬网站（瑞数等） | **仅桌面环境** |

系统会自动选择最优方案：先尝试 curl_cffi，失败时降级到 Selenium，最后尝试 DrissionPage。

### 反爬等级 (anti_bot_level)

| 等级 | 说明 | 抓取策略 | 典型场景 |
|------|------|----------|----------|
| `0` | 普通网站 | curl_cffi → Selenium → DrissionPage | Anthropic, OpenAI |
| `1` | 中等反爬 | DrissionPage headless → headed | 部分企业网站 |
| `2` | 强反爬（瑞数等） | DrissionPage headed | 政府网站（NMPA） |
| `3+` | 需要登录态 | DrissionPage + 持久化登录 Profile | 社交媒体（知乎） |

**说明**：
- **Level 0-2** 由 `smart_fetch` 自动处理
- **Level 3+** 需要各 generator 自行实现登录逻辑（如 `zhihu_base.py`）

---

## 政府网站反爬突破方案

很多政府网站（如 NMPA 国家药监局）使用商用反爬系统（瑞数信息 RuiShu），会拦截所有自动化访问（HTTP 412）。本项目提供了专门的解决方案。

### 支持绕过的反爬系统

- **瑞数信息 (RuiShu)** — 国内政府网站常用
- **其他 JS 挑战类反爬** — 需要执行 JS 后才能访问的网站

### 技术原理

| 工具 | Headless 模式 | 非 Headless 模式 |
|------|--------------|------------------|
| Selenium | 被拦截 | 被拦截 |
| Playwright | 被拦截 | 被拦截 |
| **DrissionPage** | 被拦截 | **可以绕过** |

DrissionPage 使用 CDP 协议直接控制 Chrome，伪装更彻底，配合以下措施可绕过瑞数：
1. **非 Headless 模式** — 必须有真实显示器或虚拟显示
2. **干净的浏览器 Profile** — 每次请求使用新的临时 Profile
3. **反检测 JS 注入** — 隐藏 `navigator.webdriver` 等特征

### 运行环境要求

由于必须使用非 Headless 模式，政府网站抓取**无法在 GitHub Actions 等 CI 环境运行**。

| 环境 | 是否支持 | 说明 |
|------|---------|------|
| Windows 桌面 | 支持 | 推荐，直接运行 |
| Windows Server + RDP | 支持 | 需保持桌面会话 |
| Linux + 桌面环境 | 支持 | GNOME/KDE + VNC |
| Linux + Xvfb | 可能不支持 | 虚拟显示可能被检测 |
| Docker / CI | 不支持 | 无真实显示器 |

### 使用方式

```bash
# 运行 NMPA 药品公告抓取（需桌面环境）
python scripts/run_single.py nmpa_drug --max 30

# 或直接调用，支持翻页
python generators/medical/nmpa_drug.py --max 30 --pages 2 --full
```

### 定时运行建议

1. **Windows 任务计划程序** — 每天定时运行，生成后推送到 GitHub
2. **本地 cron** — Linux 桌面环境下配置定时任务
3. **手动运行** — 需要更新时手动执行

```bash
# 运行后推送到 GitHub
python scripts/run_single.py nmpa_drug --max 50
git add feeds/ cache/
git commit -m "chore: update NMPA feed"
git push
```

### 添加新的政府网站源

```python
from generators.base import Article, BaseFeedGenerator
from generators.utils import smart_fetch

class MyGovGenerator(BaseFeedGenerator):
    FEED_NAME = "my_gov"
    FEED_TITLE = "某政府网站"
    FEED_URL = "https://www.example.gov.cn/news/"
    
    # 设置反爬等级为 2（强反爬）
    ANTI_BOT_LEVEL = 2
    CONTENT_CHECK = "/news/"  # 验证抓取成功的字符串
    
    def fetch_articles(self) -> list[Article]:
        html = smart_fetch(
            self.FEED_URL,
            anti_bot_level=self.ANTI_BOT_LEVEL,
            content_check=self.CONTENT_CHECK,
            selenium_wait=8,
        )
        # 解析 HTML，返回 Article 列表
        ...
```

---

## 知乎内容订阅（需登录态）

知乎热榜和用户动态需要**登录态**才能访问。支持复用浏览器登录会话。

### 首次设置（登录）

```bash
# 打开浏览器，扫码登录知乎
python -m generators.social.zhihu_base --login

# 登录成功后，会话保存到 zhihu_profile/ 目录
```

### 使用方式

**知乎热榜**（抓取实时热门话题）：
```bash
# 生成热榜 RSS（最新 50 条）
python scripts/run_single.py zhihu_hot --max 50
```

**知乎用户动态**（跟踪特定用户）：
```bash
# 跟踪单个用户
python -m generators.social.zhihu_user --users excited-vczh --max 20

# 跟踪多个用户
python -m generators.social.zhihu_user --users user1 user2 user3 --max 30
```

**搜索知乎用户**（找到用户 ID）：
```bash
# 搜索用户
python -m generators.social.zhihu_user --search "人工智能"
# 返回用户列表，复制 ID 后用于 --users 参数
```

### 内容说明

- **热榜**：包含排名、标题、热度、摘要、封面图，点链接查看完整讨论
- **用户动态**：包含回答、文章、赞同等活动，前 500 字摘要

### 法律风险提示

⚠️ **重要提醒**：
- 知乎明确禁止爬取，且有法律判例（2025 年判刑 3 年）
- 本功能**仅供个人学习研究**，用户自用自担风险
- **禁止商业化使用**，禁止转卖数据
- 建议低频使用，避免触发风控

---

## 添加新信息源

1. 在 `generators/` 下创建新文件
2. 继承 `BaseFeedGenerator`
3. 实现 `fetch_articles()` 方法
4. 在 `scripts/run_all.py` 注册

### 普通网站示例

```python
from generators.base import Article, BaseFeedGenerator
from generators.utils import smart_fetch

class MyGenerator(BaseFeedGenerator):
    FEED_NAME = "my_source"
    FEED_TITLE = "My Source"
    FEED_URL = "https://example.com/blog"
    FEED_DESCRIPTION = "Example blog feed"
    
    # curl_cffi 能抓到设为 False，需要 JS 渲染设为 True
    REQUIRE_JS = False
    CONTENT_CHECK = "/blog/"  # 验证抓取成功的字符串
    
    def fetch_articles(self) -> list[Article]:
        html = smart_fetch(self.FEED_URL, require_js=self.REQUIRE_JS)
        # 解析 HTML，返回 Article 列表
        ...
```

### 政府/强反爬网站示例

```python
class MyGovGenerator(BaseFeedGenerator):
    FEED_NAME = "my_gov"
    FEED_TITLE = "某政府网站"
    FEED_URL = "https://www.example.gov.cn/news/"
    
    ANTI_BOT_LEVEL = 2  # 强反爬
    CONTENT_CHECK = "/news/"
    
    def fetch_articles(self) -> list[Article]:
        html = smart_fetch(
            self.FEED_URL,
            anti_bot_level=self.ANTI_BOT_LEVEL,
            content_check=self.CONTENT_CHECK,
        )
        ...
```

---

## 项目结构

```
forgerss/
├── generators/           # Feed 生成器
│   ├── base.py          # 基类（缓存、去重、RSS生成）
│   ├── utils.py         # HTTP工具（curl_cffi + Selenium + DrissionPage）
│   ├── ai/              # AI 公司信息源
│   │   ├── anthropic_news.py
│   │   ├── anthropic_research.py
│   │   ├── anthropic_engineering.py
│   │   └── openai_research.py
│   ├── medical/         # 医学/政府信息源
│   │   ├── idsociety.py
│   │   └── nmpa_drug.py  # 国家药监局（需桌面环境）
│   └── social/          # 社交媒体信息源（需登录）
│       ├── zhihu_base.py    # 知乎登录态管理
│       ├── zhihu_hot.py     # 知乎热榜
│       └── zhihu_user.py    # 知乎用户动态
├── cache/               # JSON 缓存
├── feeds/               # 生成的 RSS 文件
├── data/                # SQLite 数据库
├── scripts/             # 运行脚本
├── .github/workflows/   # GitHub Actions
├── Dockerfile           # Docker 镜像
└── docker-compose.yml   # Docker Compose
```

---

## 环境变量

复制 `.env.example` 为 `.env`：

```bash
# 日志级别
LOG_LEVEL=INFO

# 每个 Feed 最大文章数
MAX_ARTICLES=50

# 运行间隔（秒），Docker 持久运行模式
RUN_INTERVAL=21600  # 默认 6 小时
```

### GitHub Actions 配置

通过 Repository Variables 可自定义：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `MAX_ARTICLES` | 每个 Feed 最大文章数 | 50 |
| `LOG_LEVEL` | 日志级别 | INFO |

> 运行频率默认每 6 小时一次，如需调整可 Fork 后修改 `.github/workflows/generate_feeds.yml` 中的 cron 表达式

---

## 开源协议

本项目采用 **AGPL 3.0** 协议开源，**所有功能代码完整公开，私有化部署完全免费**。

| 使用场景 | 是否允许 |
|---------|---------|
| 个人学习和研究 | 允许，免费使用 |
| 企业内部使用 | 允许，免费使用 |
| 私有化部署 | 允许，免费使用 |
| 修改后对外提供网络服务 | 需开源修改后的代码 |

详见 [LICENSE](LICENSE) 文件。

### 免责声明

- 本软件按"原样"提供，不提供任何形式的担保
- 本项目仅供学习和研究目的，请遵守相关网站的服务条款
- 使用者对自己的操作承担全部责任
- 因使用本软件导致的任何损失，开发者不承担责任

---

## 参与贡献

由于个人精力有限，暂不接受代码合并请求，但非常欢迎：

- **提交 Issue** — 报告 Bug、提出功能建议、贡献新的信息源配置
- **Fork 项目** — 自由修改和定制
- **Star 支持** — 给项目点 Star，让更多人看到

---

## 联系方式

<table>
  <tr>
    <td align="center">
      <img src="assets/qrcode/wechat.jpg" width="200"><br>
      <b>个人微信</b><br>
      <em>技术交流 / 商务合作</em>
    </td>
    <td align="center">
      <img src="assets/qrcode/sponsor.jpg" width="200"><br>
      <b>赞赏支持</b><br>
      <em>开源不易，感谢支持</em>
    </td>
  </tr>
</table>

- **GitHub Issues**: [提交问题](https://github.com/tmwgsicp/ForgeRSS/issues)
- **邮箱**: creator@waytomaster.com

---

## 致谢

- [curl_cffi](https://github.com/lexiforest/curl_cffi) — 支持浏览器 TLS 指纹模拟的 HTTP 客户端
- [Selenium](https://www.selenium.dev/) — 浏览器自动化框架
- [DrissionPage](https://github.com/g1879/DrissionPage) — 强大的网页自动化工具，支持绕过多种反爬
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) — HTML 解析库
- [jsDelivr](https://www.jsdelivr.com/) — 免费 CDN 服务

---

<div align="center">

**如果觉得项目有用，请给个 Star 支持一下！**

[![Star History Chart](https://api.star-history.com/svg?repos=tmwgsicp/ForgeRSS&type=Date)](https://star-history.com/#tmwgsicp/ForgeRSS&Date)

Made with love by [tmwgsicp](https://github.com/tmwgsicp)

</div>
