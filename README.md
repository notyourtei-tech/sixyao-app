# 六爻占卜 / Six Yao Divination

一个支持 **6种语言** 的在线六爻占卜网站，基于中国古代《周易》预测方法。

## 功能特点

### 核心功能
- **三种起卦方式**：摇卦（传统铜钱法）、时间起卦、数字起卦
- **五大运势解读**：恋爱/感情、工作/学业、金钱/财运、健康、人际/出行
- **本卦与变卦**：自动生成当前状态和未来走向的对比分析
- **动爻分析**：详细解读变化爻位的含义
- **卦象趋势**：从本卦到变卦的发展趋势预测
- **每日运势**：每天自动生成一签

### 用户功能
- **收藏功能**：保存感兴趣的占卜结果
- **历史记录**：查看所有占卜记录，支持搜索和时间筛选
- **卦象图谱**：浏览完整的六十四卦图鉴
- **数据统计**：查看占卜次数、卦象分布、类型分布
- **分享功能**：支持 Twitter、WhatsApp、LINE、Facebook 分享
- **图片保存**：一键生成精美的占卜结果图片
- **每日提醒**：开启浏览器通知提醒占卜
- **深色/浅色主题**：自由切换界面主题

### 多语言支持
支持以下 6 种语言，界面、占卜解读、教程全部本地化：

| 语言 | 代码 | 状态 |
|------|------|------|
| 中文 | zh | ✅ 完整 |
| 日本語 | ja | ✅ 完整 |
| English | en | ✅ 完整 |
| Tiếng Việt | vi | ✅ 完整 |
| 한국어 | ko | ✅ 完整 |
| မြန်မာ | my | ✅ 完整 |

### 技术特性
- **PWA 支持**：可添加到手机主屏幕，离线可用
- **响应式设计**：适配手机、平板、桌面端
- **SEO 优化**：完整的 meta 标签和 Open Graph 支持
- **安全防护**：CSRF 保护、输入验证、SQL 注入防护
- **64 卦完整数据**：每个卦象都有详细的多语言解读

## 技术栈

- **后端**：Python Flask
- **数据库**：SQLite
- **前端**：HTML/CSS/JavaScript（无框架依赖）
- **部署**：Gunicorn + Render

## 快速开始

### 本地运行

```bash
# 克隆项目
git clone https://github.com/你的用户名/sixyao-app.git
cd sixyao-app

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt

# 启动开发服务器
python app.py
```

访问 http://127.0.0.1:8888

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| SECRET_KEY | Flask 密钥 | 自动生成 |
| BIND | 服务器绑定地址 | 0.0.0.0:8000 |
| WORKERS | Gunicorn 工作进程数 | 2 |

## 部署到 Render

1. 推送代码到 GitHub
2. 在 Render 创建 Web Service
3. 设置环境变量 `SECRET_KEY`
4. 部署完成

详见 `Procfile` 和 `runtime.txt`。

## 项目结构

```
sixyao-app/
├── app.py              # Flask 主应用
├── hexinterp.py        # 六十四卦解读数据
├── requirements.txt    # Python 依赖
├── Procfile            # Render 部署配置
├── runtime.txt         # Python 版本
├── gunicorn.conf.py    # Gunicorn 配置
├── sixyao2.db          # SQLite 数据库
├── static/
│   ├── style.css       # 样式表
│   ├── manifest.json   # PWA 配置
│   ├── sw.js           # Service Worker
│   └── gua/            # 六十四卦图片
└── templates/
    ├── base.html       # 基础模板
    ├── index.html      # 首页
    ├── welcome.html    # 欢迎/引导页
    ├── result.html     # 占卜结果页
    ├── history.html    # 历史记录页
    ├── gallery.html    # 卦象图谱页
    ├── stats.html      # 统计页
    └── error.html      # 错误页
```

## 免责声明

六爻占卜是一种参考工具，结果供日常参考。重大决策还需结合实际情况综合判断。

## License

MIT
