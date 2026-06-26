# 六爻应用 硬编码文字审计报告

扫描日期：2026-06-25
扫描范围：全部 .py / .html / .js / .css 文件
规则：所有用户可见文字必须从 i18n 资源获取，不允许在代码中写死任何语言的文字

---

## 汇总

| 文件 | 严重程度 | 硬编码条目数 |
|------|----------|-------------|
| templates/welcome.html | 🔴 严重 | ~70（整个页面） |
| app.py | 🔴 严重 | ~200（多个函数内嵌多语言字典） |
| templates/base.html | 🔴 严重 | ~12（微信提示 + fallback 默认值） |
| templates/index.html | 🟡 中等 | ~25（default filter 中的中文） |
| templates/result.html | 🟡 中等 | ~20（default filter + JS 中文） |
| templates/history.html | 🟡 中等 | ~5（default filter） |
| templates/gallery.html | 🟡 中等 | ~2（default filter） |
| templates/stats.html | 🟡 中等 | ~8（default filter） |
| templates/error.html | 🟡 中等 | ~3（default filter） |
| static/style.css | 🟢 无问题 | 0 |
| static/sw.js | 🟢 无问题 | 0 |

---

## 🔴 严重问题详情

### A. welcome.html — 整页未接入 i18n

**问题**：整个欢迎页的 HTML 文本和 JS 翻译对象全部内联硬编码。

**涉及行**：
- L7: `<title>Six Yao Divination</title>` — 英文写死
- L150: `Welcome` — 英文写死
- L151: `I Ching · Six Yao Divination` — 英文写死
- L157: `Choose your language` — 英文写死
- L161-187: 6 种语言的名称全部写死在 HTML 中
- L190: `Skip — use English` — 英文写死
- L200: `STEP 1` — 英文写死
- L204-207: `Back` / `Next` / `Skip tutorial` — 英文写死
- L216-245: JS 对象 `G` 包含 6 种语言的完整教程翻译（~60 个字符串）
- L264: `'Next'` — JS 硬编码
- L272: `'STEP '` — JS 硬编码

**修复方案**：将 `G` 对象的翻译内容提取到 Python 端的 TEXTS 字典或独立 JSON 文件中，通过 Jinja2 模板注入。

---

### B. base.html — 微信提示内嵌 6 语言字典

**涉及行**：
- L10/L12/L17: `| default('Six Yao Divination - Ancient Chinese...')` — 英文 fallback
- L33-35: `| default('Starred')` / `| default('Atlas')` / `| default('Stats')` — 英文 fallback
- L38: `| default('教程')` — 中文 fallback
- L39: `| default('切换主题')` — 中文 fallback
- L109-115: 微信/QQ 浏览器提示的完整 6 语言翻译字典（`texts` 对象）

**修复方案**：微信提示的翻译提取到 TEXTS 字典的对应 key 中（如 `wechat_title`、`wechat_desc`、`wechat_step`、`wechat_btn`）。所有 default 值不应包含任何语言的可见文字，应改用 TEXTS["en"] 作为 fallback。

---

### C. app.py — 后端多处内嵌多语言数据

#### C1. 错误处理器（L68, L77, L84, L1919）

4 个错误处理器各自内联一个 `msgs` 字典，包含 6 种语言的错误信息。应统一提取到 TEXTS 字典。

涉及 key：
- 404: `error_404_msg` — "页面未找到" 等
- 403: `error_403_msg` — "禁止访问" 等
- 500: `error_500_msg` — "服务器错误" 等
- view 404: `error_record_not_found` — "记录未找到" 等

#### C2. calc_liuchin()（L886）

```python
return ["父母", "兄弟", "妻财", "子孙", "官鬼", "父母"]
```
返回固定中文列表，无 lang 参数。所有 6 个位置都是中文。

#### C3. analyze_moving_lines()（L904-971）

整个函数内嵌 `data` 字典，包含 6 套完整的语言包：
- `pos`: 爻位名称（初爻/二爻/.../上爻 × 6 语言）
- `kin`: 六亲名称（父母/兄弟/... × 6 语言）
- `dir_y`/`dir_n`: 变爻方向（阳变阴/阴变阳 × 6 语言）
- `meanings`: 各爻位含义（6 条 × 6 语言）
- `sum_base`/`sum_1`~`sum_4`: 汇总句式（6 语言）

总计约 120 个硬编码字符串。

#### C4. build_trend_analysis()（L1012-1018）

趋势分析的中文文案用 f-string 直接拼接：
- L1014: `f"从当前卦象「{h_desc[:30]}…」到变卦「{c_desc[:30]}…」..."`
- L1016: `f"当前卦象的核心含义是「{h_desc[:50]}…」..."`
- L1018: `"变卦揭示了事物发展的最终走向..."`

#### C5. build_summary()（L1065-1096）

`cat_hints`（L1065-1072）和 `moving_hints`（L1074-1081）包含 6 语言的分类提示和动爻提示。

#### C6. build_fortune_comparison()（L1113-1119）

`aspect_names` 字典包含 6 语言的运势类别名称。

#### C7. random_hex()（L2036）

随机卦的默认问题文本：
```python
{"zh": "随机一卦 · 今日运势", "ja": "ラッキー占い · 今日の運勢", "en": "Quick Cast · Daily Fortune", ...}
```

#### C8. stats()（L2105）

```python
"random": "Random",
```
英文直接写死。

#### C9. __main__（L2137-2140）

```python
print("初始化数据库 sixyao2.db ...")
print("启动: http://127.0.0.1:8888")
```
中文写死（虽然仅限终端输出，但不符合规则）。

---

## 🟡 中等问题 — 模板 default filter 中的硬编码

以下所有 `| default(...)` 的 fallback 值都是写死的文字。当 TEXTS 字典缺少对应 key 时就会显示这些硬编码文字。

### index.html（25 处）

| 行 | default 值 | 语言 |
|----|-----------|------|
| L11 | `起卦中…` | zh |
| L23 | `今日一签` | zh |
| L25 | `第` / `卦` | zh |
| L32 | `我也来一卦` | zh |
| L43 | `I Ching · Six Lines` | en |
| L51 | `问题类型` | zh |
| L55 | `综合运势` | zh |
| L59 | `感情` | zh |
| L63 | `事业` | zh |
| L67 | `财运` | zh |
| L71 | `健康` | zh |
| L75 | `人际` | zh |
| L111 | `随机一卦` | zh |
| L116 | `开启每日提醒` | zh |
| L189 | `您的浏览器不支持通知功能` | zh |
| L196/L200/L208/L235 | `开启每日提醒` / `关闭每日提醒` | zh |
| L224 | `六爻占卜` | zh |
| L225 | `今天还没有占卜哦...` | zh |

### result.html（20 处）

涉及 `本卦`、`变卦`、`动爻分析`、`变卦趋势`、`分享结果`、`复制分享文案`、`复制链接`、`保存图片`、`图片已保存`、`取消收藏`、`收藏`、`首页`、`术语解释 / Glossary` 等，全部为中文。

### history.html（5 处）

`搜索问题或卦象...`、`全部`、`今天`、`本周`、`本月`、`开始占卜` — 均为中文。

### gallery.html（2 处）

`卦象图谱`、`六十四卦完整图谱 — 点击任意一卦进行占卜` — 中文。

### stats.html（8 处）

`占卜统计`、`总占卜次数`、`收藏次数`、`不同卦象`、`还没有占卜记录...`、`卦象分布`、`起卦方式分布`、`近期活动`、`共`、`种不同卦象` — 中文。

### error.html（3 处）

`返回首页` 出现 3 次作为 fallback — 中文。

---

## 🟢 无问题文件

- `static/style.css` — 无用户可见文字
- `static/sw.js` — 仅技术标识符
- `hexinterp.py` — 解释数据，所有文字已按语言组织在字典结构中（不构成 UI 硬编码问题）

---

## 修复优先级建议

1. **P0** — welcome.html：重写为从后端传入翻译数据，或改为 Jinja2 模板
2. **P0** — app.py 中的内嵌多语言字典：统一合并到 TEXTS 中
3. **P1** — base.html 微信提示：翻译提取到 TEXTS
4. **P2** — 所有模板的 `| default(...)` 值：确保 TEXTS 字典包含所有需要的 key，消除 default fallback
5. **P3** — app.py `__main__` 中的 print 文字（仅开发者可见）
