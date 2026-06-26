from flask import Flask, render_template, request, redirect, url_for, abort, session
import json
import sqlite3
from datetime import datetime
from contextlib import contextmanager
import random
import secrets
import os
import hmac
import hashlib
import logging
from markupsafe import escape
from hexinterp import get_hex_name, get_hex_meaning, INTERPRETATIONS, GLOSSARY

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.environ.get('FLASK_ENV') == 'production',
)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sixyao2.db")

LANGS = ["zh", "ja", "en", "vi", "ko", "my"]

# ===== CSRF Protection =====
def generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']

app.jinja_env.globals['csrf_token'] = generate_csrf_token

@app.before_request
def csrf_protect():
    if request.method == "POST":
        token = request.form.get('_csrf_token', '')
        expected = session.get('_csrf_token', '')
        if not token or not hmac.compare_digest(token, expected):
            abort(403)

# ===== Input Validation =====
def sanitize_input(text, max_len=500):
    if not text:
        return ""
    text = str(text)[:max_len]
    text = text.strip()
    return text

def validate_number(value):
    try:
        n = int(value)
        return 0 <= n <= 999999
    except (ValueError, TypeError):
        return False

# ===== Path Safety =====
def safe_gua_path(hex_no):
    if not isinstance(hex_no, int) or hex_no < 0 or hex_no > 63:
        return None
    return f"gua/{hex_no}.png"

# ===== Error Handlers =====
def _error_lang_urls(lang):
    return {code: url_for("index", lang=code) for code in LANGS}

@app.errorhandler(404)
def not_found(e):
    lang = request.args.get("lang", "zh")
    if lang not in LANGS:
        lang = "zh"
    t = TEXTS.get(lang, TEXTS["zh"])
    return render_template("error.html", lang=lang, t=t, lang_urls=_error_lang_urls(lang), code=404, message=t.get("error_404", "Page Not Found")), 404

@app.errorhandler(403)
def forbidden(e):
    lang = request.args.get("lang", "zh")
    if lang not in LANGS:
        lang = "zh"
    t = TEXTS.get(lang, TEXTS["zh"])
    return render_template("error.html", lang=lang, t=t, lang_urls=_error_lang_urls(lang), code=403, message=t.get("error_403", "Access Denied")), 403

@app.errorhandler(500)
def server_error(e):
    lang = get_lang()
    t = TEXTS.get(lang, TEXTS["zh"])
    return render_template("error.html", lang=lang, t=t, lang_urls=_error_lang_urls(lang), code=500, message=t.get("error_500", "Server Error")), 500

TEXTS = {
    "zh": {
        "app_title": "六爻占卜",
        "nav_home": "首页",
        "nav_history": "历史记录",
        "btn_start": "开始占卜",
        "method_coin": "摇卦（传统铜钱）",
        "method_time": "时间起卦",
        "method_number": "数字起卦",
        "method_label": "起卦方式",
        "number_placeholder": "请输入 0-999 的数字",
        "question_label": "问题 / 心中所想",
        "question_placeholder": "可写下你现在最在意的问题，也可以留空只看运势。",
        "guide_title": "什么是六爻占卜？",
        "guide_intro": "六爻占卜，又称「周易预测」，是中国最古老的占卜方法之一，已有三千多年的历史。它通过投掷铜钱或随机方式生成六个爻（阴爻或阳爻），组成一个六十四卦之一，再结合动爻（变化的爻）得到本卦与变卦，从而解读事物的发展趋势和应对之道。",
        "guide_step1": "心中默想你要问的事情，越具体越好。比如「最近这份工作适合我吗？」比「我的运势怎么样？」更有效。",
        "guide_step2": "选择一种起卦方式：「摇卦」模拟传统铜钱法，最为正统；「时间起卦」用当前时间自动起卦；「数字起卦」输入一个数字来起卦。",
        "guide_step3": "点击「开始占卜」后，系统会生成本卦（当前状态）和变卦（未来走向），并从恋爱、事业、财运、健康、人际五个方面为你详细解读。",
        "guide_note": "六爻占卜是一种参考工具，结果供日常参考。重大决策还需结合实际情况综合判断。每一次占卜都会被记录在历史中，方便回顾。",
        "result_title": "占卜结果",
        "hex_title_prefix": "第",
        "hex_title_suffix": "卦",
        "summary_notice": "此卦的具体含义需要结合问题本身、六亲、用神等综合判断，本页面提供的是日常生活向的大致参考。",
        "five_luck": "五大运势",
        "love": "恋爱 / 感情",
        "career": "工作 / 学业",
        "wealth": "金钱 / 财运",
        "health": "健康",
        "travel": "人际 / 出行",
        "now": "当前：",
        "future": "未来：",
        "advice": "建议：",
        "history_title": "占卜记录",
        "history_id": "ID",
        "history_method": "起卦方式",
        "history_question": "问题",
        "history_hex": "卦象",
        "history_time": "时间",
        "history_none": "目前还没有记录。",
        "method_name_coin": "摇卦",
        "method_name_time": "时间起卦",
        "method_name_number": "数字起卦",
        "nav_starred": "收藏记录",
        "nav_gallery": "卦象图谱",
        "btn_random": "随机一卦",
        "btn_star": "收藏",
        "btn_unstar": "取消收藏",
        "category_label": "问题类型",
        "cat_general": "综合运势",
        "cat_love": "感情",
        "cat_career": "事业",
        "cat_wealth": "财运",
        "cat_health": "健康",
        "cat_people": "人际",
        "moving_title": "动爻分析",
        "moving_summary": "动爻提示",
        "trend_title": "变卦趋势",
        "share_title": "分享结果",
        "nav_stats": "数据统计",
        "stats_title": "占卜统计",
        "stats_total": "总占卜次数",
        "stats_starred": "收藏次数",
        "stats_hex_dist": "卦象分布",
        "stats_cat_dist": "问题类型分布",
        "stats_method_dist": "起卦方式分布",
        "stats_recent": "近期活动",
        "stats_times": "次",
        "daily_label": "今日一签",
        "btn_quick_cast": "我也来一卦",
        "coin_tossing": "起卦中…",
        "comparison_desc": "各运势从本卦到变卦的变化：",
        "label_original": "本卦：",
        "label_changed": "变卦：",
        "btn_copy_share": "复制分享文案",
        "btn_copy_link": "复制链接",
        "share_hint": "卦象解读供参考，详情请查看",
        "copied_share": "✓ 分享文案已复制到剪贴板",
        "copied_link": "✓ 链接已复制到剪贴板",
        "gallery_desc": "六十四卦完整图谱 — 点击任意一卦进行占卜",
        "stats_diff_hex": "不同卦象",
        "stats_total_diff": "共",
        "stats_diff_hex_unit": "种不同卦象",
        "stats_empty": "还没有占卜记录，快去占一卦吧！",
        "theme_toggle": "切换主题",
        "hex_prefix": "第",
        "hex_suffix": "卦",
        "original_hex": "本卦",
        "changed_hex": "变卦",
        "glossary_title": "术语解释 / Glossary",
        "search_placeholder": "搜索问题或卦象...",
        "go_cast": "开始占卜",
        "btn_save_image": "保存图片",
        "image_saved": "✓ 图片已保存",
        "btn_reminder": "开启每日提醒",
        "btn_reminder_off": "关闭每日提醒",
        "reminder_title": "六爻占卜",
        "reminder_body": "今天还没有占卜哦，来看看今日运势吧！",
        "reminder_not_supported": "您的浏览器不支持通知功能",
        "seo_description": "六爻占卜 — 中国古老的周易预测方法，支持中日英越韩缅六种语言，从恋爱、事业、财运、健康、人际五个方面为你解读运势。",
        "history_today": "今天",
        "history_week": "本周",
        "history_month": "本月",
        "date_format": "%Y年%m月%d日",
        "error_404": "页面未找到",
        "error_403": "禁止访问",
        "error_500": "服务器错误",
        "error_record_not_found": "记录未找到",
        "wechat_title": "请在浏览器中打开",
        "wechat_desc": "当前在微信/QQ等应用内置浏览器中打开，部分功能可能受限。建议使用系统浏览器访问以获得完整体验。",
        "wechat_step": "1. 点击右上角 ⋯ 按钮<br>2. 选择 在浏览器中打开",
        "wechat_btn": "我知道了",
        "random_question": "随机一卦 · 今日运势",
        "cat_random": "随机",
        "trend_zh_from": "从当前卦象「{h}…」到变卦「{c}…」，事态正在从一种状态向另一种状态转变。动爻越多，变化越剧烈。变卦揭示了事物发展的最终走向。",
        "trend_zh_stable": "当前卦象的核心含义是「{h}…」。变卦与本卦相同或相近，意味着当前状态比较稳定，短期内不会有根本性的变化。",
        "trend_zh_default": "变卦揭示了事物发展的最终走向。建议结合本卦和变卦综合判断。",
        "cat_hints": {"love": "感情方面", "career": "事业方面", "wealth": "财运方面", "health": "健康方面", "people": "人际方面", "random": "今日运势", "general": "综合运势"},
        "moving_hints": "有{n}个动爻，变化较多。",
        "aspect_names": {"love": "感情", "career": "事业", "wealth": "财运", "health": "健康", "travel": "人际"},
        "moving_data": {
            "pos": ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"],
            "kin": ["父母", "兄弟", "妻财", "子孙", "官鬼", "父母"],
            "dir_y": "阳变阴",
            "dir_n": "阴变阳",
            "meanings": {1: "事物的萌芽阶段，基础和起始", 2: "内在发展期，个人修养和积累", 3: "过渡阶段，面临抉择和考验", 4: "近君之位，机遇与风险并存", 5: "君位，事业的核心和主导", 6: "事物的极盛或转折点"},
            "sum_base": "共{n}个动爻",
            "sum_1": "，事态集中于一个焦点，变化方向明确",
            "sum_2": "，两种力量交织，需要权衡取舍",
            "sum_3": "，变化较多，局势复杂，宜静观其变",
            "sum_4": "，变数极多，当前不宜做重大决定",
        },
    },
    "ja": {
        "app_title": "六爻占い",
        "nav_home": "トップ",
        "nav_history": "履歴",
        "btn_start": "占う",
        "method_coin": "揺卦（コイン法）",
        "method_time": "時間起卦",
        "method_number": "数字起卦",
        "method_label": "起卦方法",
        "number_placeholder": "0〜999 の数字を入力してください",
        "question_label": "占いたい内容・テーマ",
        "question_placeholder": "今一番気になっていることを書いてもいいし、空欄のまま運勢だけ見ても大丈夫です。",
        "guide_title": "六爻占いとは？",
        "guide_intro": "六爻占いは「周易予測」とも呼ばれ、中国最古の占いの一つで、3000年以上の歴史があります。コインを投げたりランダムな方法で6つの爻（陰爻・陽爻）を生成し、64卦の一つを構成。変爻（動く爻）を組み合わせて本卦と変卦を得て、物事の発展傾向と対処法を読み解きます。",
        "guide_step1": "占いたいことを心に浮かべてください。具体的な方が効果的です。例：「今の仕事は自分に合っているか？」のように。",
        "guide_step2": "起卦方法を選んでください。「揺卦」は伝統的なコイン法で最も正統、「時間起卦」は現在の時刻で自動起卦、「数字起卦」は数字を入力して起卦します。",
        "guide_step3": "「占う」ボタンを押すと、本卦（今の状態）と変卦（将来の傾向）が生成され、恋愛・仕事・金運・健康・人間関係の5つの角度から詳しい解説が表示されます。",
        "guide_note": "六爻占いはあくまで参考ツールであり、日常的な目安としてご利用ください。重要な判断は現実的な状況と総合的に考えることが大切です。占いの履歴は記録されます。",
        "result_title": "占い結果",
        "hex_title_prefix": "第",
        "hex_title_suffix": "卦",
        "summary_notice": "具体的な判断には質問内容・六親・用神などを総合して読む必要があります。このページでは日常生活向けの目安となる解説を表示しています。",
        "five_luck": "五大運勢",
        "love": "恋愛・感情",
        "career": "仕事・学業",
        "wealth": "金運・お金",
        "health": "健康",
        "travel": "人間関係・お出かけ",
        "now": "現在：",
        "future": "今後：",
        "advice": "アドバイス：",
        "history_title": "占い履歴",
        "history_id": "ID",
        "history_method": "方法",
        "history_question": "内容",
        "history_hex": "卦",
        "history_time": "時間",
        "history_none": "まだ履歴はありません。",
        "method_name_coin": "揺卦",
        "method_name_time": "時間起卦",
        "method_name_number": "数字起卦",
        "nav_starred": "お気に入り",
        "nav_gallery": "六十四卦図鑑",
        "btn_random": "ラッキー占い",
        "btn_star": "お気に入り",
        "btn_unstar": "解除",
        "category_label": "質問タイプ",
        "cat_general": "総合運勢",
        "cat_love": "恋愛",
        "cat_career": "仕事",
        "cat_wealth": "金運",
        "cat_health": "健康",
        "cat_people": "人間関係",
        "moving_title": "動爻分析",
        "moving_summary": "動爻の示唆",
        "trend_title": "変卦の流れ",
        "share_title": "結果を共有",
        "nav_stats": "データ",
        "stats_title": "占いデータ",
        "stats_total": "占い総数",
        "stats_starred": "お気に入り数",
        "stats_hex_dist": "卦の分布",
        "stats_cat_dist": "質問タイプ分布",
        "stats_method_dist": "方法の分布",
        "stats_recent": "最近の活動",
        "stats_times": "",
        "daily_label": "今日の運勢",
        "btn_quick_cast": "占ってもらう",
        "coin_tossing": "占い中…",
        "comparison_desc": "本卦から変卦への各運勢の変化：",
        "label_original": "本卦：",
        "label_changed": "変卦：",
        "btn_copy_share": "共有テキストをコピー",
        "btn_copy_link": "リンクをコピー",
        "share_hint": "参考まで。詳しくはこちら：",
        "copied_share": "✓ 共有テキストをコピーしました",
        "copied_link": "✓ リンクをコピーしました",
        "gallery_desc": "六十四卦図鑑 — タップして占いましょう",
        "stats_diff_hex": "種類の卦",
        "stats_total_diff": "計",
        "stats_diff_hex_unit": "種類の卦を占いました",
        "stats_empty": "まだ記録がありません。最初の占いを始めましょう！",
        "theme_toggle": "テーマ切替",
        "hex_prefix": "第",
        "hex_suffix": "卦",
        "original_hex": "本卦",
        "changed_hex": "変卦",
        "glossary_title": "用語解説",
        "search_placeholder": "質問や卦を検索...",
        "go_cast": "占いを始める",
        "btn_save_image": "画像を保存",
        "image_saved": "✓ 画像を保存しました",
        "btn_reminder": "毎日のリマインダーを有効にする",
        "btn_reminder_off": "毎日のリマインダーを無効にする",
        "reminder_title": "六爻占い",
        "reminder_body": "今日まだ占っていません。今日の運勢を確認しましょう！",
        "reminder_not_supported": "お使いのブラウザは通知に対応していません",
        "seo_description": "六爻占い — 中国古代の周易予測法。恋愛・仕事・金運・健康・人間関係の5つの運勢を6言語で解説。",
        "history_today": "今日",
        "history_week": "今週",
        "history_month": "今月",
        "date_format": "%Y年%m月%d日",
        "error_404": "ページが見つかりません",
        "error_403": "アクセスが拒否されました",
        "error_500": "サーバーエラー",
        "error_record_not_found": "記録が見つかりません",
        "wechat_title": "ブラウザで開いてください",
        "wechat_desc": "微信やQQなどのアプリ内ブラウザでは、一部の機能が制限される場合があります。システムブラウザで開くことをお勧めします。",
        "wechat_step": "1. 右上の ⋯ ボタンをタップ<br>2. ブラウザで開く を選択",
        "wechat_btn": "了解しました",
        "random_question": "ラッキー占い · 今日の運勢",
        "cat_random": "ランダム",
        "trend_arrow": "{h}… → {c}…",
        "cat_hints": {"love": "恋愛", "career": "仕事", "wealth": "金運", "health": "健康", "people": "人間関係", "random": "今日の運勢", "general": "総合運勢"},
        "moving_hints": "動爻{n}個で、変化が多い時期です。",
        "aspect_names": {"love": "恋愛", "career": "仕事", "wealth": "金運", "health": "健康", "travel": "人間関係"},
        "moving_data": {
            "pos": ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"],
            "kin": ["父母", "兄弟", "妻財", "子孫", "官鬼", "父母"],
            "dir_y": "陽→陰",
            "dir_n": "陰→陽",
            "meanings": {1: "物事の萌芽段階、基礎と出発点", 2: "内在発展期、個人の修養と蓄積", 3: "移行段階、選択と試練に直面", 4: "君主に近い位置、機会とリスクが共存", 5: "君位、事業の核心と主導", 6: "物事の極盛または転換点"},
            "sum_base": "動爻{n}個",
            "sum_1": "、事態は一つの焦点に集中し、変化の方向は明確",
            "sum_2": "、二つの力が絡み合い、バランスを取る必要あり",
            "sum_3": "、変化が多く、状況は複雑、静観が吉",
            "sum_4": "、変動が極めて多く、重大な決定は控えめに",
        },
    },
    "my": {
        "app_title": "ဆြေရှုရေး",
        "nav_home": "ပင်မ",
        "nav_history": "မှတ်တမ်း",
        "btn_start": "စတင်ပါ",
        "method_coin": "ငွေဒင်းနစ်ဖြင့် (ရိုးရာ)",
        "method_time": "အချိန်ဖြင့်",
        "method_number": "ဂဏန်းဖြင့်",
        "method_label": "နည်းလမ်း",
        "number_placeholder": "0-999 ဂဏန်းထည့်ပါ",
        "question_label": "မေးခွန်း / စိတ်ထဲမှာရှိနေတာ",
        "question_placeholder": "သင့်အတွက် အရေးအကြီးဆုံးကိစ္စကို ရေးပါ၊ ဒါမှမဟုတ် ကွာဟချက်ထားပြီး ကံကြမ္မာကိုပဲ ကြည့်ပါ။",
        "guide_title": "ဆြေရှုရေးဆိုတာ ဘာလဲ?",
        "guide_intro": "ဆြေရှုရေးသည် တရုတ်ရိုးရာ အဟောင်းဆုံး နိမိတ်ဖတ်ခြင်းနည်းစနစ်ဖြစ်ပြီး နှစ်ပေါင်း ၃၀၀၀ ကျော် သမိုင်းကြောင်းရှိသည်။",
        "guide_step1": "သင်မေးလိုသည့်အရာကို အတွေးထဲမှာ ရှင်းရှင်းလင်းလင်း စဉ်းစားပါ။ ပိုတိကျလေ ပိုကောင်းလေဖြစ်သည်။",
        "guide_step2": "နည်းလမ်းတစ်ခုရွေးပါ — 'ငွေဒင်းနစ်'သည် ရိုးရာနည်းလမ်းဖြစ်ပြီး အကောင်းဆုံးဖြစ်သည်။ 'အချိန်ဖြင့်'နှင့် 'ဂဏန်းဖြင့်'ကိုလည်း ရွေးချယ်နိုင်သည်။",
        "guide_step3": "'စတင်ပါ'ကိုနှိပ်ပါ — မူလဗေဒနှင့် ပြောင်းလဲသွားသည့် ဗေဒနှစ်ခုလုံးကို ဖန်တီးပြီး ချစ်ခြင်း၊ အလုပ်၊ ငွေကြေး၊ ကျန်းမာရေး၊ လူမှုဆက်ဆံရေး ဟူသော အပိုင်း ၅ ပိုင်းမှ အသေးစိတ်ဖတ်ရှုနိုင်ပါသည်။",
        "guide_note": "ဆြေရှုရေးသည် ကိုးကားအချက်အလက်တစ်ခုဖြစ်ပါသည်။ အရေးကြီးသည့်ဆုံးဖြတ်ချက်များအတွက် လက်တွေ့အခြေအနေနှင့် ပေါင်းစပ်စဉ်းစားပါ။",
        "result_title": "ရလဒ်",
        "hex_title_prefix": "ဗေဒ",
        "hex_title_suffix": "",
        "summary_notice": "တိကျသည့်ဖတ်ခြင်းအတွက် မေးခွန်း၊ ဆွေမျိုး ၆ ပါးနှင့် အသုံးဝင်သည့် စိတ်တန်ခိုးတို့ကို ပေါင်းစပ်ဖတ်ရှုရပါမည်။",
        "five_luck": "အပိုင်း ၅ ပိုင်း",
        "love": "ချစ်ခြင်းမေတ္တာ",
        "career": "အလုပ် / ပညာရေး",
        "wealth": "ငွေကြေး",
        "health": "ကျန်းမာရေး",
        "travel": "လူမှုဆက်ဆံရေး",
        "now": "လက်ရှိ —",
        "future": "အနာဂတ် —",
        "advice": "အကြံပြုချက် —",
        "history_title": "မှတ်တမ်း",
        "history_id": "ID",
        "history_method": "နည်းလမ်း",
        "history_question": "မေးခွန်း",
        "history_hex": "ဗေဒ",
        "history_time": "အချိန်",
        "history_none": "မှတ်တမ်းမရှိသေးပါ။",
        "method_name_coin": "ငွေဒင်းနစ်",
        "method_name_time": "အချိန်",
        "method_name_number": "ဂဏန်း",
        "nav_starred": "သိမ်းဆည်းထားသည်",
        "nav_gallery": "ဗေဒ ၆၄ ခု",
        "nav_stats": "စာရင်းအင်း",
        "btn_random": "မြန်မြန်ဆန်ဆန်",
        "btn_star": "သိမ်းဆည်းရန်",
        "btn_unstar": "ဖယ်ရှားရန်",
        "category_label": "မေးခွန်းအမျိုးအစား",
        "cat_general": "အထွေထွေ",
        "cat_love": "ချစ်ခြင်း",
        "cat_career": "အလုပ်",
        "cat_wealth": "ငွေကြေး",
        "cat_health": "ကျန်းမာရေး",
        "cat_people": "လူမှုဆက်ဆံ",
        "moving_title": "လှုပ်ရှားသည့်အကြောင်းအရာ ခွဲခြမ်းစိတ်ဖြာခြင်း",
        "moving_summary": "လှုပ်ရှားသည့်အကြောင်းအရာ အကြံပြုချက်",
        "trend_title": "ပြောင်းလဲမှု လမ်းကြောင်း",
        "original_hex": "မူလဗေဒ",
        "changed_hex": "ပြောင်းလဲသည့်ဗေဒ",
        "share_title": "ရလဒ်မျှဝေရန်",
        "daily_label": "ယနေ့ ဗေဒ",
        "btn_quick_cast": "ကျွန်ပ်အတွက် လှည့်ပါ",
        "coin_tossing": "လှည့်နေသည်...",
        "comparison_desc": "မူလဗေဒမှ ပြောင်းလဲသည့်ဗေဒသို့ အပိုင်းတိုင်း ပြောင်းလဲမှု —",
        "label_original": "မူလဗေဒ —",
        "label_changed": "ပြောင်းလဲသည့်ဗေဒ —",
        "btn_copy_share": "မျှဝေရန် ကူးယူရန်",
        "btn_copy_link": "လင့်ခ် ကူးယူရန်",
        "share_hint": "ကိုးကားအတွက်သာ — အသေးစိတ် —",
        "copied_share": "✓ မျှဝေရန် ကူးယူပြီးပါပြီ",
        "copied_link": "✓ လင့်ခ် ကူးယူပြီးပါပြီ",
        "gallery_desc": "ဗေဒ ၆၄ ခု အပြည့်အစုံ — မည်သည့်ဗေဒကိုမဆို နှိပ်ပြီး လှည့်ပါ",
        "stats_title": "စာရင်းအင်း",
        "stats_total": "စုစုပေါင်း လှည့်မှု",
        "stats_starred": "သိမ်းဆည်းထားမှု",
        "stats_hex_dist": "ဗေဒ ဖြန့်ဝေမှု",
        "stats_cat_dist": "မေးခွန်းအမျိုးအစား ဖြန့်ဝေမှု",
        "stats_method_dist": "နည်းလမ်း ဖြန့်ဝေမှု",
        "stats_recent": "နောက်ဆုံး လုပ်ဆောင်ချက်",
        "stats_times": "",
        "stats_diff_hex": "ကွဲပြားသည့်ဗေဒ",
        "stats_total_diff": "စုစုပေါင်း",
        "stats_diff_hex_unit": "ဗေဒလှည့်ပြီးပါပြီ",
        "stats_empty": "မှတ်တမ်းမရှိသေးပါ — ပထမဆုံး ဗေဒလှည့်ပါ!",
        "theme_toggle": "အပြင်အဆင် ပြောင်းလဲရန်",
        "hex_prefix": "ဗေဒ",
        "hex_suffix": "",
        "glossary_title": "အသုံးအနှုန်းရှင်းလင်းချက်",
        "search_placeholder": "မေးခွန်း သို့မဟုတ် ဗေဒ ရှာဖွေရန်...",
        "go_cast": "စတင်လှည့်ရန်",
        "btn_save_image": "ပုံသိမ်းရန်",
        "image_saved": "✓ ပုံသိမ်းပြီးပါပြီ",
        "btn_reminder": "နေ့စဉ် သတိပေးချက် ဖွင့်ရန်",
        "btn_reminder_off": "နေ့စဉ် သတိပေးချက် ပိတ်ရန်",
        "reminder_title": "ဆြေရှုရေး",
        "reminder_body": "ယနေ့ ဗေဒမလှည့်ရသေးပါ — ယနေ့ ကံကြမ္မာကို ကြည့်ပါ!",
        "reminder_not_supported": "သင့်ဘရောင်ဇာသည် သတိပေးချက်ကို ပံ့ပိုးမပေးပါ",
        "seo_description": "ဆြေရှုရေး — တရုတ်ရိုးရာ နိမိတ်ဖတ်ခြင်းနည်းစနစ်။ ချစ်ခြင်း/အလုပ်/ငွေကြေး/ကျန်းမာရေး/လူမှုဆက်ဆံ ဘာသာစကား ၆ မျိုးဖြင့် ခွဲခြမ်းစိတ်ဖြာပါသည်။",
        "history_today": "ယနေ့",
        "history_week": "ဤအပတ်",
        "history_month": "ဤလ",
        "date_format": "%Y-%m-%d",
        "error_404": "စာမျက်နှာ ရှာမတွေ့ပါ",
        "error_403": "ဝင်ရောက်ခွင့် ငြင်းပိတ်ထားသည်",
        "error_500": "ဆာဗာ အမှား",
        "error_record_not_found": "မှတ်တမ်း ရှာမတွေ့ပါ",
        "wechat_title": "ဘရောင်ဇာဖြင့် ဖွင့်ပါ",
        "wechat_desc": "WeChat/QQ အက်ပ်အတွင်း ဘရောင်ဇာဖြင့် ဖွင့်ထားပါသည်။ အပြည့်အဝအသုံးပြုရန် စနစ်ဘရောင်ဇာဖြင့် ဖွင့်ပါ။",
        "wechat_step": "၁။ ညာဘက်အပေါ်ခြမ်းရှိ ⋯ ခလုတ်ကို နှိပ်ပါ<br>၂။ ဘရောင်ဇာဖြင့် ဖွင့်ရန် ကို ရွေးပါ",
        "wechat_btn": "နားလည်ပါပြီ",
        "random_question": "မြန်မြန်ဆန်ဆန် · ယနေ့ ကံကြမ္မာ",
        "cat_random": "များများ",
        "trend_arrow": "{h}… → {c}…",
        "cat_hints": {"love": "ချစ်ခြင်း", "career": "အလုပ်", "wealth": "ငွေကြေး", "health": "ကျန်းမာရေး", "people": "လူမှုဆက်ဆံ", "random": "ယနေ့ ကံကြမ္မာ", "general": "အထွေထွေ ကံကြမ္မာ"},
        "moving_hints": "လှုပ်ရှားသည့်အကြောင်းအရာ {n} ခု — ပြောင်းလဲမှုများ များပြားပါသည်။",
        "aspect_names": {"love": "ချစ်ခြင်း", "career": "အလုပ်", "wealth": "ငွေကြေး", "health": "ကျန်းမာရေး", "travel": "လူမှုဆက်ဆံ"},
        "moving_data": {
            "pos": ["ပထမအကြောင်း", "ဒုတိယအကြောင်း", "တတိယအကြောင်း", "စတုတ္ထအကြောင်း", "ပဉ္စမအကြောင်း", "ဆဋ္ဌမအကြောင်း"],
            "kin": ["မိဘ", "ညီအစ်ကိုမောင်နှမ", "ဇနီး/ငွေကြေး", "သားသမီး", "အရာရှိ", "မိဘ"],
            "dir_y": "အမျိုးသား→အမျိုးသမီး",
            "dir_n": "အမျိုးသမီး→အမျိုးသား",
            "meanings": {1: "အစပျိုးခြင်းအဆင့် — အခြေခံနှင့် အစပျိုးခြင်း", 2: "အတွင်းပိုင်းဖွံ့ဖြိုးခြင်း — ကိုယ်ကျင့်တရားနှင့် စုဆောင်းခြင်း", 3: "ပြောင်းလဲခြင်းအဆင့် — ဆုံးဖြတ်ချက်များနှင့် စမ်းသပ်မှုများ", 4: "ဘုရင်နှင့် နီးကပ်သည့်နေရာ — အခွင့်အရေးနှင့် အန္တရာယ်", 5: "ဘုရင်နေရာ — အလုပ်၏ အဓိကနှင့် ဦးဆောင်မှု", 6: "အမြင့်ဆုံး သို့မဟုတ် ပြောင်းလဲမှုအမှတ်"},
            "sum_base": "လှုပ်ရှားသည့်အကြောင်းအရာ {n} ခု",
            "sum_1": " — အဓိကအာရုံချက်တစ်ခုတည်းတွင် စုပေါင်းပြီး ပြောင်းလဲမှု ဦးတည်ချက်ရှင်းလင်းသည်",
            "sum_2": " — အင်အားနှစ်ခု ထွေထွေရှုပ်နေပြီး ဟန်ချက်ညီအောင် လုပ်ရန် လိုအပ်သည်",
            "sum_3": " — ပြောင်းလဲမှုများပြားပြီး အခြေအနေရှုပ်ထွေးသည်၊ ငြိမ်သက်စွာ ကြည့်ရှုရန် သင့်တော်သည်",
            "sum_4": " — ပြောင်းလဲမှုများ အလွန်များပြားပြီး အရေးကြီးသည့် ဆုံးဖြတ်ချက်များ ချမှတ်ခြင်းမပြုသင့်ပါ",
        },
    },
    "welcome_texts": {
        "zh": {
            "title": "欢迎使用六爻占卜",
            "step1_title": "这是什么？",
            "step1_desc": "六爻占卜是中国古老的周易预测方法，通过起卦来了解事物的发展趋势，帮你做出更好的决策。",
            "step2_title": "可以做什么？",
            "step2_desc": "你可以占卜恋爱、事业、财运、健康、人际等五个方面的运势，获得当前状态和未来走向的分析。",
            "step3_title": "如何使用？",
            "step3_desc": "第一步：选择起卦方式（摇卦/时间/数字）\n第二步：写下你心中想问的问题\n第三步：点击开始占卜",
            "btn_start": "开始使用",
            "lang_title": "选择语言",
        },
        "ja": {
            "title": "六爻占いへようこそ",
            "step1_title": "これは何？",
            "step1_desc": "六爻占いは中国の古代からの周易予測法で、卦を起こすことで物事の発展傾向を知り、より良い判断を助けます。",
            "step2_title": "何が出来る？",
            "step2_desc": "恋愛、仕事、金運、健康、人間関係の5つの運勢を占い、現在の状態と将来の傾向を分析できます。",
            "step3_title": "使い方",
            "step3_desc": "ステップ1：起卦方法を選択（揺卦/時間/数字）\nステップ2：占いたいことを書く\nステップ3：「占う」をクリック",
            "btn_start": "始める",
            "lang_title": "言語を選択",
        },
        "en": {
            "title": "Welcome to Six Yao Divination",
            "step1_title": "What is it?",
            "step1_desc": "Six Yao Divination is an ancient Chinese I Ching prediction method. By casting hexagrams, you can understand trends and make better decisions.",
            "step2_title": "What can you do?",
            "step2_desc": "You can divine five aspects of fortune: Love, Career, Wealth, Health, and Relationships, with analysis of current state and future direction.",
            "step3_title": "How to use?",
            "step3_desc": "Step 1: Choose a casting method (Coin/Time/Number)\nStep 2: Write your question\nStep 3: Click Start",
            "btn_start": "Get Started",
            "lang_title": "Choose Language",
        },
        "vi": {
            "title": "Chào mừng đến với Quẻ Lục Hào",
            "step1_title": "Đây là gì?",
            "step1_desc": "Lục Hào là phương pháp bói Chu Dịch cổ xưa của Trung Quốc. Qua việc gieo quẻ, bạn có thể hiểu xu hướng sự việc và đưa ra quyết định tốt hơn.",
            "step2_title": "Làm được gì?",
            "step2_desc": "Bạn có thể bói 5 phương diện: Tình cảm, Sự nghiệp, Tài vận, Sức khỏe, Quan hệ, phân tích trạng thái hiện tại và hướng đi tương lai.",
            "step3_title": "Cách dùng",
            "step3_desc": "Bước 1: Chọn cách gieo quẻ (Đồng xu/Thời gian/Số)\nBước 2: Viết câu hỏi của bạn\nBước 3: Nhấn Bắt đầu",
            "btn_start": "Bắt đầu",
            "lang_title": "Chọn ngôn ngữ",
        },
        "ko": {
            "title": "육효 점에 오신 것을 환영합니다",
            "step1_title": "이게 뭔가요?",
            "step1_desc": "육효 점은 중국의 고대 주역 예측법으로, 괘를 통해 사물의 발전 경향을 이해하고 더 나은 결정을 내리는 데 도움을 줍니다.",
            "step2_title": "뭘 할 수 있나요?",
            "step2_desc": "연애/직업/재운/건강/인간관계 5가지 운세를 점칠 수 있으며, 현재 상태와 미래 방향을 분석합니다.",
            "step3_title": "사용법",
            "step3_desc": "1단계: 점 방법 선택 (동전/시간/숫자)\n2단계: 질문 내용 입력\n3단계: 점 보기 클릭",
            "btn_start": "시작하기",
            "lang_title": "언어 선택",
        },
        "my": {
            "title": "ဆြေရှုရေးသို့ ကြိုဆိုပါ၏",
            "step1_title": "ဒါက ဘာလဲ?",
            "step1_desc": "ဆြေရှုရေးသည် တရုတ်ရိုးရာ အဟောင်းဆုံး နိမိတ်ဖတ်ခြင်းနည်းစနစ်ဖြစ်ပြီး ဗေဒများဖန်တီးခြင်းဖြင့် အရာဝတ္ထုများ၏ ဖွံ့ဖြိုးတိုးတက်မှု လမ်းကြောင်းကို နားလည်ပြီး ပိုကောင်းသည့်ဆုံးဖြတ်ချက်များ ချမှတ်နိုင်ပါသည်။",
            "step2_title": "ဘာတွေလုပ်နိုင်လဲ?",
            "step2_desc": "ချစ်ခြင်း၊ အလုပ်၊ ငွေကြေး၊ ကျန်းမာရေး၊ လူမှုဆက်ဆံရေး ဟူသော အပိုင်း ၅ ပိုင်း၏ ကံကြမ္မာကို နိမိတ်ဖတ်နိုင်ပြီး လက်ရှိအခြေအနေနှင့် အနာဂတ် ဦးတည်ချက်တို့ကို ခွဲခြမ်းစိတ်ဖြာနိုင်ပါသည်။",
            "step3_title": "ဘယ်လိုသုံးရမလဲ?",
            "step3_desc": "အဆင့် ၁ — နည်းလမ်းရွေးပါ (ငွေဒင်းနစ်/အချိန်/ဂဏန်း)\nအဆင့် ၂ — သင့်မေးခွန်းကို ရေးပါ\nအဆင့် ၃ — စတင်ပါကို နှိပ်ပါ",
            "btn_start": "စတင်ရန်",
            "lang_title": "ဘာသာစကား ရွေးပါ",
        },
    },
    "en": {
        "app_title": "Six Yao Divination",
        "nav_home": "Home",
        "nav_history": "History",
        "btn_start": "Start",
        "method_coin": "Coin casting (traditional)",
        "method_time": "Time-based casting",
        "method_number": "Number casting",
        "method_label": "Casting method",
        "number_placeholder": "Enter a number from 0 to 999",
        "question_label": "Question / focus",
        "question_placeholder": "Write down what you care about most right now, or leave it blank to just see the general fortune.",
        "guide_title": "What is Six Yao Divination?",
        "guide_intro": "Six Yao (Liu Yao) divination, also known as I Ching prediction, is one of China's oldest divination methods with over 3,000 years of history. It generates six lines (yin or yang) through coin casting or random methods, forming one of the 64 hexagrams. Combined with moving lines (changing lines), it produces the Original Hexagram (current state) and Changed Hexagram (future direction), revealing trends and guidance.",
        "guide_step1": "Think clearly about what you want to ask. The more specific, the better. For example, 'Is this job right for me?' works better than 'How is my fortune?'",
        "guide_step2": "Choose a casting method: 'Coin casting' simulates the traditional copper coin method and is the most orthodox; 'Time-based casting' uses the current time; 'Number casting' lets you input a number.",
        "guide_step3": "Click 'Start' and the system will generate the Original Hexagram (current state) and Changed Hexagram (future direction), with detailed readings from five aspects: Love, Career, Wealth, Health, and Relationships.",
        "guide_note": "Six Yao divination is a reference tool for daily guidance. For major decisions, combine the reading with your actual situation. Every divination is recorded in your history for review.",
        "result_title": "Result",
        "hex_title_prefix": "Hexagram ",
        "hex_title_suffix": "",
        "summary_notice": "A precise reading requires combining the question, six relations and useful spirit. Here we show a practical, everyday-style summary.",
        "five_luck": "Five Aspects",
        "love": "Love / Relationship",
        "career": "Career / Study",
        "wealth": "Wealth / Money",
        "health": "Health",
        "travel": "People / Travel",
        "now": "Now:",
        "future": "Future:",
        "advice": "Advice:",
        "history_title": "History",
        "history_id": "ID",
        "history_method": "Method",
        "history_question": "Question",
        "history_hex": "Hexagram",
        "history_time": "Time",
        "history_none": "No records yet.",
        "method_name_coin": "Coin",
        "method_name_time": "Time",
        "method_name_number": "Number",
        "nav_starred": "Starred",
        "nav_gallery": "Hexagram Atlas",
        "btn_random": "Quick Cast",
        "btn_star": "Star",
        "btn_unstar": "Unstar",
        "category_label": "Question Type",
        "cat_general": "General",
        "cat_love": "Love",
        "cat_career": "Career",
        "cat_wealth": "Wealth",
        "cat_health": "Health",
        "cat_people": "People",
        "moving_title": "Moving Lines Analysis",
        "moving_summary": "Moving Lines Insight",
        "trend_title": "Trend Analysis",
        "share_title": "Share Result",
        "daily_label": "Daily Fortune",
        "btn_quick_cast": "Cast for me",
        "coin_tossing": "Casting…",
        "comparison_desc": "How each fortune aspect changes from original to changed hexagram:",
        "label_original": "Original: ",
        "label_changed": "Changed: ",
        "btn_copy_share": "Copy share text",
        "btn_copy_link": "Copy link",
        "share_hint": "For reference only. Details:",
        "copied_share": "✓ Share text copied",
        "copied_link": "✓ Link copied",
        "gallery_desc": "Complete 64-Hexagram Atlas — click any hexagram to cast",
        "stats_diff_hex": "different hexagrams",
        "stats_total_diff": "",
        "stats_diff_hex_unit": "different hexagrams cast",
        "stats_empty": "No records yet — cast your first hexagram!",
        "theme_toggle": "Toggle theme",
        "hex_prefix": "#",
        "hex_suffix": "",
        "original_hex": "Original Hexagram",
        "changed_hex": "Changed Hexagram",
        "glossary_title": "Glossary",
        "search_placeholder": "Search question or hexagram...",
        "go_cast": "Start Casting",
        "btn_save_image": "Save Image",
        "image_saved": "✓ Image saved",
        "btn_reminder": "Enable Daily Reminder",
        "btn_reminder_off": "Disable Daily Reminder",
        "reminder_title": "Six Yao Divination",
        "reminder_body": "You haven't cast today — check your daily fortune!",
        "reminder_not_supported": "Your browser doesn't support notifications",
        "seo_description": "Six Yao Divination — Ancient Chinese I Ching prediction. Analyze Love, Career, Wealth, Health & Relationships in 6 languages.",
        "history_today": "Today",
        "history_week": "This Week",
        "history_month": "This Month",
        "date_format": "%B %d, %Y",
        "nav_stats": "Statistics",
        "stats_title": "Divination Stats",
        "stats_total": "Total Casts",
        "stats_starred": "Starred",
        "stats_hex_dist": "Hexagram Distribution",
        "stats_cat_dist": "Question Type Distribution",
        "stats_method_dist": "Method Distribution",
        "stats_recent": "Recent Activity",
        "stats_times": "",
        "error_404": "Page Not Found",
        "error_403": "Access Denied",
        "error_500": "Server Error",
        "error_record_not_found": "Record Not Found",
        "wechat_title": "Open in Browser",
        "wechat_desc": "This page was opened in WeChat/QQ in-app browser. Some features may be limited. Please open in your system browser for the full experience.",
        "wechat_step": "1. Tap the ⋯ button at the top right<br>2. Select Open in Browser",
        "wechat_btn": "Got it",
        "random_question": "Quick Cast · Daily Fortune",
        "cat_random": "Random",
        "trend_arrow": "{h}… → {c}…",
        "cat_hints": {"love": "Love", "career": "Career", "wealth": "Wealth", "health": "Health", "people": "People", "random": "Daily Fortune", "general": "General Fortune"},
        "moving_hints": "{n} moving lines — significant changes ahead.",
        "aspect_names": {"love": "Love", "career": "Career", "wealth": "Wealth", "health": "Health", "travel": "People"},
        "moving_data": {
            "pos": ["1st Line", "2nd Line", "3rd Line", "4th Line", "5th Line", "6th Line"],
            "kin": ["Parents", "Siblings", "Wife/Wealth", "Children", "Officials", "Parents"],
            "dir_y": "Yang→Yin",
            "dir_n": "Yin→Yang",
            "meanings": {1: "Budding stage — foundation and beginning", 2: "Inner development — cultivation and accumulation", 3: "Transition — facing choices and tests", 4: "Near the throne — opportunity meets risk", 5: "Seat of power — core of career and leadership", 6: "Peak or turning point"},
            "sum_base": "{n} moving lines",
            "sum_1": " — focus concentrates on one point, direction is clear",
            "sum_2": " — two forces intertwine, balance is needed",
            "sum_3": " — many changes, complex situation, best to observe quietly",
            "sum_4": " — extreme variability, avoid major decisions now",
        },
    },
    "vi": {
        "app_title": "Quẻ Lục Hào",
        "nav_home": "Trang chủ",
        "nav_history": "Lịch sử",
        "btn_start": "Bắt đầu bói",
        "method_coin": "Gieo quẻ bằng đồng xu",
        "method_time": "Lấy thời gian hiện tại",
        "method_number": "Nhập số để gieo quẻ",
        "method_label": "Cách gieo quẻ",
        "number_placeholder": "Nhập số từ 0 đến 999",
        "question_label": "Câu hỏi / điều đang nghĩ",
        "question_placeholder": "Bạn có thể viết điều mình băn khoăn nhất, hoặc để trống chỉ xem vận thế chung.",
        "guide_title": "Lục Hào là gì?",
        "guide_intro": "Lục Hào (Liu Yao), còn gọi là Phong Thủy dự đoán hay Chu Dịch, là một trong những phương pháp bói cổ xưa nhất của Trung Quốc, có lịch sử hơn 3.000 năm. Hệ thống tạo ra 6 hào (dương hoặc âm) bằng cách gieo xu hoặc phương pháp ngẫu nhiên, tạo thành một trong 64 quẻ. Kết hợp hào động (hào thay đổi), ta có quẻ gốc (trạng thái hiện tại) và quẻ biến (hướng đi tương lai), từ đó luận giải xu hướng và cách ứng xử.",
        "guide_step1": "Hãy tập trung suy nghĩ về điều bạn muốn hỏi. Càng cụ thể càng tốt. Ví dụ: 'Công việc hiện tại có phù hợp với mình không?' hiệu quả hơn là 'Vận thế của mình thế nào?'",
        "guide_step2": "Chọn cách gieo quẻ: 'Gieo bằng đồng xu' mô phỏng phương pháp truyền thống, chính thống nhất; 'Lấy thời gian' dùng thời điểm hiện tại; 'Nhập số' cho phép bạn nhập con số để gieo.",
        "guide_step3": "Nhấn 'Bắt đầu bói', hệ thống sẽ tạo quẻ gốc (trạng thái hiện tại) và quẻ biến (hướng đi tương lai), kèm luận giải chi tiết từ 5 phương diện: Tình cảm, Sự nghiệp, Tài vận, Sức khỏe, Quan hệ.",
        "guide_note": "Lục Hào là công cụ tham khảo cho đời sống hàng ngày. Với quyết định quan trọng, hãy kết hợp kết quả với thực tế. Mỗi lần bói đều được lưu trong lịch sử để dễ dàng xem lại.",
        "result_title": "Kết quả",
        "hex_title_prefix": "Quẻ số ",
        "hex_title_suffix": "",
        "summary_notice": "Để luận quẻ chính xác cần kết hợp nội dung câu hỏi, Lục Thân và Dụng thần. Trang này chỉ đưa ra phần giải thích mang tính tham khảo cho đời sống hằng ngày.",
        "five_luck": "Năm phương diện",
        "love": "Tình cảm / Yêu đương",
        "career": "Công việc / Học tập",
        "wealth": "Tiền bạc / Tài vận",
        "health": "Sức khỏe",
        "travel": "Quan hệ / Đi lại",
        "now": "Hiện tại:",
        "future": "Tương lai:",
        "advice": "Gợi ý:",
        "history_title": "Lịch sử gieo quẻ",
        "history_id": "ID",
        "history_method": "Cách gieo",
        "history_question": "Câu hỏi",
        "history_hex": "Quẻ",
        "history_time": "Thời gian",
        "history_none": "Chưa có dữ liệu.",
        "method_name_coin": "Đồng xu",
        "method_name_time": "Thời gian",
        "method_name_number": "Con số",
        "nav_starred": "Đã lưu",
        "nav_gallery": "Sách 64 quẻ",
        "btn_random": "Bói nhanh",
        "btn_star": "Lưu",
        "btn_unstar": "Bỏ lưu",
        "category_label": "Loại câu hỏi",
        "cat_general": "Tổng quan",
        "cat_love": "Tình cảm",
        "cat_career": "Sự nghiệp",
        "cat_wealth": "Tài chính",
        "cat_health": "Sức khỏe",
        "cat_people": "Quan hệ",
        "moving_title": "Phân tích hào động",
        "moving_summary": "Gợi ý hào động",
        "trend_title": "Xu hướng quẻ biến",
        "share_title": "Chia sẻ kết quả",
        "nav_stats": "Thống kê",
        "stats_title": "Thống kê bói",
        "stats_total": "Tổng số lần bói",
        "stats_starred": "Số lần lưu",
        "stats_hex_dist": "Phân bố quẻ",
        "stats_cat_dist": "Phân bố loại câu hỏi",
        "stats_method_dist": "Phân bố phương pháp",
        "stats_recent": "Hoạt động gần đây",
        "stats_times": "lần",
        "daily_label": "Quẻ hôm nay",
        "btn_quick_cast": "Bói cho tôi",
        "coin_tossing": "Đang gieo quẻ…",
        "comparison_desc": "Sự thay đổi của từng phương diện từ quẻ gốc đến quẻ biến：",
        "label_original": "Quẻ gốc：",
        "label_changed": "Quẻ biến：",
        "btn_copy_share": "Sao chép nội dung chia sẻ",
        "btn_copy_link": "Sao chép liên kết",
        "share_hint": "Chỉ mang tính tham khảo. Chi tiết tại：",
        "copied_share": "✓ Đã sao chép nội dung chia sẻ",
        "copied_link": "✓ Đã sao chép liên kết",
        "gallery_desc": "Sách 64 quẻ đầy đủ — nhấn vào quẻ để bói",
        "stats_diff_hex": "quẻ khác nhau",
        "stats_total_diff": "Tổng cộng",
        "stats_diff_hex_unit": "quẻ đã bói",
        "stats_empty": "Chưa có dữ liệu. Hãy bói quẻ đầu tiên!",
        "theme_toggle": "Đổi giao diện",
        "hex_prefix": "Quẻ ",
        "hex_suffix": "",
        "original_hex": "Quẻ gốc",
        "changed_hex": "Quẻ biến",
        "glossary_title": "Thuật ngữ",
        "search_placeholder": "Tìm kiếm câu hỏi hoặc quẻ...",
        "go_cast": "Bắt đầu bói",
        "btn_save_image": "Lưu ảnh",
        "image_saved": "✓ Ảnh đã lưu",
        "btn_reminder": "Bật nhắc hằng ngày",
        "btn_reminder_off": "Tắt nhắc hằng ngày",
        "reminder_title": "Bói Lục Hào",
        "reminder_body": "Hôm nay bạn chưa bói. Hãy xem vận may hôm nay!",
        "reminder_not_supported": "Trình duyệt của bạn không hỗ trợ thông báo",
        "seo_description": "Quẻ Lục Hào — Phương pháp bói Chu Dịch cổ xưa. Phân tích Tình cảm, Sự nghiệp, Tài chính, Sức khỏe & Quan hệ bằng 6 ngôn ngữ.",
        "history_today": "Hôm nay",
        "history_week": "Tuần này",
        "history_month": "Tháng này",
        "date_format": "%d/%m/%Y",
        "error_404": "Không tìm thấy trang",
        "error_403": "Truy cập bị từ chối",
        "error_500": "Lỗi server",
        "error_record_not_found": "Không tìm thấy bản ghi",
        "wechat_title": "Mở trong trình duyệt",
        "wechat_desc": "Trang này đang được mở trong trình duyệt tích hợp của WeChat/QQ. Hãy mở trong trình duyệt hệ thống để có trải nghiệm đầy đủ.",
        "wechat_step": "1. Nhấn nút ⋯ ở góc trên bên phải<br>2. Chọn Mở trong trình duyệt",
        "wechat_btn": "Đã hiểu",
        "random_question": "Bói nhanh · Vận hôm nay",
        "cat_random": "Ngẫu nhiên",
        "trend_arrow": "{h}… → {c}…",
        "cat_hints": {"love": "Tình cảm", "career": "Sự nghiệp", "wealth": "Tài chính", "health": "Sức khỏe", "people": "Quan hệ", "random": "Vận hôm nay", "general": "Tổng quan"},
        "moving_hints": "{n} hào động — nhiều biến đổi sắp tới.",
        "aspect_names": {"love": "Tình cảm", "career": "Sự nghiệp", "wealth": "Tài chính", "health": "Sức khỏe", "travel": "Quan hệ"},
        "moving_data": {
            "pos": ["Hào sơ", "Hào nhị", "Hào tam", "Hào tứ", "Hào ngũ", "Hào thượng"],
            "kin": ["Phụ mẫu", "Huynh đệ", "Thê tài", "Tử tôn", "Quan quỷ", "Phụ mẫu"],
            "dir_y": "Dương→Âm",
            "dir_n": "Âm→Dương",
            "meanings": {1: "Giai đoạn nảy mầm — nền tảng và khởi đầu", 2: "Phát triển nội tại — tu dưỡng và tích lũy", 3: "Giai đoạn chuyển tiếp — đối mặt lựa chọn và thử thách", 4: "Vị trí gần vua — cơ hội và rủi ro cùng tồn tại", 5: "Vị trí quân — cốt lõi sự nghiệp và lãnh đạo", 6: "Đỉnh cao hoặc điểm chuyển"},
            "sum_base": "{n} hào động",
            "sum_1": " — tập trung vào một trọng tâm, hướng đi rõ ràng",
            "sum_2": " — hai lực lượng đan xen, cần cân nhắc",
            "sum_3": " — nhiều biến đổi, tình hình phức tạp, nên quan sát",
            "sum_4": " — biến số cực nhiều, không nên quyết định lớn",
        },
    },
    "ko": {
        "app_title": "육효 점",
        "nav_home": "홈",
        "nav_history": "기록",
        "btn_start": "점 보기",
        "method_coin": "동전 던지기 (전통)",
        "method_time": "시간으로 점 보기",
        "method_number": "숫자로 점 보기",
        "method_label": "점 방법",
        "number_placeholder": "0~999 사이 숫자를 입력하세요",
        "question_label": "질문 / 마음속 생각",
        "question_placeholder": "지금 가장 궁금한 것을 적어도 되고, 비워두면 운세만 봅니다.",
        "guide_title": "육효 점이란?",
        "guide_intro": "육효 점은 '주역 예측'이라고도 하며, 중국에서 3,000년 이상 된 가장 오래된 점술 중 하나입니다. 동전을 던지거나 임의의 방법으로 6개의 효(음효 또는 양효)를 생성하여 64괘 중 하나를 만듭니다. 동효(변하는 효)를 결합하여 본괘(현재 상태)와 변괘(미래 방향)를 얻고, 사물의 발전 경향과 대처법을 해석합니다.",
        "guide_step1": "묻고 싶은 것을 마음속으로 생각하세요. 구체적일수록 효과적입니다. 예: '지금 이 직업이 나한테 맞나요?'처럼.",
        "guide_step2": "점 방법을 선택하세요. '동전 던지기'는 전통적인 동전법으로 가장 정통, '시간으로 점 보기'는 현재 시간을 이용, '숫자로 점 보기'는 숫자를 입력합니다.",
        "guide_step3": "'점 보기'를 누르면 본괘(현재 상태)와 변괘(미래 방향)가 생성되고, 연애/직업/재운/건강/인간관계 5가지 방면에서 상세한 해석이 표시됩니다.",
        "guide_note": "육효 점은 일상생활 참고용 도구입니다. 중요한 결정은 현실 상황과 종합적으로 판단하세요. 매 점 결과는 기록되어 나중에 확인할 수 있습니다.",
        "result_title": "점 결과",
        "hex_title_prefix": "제",
        "hex_title_suffix": "효",
        "summary_notice": "정확한 해석을 위해서는 질문 내용, 육신, 용신 등을 종합적으로 판단해야 합니다. 이 페이지에서는 일상생활에 대한 참고용 해석을 제공합니다.",
        "five_luck": "오행 운세",
        "love": "연애 / 감정",
        "career": "직업 / 학업",
        "wealth": "재물 / 금전",
        "health": "건강",
        "travel": "인간관계 / 외출",
        "now": "현재:",
        "future": "미래:",
        "advice": "조언:",
        "history_title": "점 기록",
        "history_id": "ID",
        "history_method": "방법",
        "history_question": "질문",
        "history_hex": "괘",
        "history_time": "시간",
        "history_none": "아직 기록이 없습니다.",
        "method_name_coin": "동전",
        "method_name_time": "시간",
        "method_name_number": "숫자",
        "nav_starred": "즐겨찾기",
        "nav_gallery": "64괘 도감",
        "btn_random": "빠른 점",
        "btn_star": "즐겨찾기",
        "btn_unstar": "해제",
        "category_label": "질문 유형",
        "cat_general": "종합 운세",
        "cat_love": "연애",
        "cat_career": "직업",
        "cat_wealth": "재물",
        "cat_health": "건강",
        "cat_people": "인간관계",
        "moving_title": "동효 분석",
        "moving_summary": "동효의 시사점",
        "trend_title": "변괘 흐름",
        "share_title": "결과 공유",
        "nav_stats": "통계",
        "stats_title": "점 데이터",
        "stats_total": "총 점 횟수",
        "stats_starred": "즐겨찾기 수",
        "stats_hex_dist": "괘 분포",
        "stats_cat_dist": "질문 유형 분포",
        "stats_method_dist": "방법 분포",
        "stats_recent": "최근 활동",
        "stats_times": "",
        "daily_label": "오늘의 운세",
        "btn_quick_cast": "점 보여줘",
        "coin_tossing": "점 보는 중…",
        "comparison_desc": "본괘에서 변괘로의 각 운세 변화:",
        "label_original": "본괘: ",
        "label_changed": "변괘: ",
        "btn_copy_share": "공유 텍스트 복사",
        "btn_copy_link": "링크 복사",
        "share_hint": "참고용입니다. 자세한 내용:",
        "copied_share": "✓ 공유 텍스트가 복사되었습니다",
        "copied_link": "✓ 링크가 복사되었습니다",
        "gallery_desc": "64괘 완전 도감 — 괘를 눌러 점을 보세요",
        "stats_diff_hex": "가지 괘",
        "stats_total_diff": "총",
        "stats_diff_hex_unit": "가지 괘를 봤습니다",
        "stats_empty": "기록이 없습니다. 첫 번째 점을 보세요!",
        "theme_toggle": "테마 전환",
        "hex_prefix": "제",
        "hex_suffix": "효",
        "glossary_title": "용어 설명",
        "search_placeholder": "질문이나 괘를 검색...",
        "go_cast": "점 시작하기",
        "btn_save_image": "이미지 저장",
        "image_saved": "✓ 이미지가 저장되었습니다",
        "btn_reminder": "매일 알림 켜기",
        "btn_reminder_off": "매일 알림 끄기",
        "reminder_title": "육효 점",
        "reminder_body": "오늘 아직 점을 보지 않았습니다. 오늘의 운세를 확인하세요!",
        "reminder_not_supported": "브라우저가 알림을 지원하지 않습니다",
        "seo_description": "육효 점 — 중국 고대 주역 예측법. 연애/직업/재운/건강/인간관계 5가지 운세를 6개 언어로 분석.",
        "history_today": "오늘",
        "history_week": "이번 주",
        "history_month": "이번 달",
        "date_format": "%Y년 %m월 %d일",
        "original_hex": "본괘 (원래)",
        "changed_hex": "변괘 (변화 후)",
        "hex_overall": "괘 전체 해석",
        "error_404": "페이지를 찾을 수 없습니다",
        "error_403": "접근이 거부되었습니다",
        "error_500": "서버 오류",
        "error_record_not_found": "기록을 찾을 수 없습니다",
        "wechat_title": "브라우저에서 열어주세요",
        "wechat_desc": "微信/QQ 인앱 브라우저에서 열렸습니다. 시스템 브라우저에서 열어주세요.",
        "wechat_step": "1. 오른쪽 상단의 ⋯ 버튼을 누르세요<br>2. 브라우저에서 열기를 선택하세요",
        "wechat_btn": "알겠습니다",
        "random_question": "빠른 점 · 오늘의 운세",
        "cat_random": "랜덤",
        "trend_arrow": "{h}… → {c}…",
        "cat_hints": {"love": "연애", "career": "직업", "wealth": "재물", "health": "건강", "people": "인간관계", "random": "오늘의 운세", "general": "종합 운세"},
        "moving_hints": "동효 {n}개 — 큰 변화가 예상됩니다.",
        "aspect_names": {"love": "연애", "career": "직업", "wealth": "재물", "health": "건강", "travel": "인간관계"},
        "moving_data": {
            "pos": ["초효", "이효", "삼효", "사효", "오효", "상효"],
            "kin": ["부모", "형제", "처재", "자손", "관귀", "부모"],
            "dir_y": "양→음",
            "dir_n": "음→양",
            "meanings": {1: "싹트는 단계 — 기반과 시작", 2: "내적 발전기 — 수양과 축적", 3: "전환기 — 선택과 시련에 직면", 4: "군주 가까운 자리 — 기회와 공존", 5: "군위 — 사업의 핵심과 주도", 6: "극盛 또는 전환점"},
            "sum_base": "동효 {n}개",
            "sum_1": " — 사태가 하나의 초점에 집중, 변화 방향 명확",
            "sum_2": " — 두 힘이 얽혀있어 균형 필요",
            "sum_3": " — 변화가 많고 상황 복잡, 가만히 관찰하는 것이 좋음",
            "sum_4": " — 변수가 극히 많아 중대 결정은 피하는 것이 좋음",
        },
    },
}


def get_lang():
    if request.method == "POST":
        lang = request.form.get("lang")
    else:
        lang = request.args.get("lang")
    if lang not in LANGS:
        lang = "zh"
    return lang


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


@contextmanager
def db_connection():
    conn = get_db()
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                method TEXT,
                question TEXT,
                category TEXT DEFAULT '',
                hex_code INTEGER,
                lines TEXT,
                moving TEXT,
                liuchin TEXT,
                starred INTEGER DEFAULT 0,
                created_at TEXT
            )
            """
        )
        conn.commit()
    logger.info("Database initialized")


def migrate_db():
    with db_connection() as conn:
        cur = conn.cursor()
        migrations = [
            "ALTER TABLE history ADD COLUMN category TEXT DEFAULT ''",
            "ALTER TABLE history ADD COLUMN starred INTEGER DEFAULT 0",
        ]
        for sql in migrations:
            try:
                cur.execute(sql)
            except Exception:
                pass
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_history_created_at ON history(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_history_hex_code ON history(hex_code)",
            "CREATE INDEX IF NOT EXISTS idx_history_question ON history(question)",
            "CREATE INDEX IF NOT EXISTS idx_history_starred ON history(starred)",
        ]
        for idx_sql in indexes:
            cur.execute(idx_sql)
        conn.commit()
    logger.info("Database migration complete")


# ========== 起卦相关 ==========

def roll_coin_line():
    # 三个'硬币'，0/1 取奇偶做阴阳，0 或 3 当动爻
    total = sum(random.randint(0, 1) for _ in range(3))
    yang = 1 if total % 2 == 1 else 0
    moving = 1 if total in (0, 3) else 0
    return yang, moving


def make_lines(method, number=None):
    lines = []
    moving = []

    if method == "coin":
        for i in range(6):
            v, mv = roll_coin_line()
            lines.append(v)
            if mv:
                moving.append(i + 1)  # 1-based

    elif method == "time":
        now = datetime.now()
        seed = now.year * 31536000 + now.month * 2592000 + now.day * 86400 + now.hour * 3600 + now.minute * 60 + now.second + now.microsecond
        local_rng = random.Random(seed)
        for i in range(6):
            v = local_rng.randint(0, 1)
            lines.append(v)
        moving = [3]

    elif method == "number" and number is not None:
        s = str(abs(number))
        if not s:
            s = "0"
        for i in range(6):
            d = int(s[i % len(s)])
            v = d % 2
            lines.append(v)
        idx = sum(lines) % 6
        moving = [idx if idx != 0 else 6]

    else:
        for i in range(6):
            v = random.randint(0, 1)
            lines.append(v)
        moving = []

    return lines, moving


def lines_to_code(lines):
    code = 0
    for i, v in enumerate(lines):
        if v:
            code |= (1 << i)
    return code


def calc_liuchin(lines, lang="zh"):
    t = TEXTS.get(lang, TEXTS["zh"])
    return t.get("moving_data", {}).get("kin", ["Parents", "Siblings", "Wife/Wealth", "Children", "Officials", "Parents"])


def calc_changed_lines(lines, moving):
    """Calculate the changed hexagram by flipping moving lines."""
    changed = list(lines)
    for m in moving:
        idx = int(m) - 1  # 0-based
        if 0 <= idx < 6:
            changed[idx] = 1 - changed[idx]  # flip yin/yang
    return changed


def analyze_moving_lines(lines, moving, lang="zh"):
    if not moving:
        return {"has_moving": False, "count": 0, "details": []}

    t = TEXTS.get(lang, TEXTS["zh"])
    d = t.get("moving_data", TEXTS["zh"]["moving_data"])

    details = []
    for m in moving:
        pos = int(m)
        idx = pos - 1
        yang = lines[idx]
        details.append({
            "position": pos,
            "name": d["pos"][idx],
            "meaning": d["meanings"].get(pos, ""),
            "kin": d["kin"][idx],
            "direction": d["dir_y"] if yang else d["dir_n"],
        })

    summary = d["sum_base"].format(n=len(moving))
    if len(moving) == 1:
        summary += d["sum_1"]
    elif len(moving) == 2:
        summary += d["sum_2"]
    elif len(moving) == 3:
        summary += d["sum_3"]
    else:
        summary += d["sum_4"]

    return {"has_moving": True, "count": len(moving), "details": details, "summary": summary}


def build_trend_analysis(hex_code, changed_code, moving_count):
    hex_interp = INTERPRETATIONS.get(hex_code, {})
    changed_interp = INTERPRETATIONS.get(changed_code, {})

    trend = {}
    for lang in LANGS:
        t = TEXTS.get(lang, TEXTS["zh"])
        h_desc = hex_interp.get("overall", {}).get("desc", {}).get(lang, "")
        c_desc = changed_interp.get("overall", {}).get("desc", {}).get(lang, "")

        if lang == "zh":
            if h_desc and c_desc and h_desc != c_desc:
                trend[lang] = t.get("trend_zh_from", "").format(h=h_desc[:30], c=c_desc[:30])
            elif h_desc:
                trend[lang] = t.get("trend_zh_stable", "").format(h=h_desc[:50])
            else:
                trend[lang] = t.get("trend_zh_default", "")
        else:
            arrow = t.get("trend_arrow", "{h}… → {c}…")
            if h_desc and c_desc and h_desc != c_desc:
                trend[lang] = arrow.format(h=h_desc[:40], c=c_desc[:40])
            elif h_desc:
                trend[lang] = h_desc[:80] + "…" if len(h_desc) > 80 else h_desc
            else:
                trend[lang] = ""

    return trend


def get_daily_fortune(lang="zh"):
    """Generate today's fortune based on date seed."""
    today = datetime.now()
    seed = today.year * 10000 + today.month * 100 + today.day
    rng = random.Random(seed)
    hex_code = rng.randint(0, 63)
    interp = INTERPRETATIONS.get(hex_code, {})
    overall = interp.get("overall", {})
    title = overall.get("title", {})
    desc = overall.get("desc", {})
    t = TEXTS.get(lang, TEXTS["en"])
    date_fmt = t.get("date_format", "%Y-%m-%d")
    date_str = today.strftime(date_fmt)
    return {
        "hex_code": hex_code,
        "hex_no": hex_code + 1,
        "title": title,
        "desc": desc,
        "date": date_str,
    }


def build_summary(hex_code, lines, moving, category, lang="zh"):
    interp = INTERPRETATIONS.get(hex_code, {})
    overall_title = interp.get("overall", {}).get("title", {})
    overall_desc = interp.get("overall", {}).get("desc", {})

    t = TEXTS.get(lang, TEXTS["zh"])
    cat_hints = t.get("cat_hints", {})
    moving_hints = t.get("moving_hints", "")

    title_text = overall_title.get(lang, overall_title.get("zh", ""))
    desc_text = overall_desc.get(lang, overall_desc.get("zh", ""))
    first_sentence = desc_text.split("。")[0] + "。" if lang == "zh" else desc_text.split(".")[0].strip() + "." if desc_text else ""
    cat_hint = cat_hints.get(category, cat_hints.get("general", ""))
    moving_hint = moving_hints.format(n=len(moving)) if moving else ""

    summary_punct = {
        "zh": ("【", "】", "："),
        "ja": ("【", "】", "："),
        "en": ("[", "]", " - "),
        "vi": ("[", "]", " - "),
        "ko": ("[", "]", " - "),
        "my": ("[", "]", " - "),
    }
    lp, rp, sep = summary_punct.get(lang, summary_punct["en"])
    summary = f"{lp}{title_text}{rp}{cat_hint}{sep}{first_sentence}"
    if moving_hint:
        summary += moving_hint
    return summary[:150]


def build_fortune_comparison(hex_code, changed_code):
    """Compare per-fortune readings between 本卦 and 变卦 for each aspect."""
    hex_interp = INTERPRETATIONS.get(hex_code, {})
    changed_interp = INTERPRETATIONS.get(changed_code, {})

    if hex_code == changed_code:
        return None

    aspects = ["love", "career", "wealth", "health", "travel"]
    aspect_names = {}
    for l in LANGS:
        lt = TEXTS.get(l, TEXTS["zh"])
        aspect_names[l] = lt.get("aspect_names", {})

    comparison = {}
    for lang in ["zh", "ja", "en", "vi", "ko", "my"]:
        items = []
        for asp in aspects:
            h_desc = hex_interp.get(asp, {}).get("desc", {}).get(lang, "")
            c_desc = changed_interp.get(asp, {}).get("desc", {}).get(lang, "")
            if not h_desc:
                h_desc = hex_interp.get(asp, {}).get("desc", {}).get("en", "")
            if not c_desc:
                c_desc = changed_interp.get(asp, {}).get("desc", {}).get("en", "")
            if not h_desc:
                h_desc = hex_interp.get(asp, {}).get("desc", {}).get("zh", "")
            if not c_desc:
                c_desc = changed_interp.get(asp, {}).get("desc", {}).get("zh", "")
            name = aspect_names[lang].get(asp, asp)
            if h_desc and c_desc and h_desc != c_desc:
                items.append({
                    "name": name,
                    "from_text": h_desc[:80] + "…" if len(h_desc) > 80 else h_desc,
                    "to_text": c_desc[:80] + "…" if len(c_desc) > 80 else c_desc,
                })
        comparison[lang] = items

    return comparison


# ========== 运势解析 ==========

def build_analysis(lines, moving, liuchin, hex_code):
    interp = INTERPRETATIONS.get(hex_code, {})

    if moving:
        focus_idx = max(1, min(6, int(moving[0])))
    else:
        focus_idx = 3
    focus_kin = liuchin[focus_idx - 1] if 0 <= focus_idx - 1 < len(liuchin) else "用神"

    LANG_KEYS = ["zh", "ja", "en", "vi", "ko"]

    def L(zh, ja, en, vi, ko, my=None):
        if my is None:
            my = zh
        return {"zh": zh, "ja": ja, "en": en, "vi": vi, "ko": ko, "my": my}

    def block(title, now, future, advice):
        return {"title": title, "now": now, "future": future, "advice": advice}

    # ===== 恋爱 / 感情 =====
    love_core = interp.get("love", {})
    love_desc = love_core.get("desc", {})
    love_title = love_core.get("title", {})

    love_now_extra = L(
        f"\n\n从卦象来看，你目前的感情状态受到「{focus_kin}」的影响较大。这意味着你的情感走向与现实环境密不可分——比如工作压力、经济状况、家庭背景等因素都在间接影响着你的感情生活。建议你先理清这些外在因素，再去看感情本身。"
        f"\n\n具体来说：如果你是单身，目前的社交圈可能比较固定，需要主动拓展接触面，比如参加兴趣班、朋友聚会或线上社交活动；如果你正在暧昧期，对方的态度可能还不够明确，不妨多观察一段时间；如果你已有伴侣，最近可能因为琐事产生小摩擦，但只要双方愿意沟通，问题不大。",
        f"\n\n卦から見ると、今の恋愛運は「{focus_kin}」の影響を強く受けています。感情の動きが現実の環境（仕事・経済・家族など）と深く結びついている状態です。まずこれらの外的要因を整理してから、感情そのものを見つめ直すことが大切です。"
        f"\n\n具体的には：独身の方は現在の交友関係が固定されがちなので、趣味の教室や友人の集まり、オンライン交流など場を広げましょう。曖昧な関係にある方は、相手の様子をもう少し観察する時間を設けてください。パートナーがいる方は、些細なことでぶつかるかもしれませんが、話せば解決する問題です。",
        f"\n\nLooking at the hexagram, your current love situation is strongly influenced by the '{focus_kin}' line. This means your emotional state is deeply connected to practical circumstances — work stress, finances, family background all play a role. Try to sort out these external factors before examining the relationship itself."
        f"\n\nSpecifically: if you're single, your social circle may be quite fixed — consider joining classes, attending friend gatherings, or trying online social platforms. If you're in an ambiguous stage, give it more time and observe. If you're in a relationship, small frictions from daily life are normal, but open communication resolves them quickly.",
        f"\n\nNhìn vào quẻ, tình cảm hiện tại chịu ảnh hưởng lớn của '{focus_kin}'. Cảm xúc gắn liền với hoàn cảnh thực tế — áp lực công việc, tài chính, gia đình đều ảnh hưởng gián tiếp. Hãy giải quyết các yếu tố bên ngoài trước khi nhìn vào chuyện tình cảm."
        f"\n\nCụ thể: nếu độc thân, vòng tròn quan hệ hiện tại khá cố định, cần chủ động mở rộng — lớp học sở thích, tụ tập bạn bè, mạng xã hội. Nếu đang ở giai đoạn mập mờ, hãy quan sát thêm. Nếu đã có partner, bất đồng nhỏ từ cuộc sống hàng ngày là bình thường, chỉ cần chịu nói chuyện là giải quyết được.",
        f"\n\n괘를 보면 현재 연애운은 '{focus_kin}'의 영향을 크게 받습니다. 감정이 현실 상황(업무, 경제, 가족 등)과 깊게 연결되어 있습니다. 이러한 외적 요인을 정리한 후 감정을 바라보는 것이 중요합니다."
        f"\n\n구체적으로: 솔로라면 현재 교제 범위가 고정되기 쉬우니 관심사 모임, 친구 모임, 온라인 소셜 등 범위를 넓혀보세요. 애매한 관계라면 좀 더 관찰하는 시간을 가지세요. 파트너가 있다면 사소한 마찰이 있을 수 있지만 대화로 해결할 수 있습니다.",
        f"\n\nဗေဒမှကြည့်ပါက သင့်ချစ်ခြင်းမေတ္တာအခြေအနေသည် 「{focus_kin}」 ၏ သက်ရောက်မှုကြီးမားပါသည်။ သင့်စိတ်ခံစားမှုသည် လက်တွေ့အခြေအနေနှင့် ချိတ်ဆက်နေပါသည် — အလုပ်ဖိအား၊ ငွေကြေး၊ မိသားစုနောက်ခံတို့က သင့်ချစ်ခြင်းဘဝကို သက်ရောက်နေပါသည်။ ဒီအပြင်ပိုင်းအချက်အလက်များကို ရှင်းလင်းပြီးမှ ချစ်ခြင်းမေတ္တာကို ကြည့်ပါ။"
        f"\n\nအသေးစိတ်အားဖြင့် — လက်ထပ်မထိတ်သေးသူများ: သင့်လူမှုဆက်ဆံရေးသည် အကျပ်အတည်းဖြစ်နိုင်ပါသည်၊ ဝါသနာအုပ်စုများ၊ မိတ်ဆွေစုဝေးပွဲများ စသည်တို့ကို တက်ကြွစွာ တက်ရောက်ပါ။ ချစ်သူရှိသူများ: လောလောဆယ် သေးငယ်သည့်ကိစ္စများကြောင့် ပဋိပက္ခဖြစ်နိုင်ပါသည်၊ သို့သော် စကားပြောဆိုပါက ဖြေရှင်းနိုင်ပါသည်။",
    )

    love_future_extra = L(
        f"\n\n在接下来的一段时间里，你的感情运会呈现「{focus_kin}」所暗示的趋势。"
        f"\n\n• 如果目前感情稳定，未来会进入一个需要「做选择」的阶段——可能是确认关系、见家长、讨论未来规划等。这个选择不需要着急，但也不能一直回避。"
        f"\n• 如果目前感情有波动，未来会逐渐趋于明朗。那些让你犹豫不决的因素会慢慢浮出水面，帮你做出判断。"
        f"\n• 桃花运方面，近期可能会通过工作关系、朋友介绍或社交场合遇到有好感的人。但要注意分辨对方是真心还是只是一时新鲜感。"
        f"\n• 复合的可能性：如果是问旧情，卦象暗示有机会但需要双方都有诚意，单方面的付出不够。",
        f"\n\n今後の恋愛運は「{focus_kin}」が示す流れに沿って展開します。"
        f"\n\n• もし今の関係が安定しているなら、「選択を迫られる」段階が来ます。交際の確定、家族への挨拶、将来の話など。急ぐ必要はありませんが、先送りにしすぎないでください。"
        f"\n• もし今の関係に不安定さがあるなら、少しずつはっきりしてくるでしょう。迷わせていた要因が浮き彫りになり、判断の助けになります。"
        f"\n• 新しい出会い方面では、仕事や友人紹介、社交の場で気になる人に出会う可能性があります。ただし、本心か一時的な新鮮感かを見分けてください。"
        f"\n• 複縁については、双方に诚意があれば可能性があります。一方的な努力だけでは不十分です。",
        f"\n\nIn the coming period, your love fortune will follow the trend indicated by the '{focus_kin}' line."
        f"\n\n• If your relationship is stable, you'll enter a phase requiring choices — defining the relationship, meeting families, discussing future plans. No rush, but don't keep avoiding it either."
        f"\n• If there's been uncertainty, things will gradually become clearer. The factors that confused you will surface and help you decide."
        f"\n• For new romance, you may meet someone interesting through work, friends, or social events. But distinguish genuine interest from fleeting novelty."
        f"\n• For reconciliation: there's a chance if both parties are sincere, but one-sided effort isn't enough.",
        f"\n\nTrong thời gian tới, vận tình cảm sẽ theo xu hướng mà '{focus_kin}' chỉ ra."
        f"\n\n• Nếu tình cảm ổn định, giai đoạn cần「đưa ra lựa chọn」sẽ đến — xác nhận mối quan hệ, ra mắt gia đình, nói về tương lai. Không cần vội, nhưng cũng đừng trì hoãn mãi."
        f"\n• Nếu có bất ổn, mọi thứ sẽ dần rõ ràng hơn. Những yếu tố gây do dự sẽ nổi lên giúp bạn phán đoán."
        f"\n• Về nhân duyên mới, có thể gặp người thiện cảm qua công việc, giới thiệu bạn bè hoặc các buổi giao lưu. Nhưng phân biệt thật giả."
        f"\n• Về quay lại với người cũ: có khả năng nếu cả hai đều chân thành, nhưng nỗ lực một phía thì không đủ.",
        f"\n\n앞으로 연애운은 '{focus_kin}'이 보여주는 흐름을 따를 것입니다."
        f"\n\n• 현재 관계가 안정적이라면「선택을 요구하는」단계가 올 것입니다. 교제 확정, 가족 소개, 미래 이야기 등. 서두를 필요는 있지만 너무 미루지도 마세요."
        f"\n• 현재 불안정하다면 점차 명확해질 것입니다. 망설이게 했던 요인들이 드러나 판단에 도움이 됩니다."
        f"\n• 새 인연의 경우, 업무나 친구 소개, 모임에서 호감 가는 사람을 만날 수 있습니다. 하지만 진심인지 일시적인 신선함인지 구별하세요."
        f"\n• 재결합의 경우, 양쪽 모두 진심이면 가능성이 있지만 일방적인 노력으로는 부족합니다.",
        f"\n\nနောက်ထပ်ကာလတွင် သင့်ချစ်ခြင်းကံသည် '{focus_kin}' ၏ လမ်းညွှန်ချက်အတိုင်း ဖွံ့ဖြိုးလာမည်ဖြစ်သည်။"
        f"\n\n• လက်ရှိဆက်ဆံရေးတည်ငြိမ်ပါက၊ ဆုံးဖြတ်ချက်ချရမည့်အဆင့်သို့ ရောက်လာနိုင်ပါသည် — ဆက်ဆံရေးအတည်ပြုခြင်း၊ မိသားစုနှင့်တွေ့ခြင်း၊ အနာဂတ်အစီအစဉ်များဆွေးနွေးခြင်း စသည်တို့ဖြစ်သည်။ အလျင်စလိုမလုပ်ပါနှင့်၊ သို့သော် အမြဲတမ်းရှောင်ဖယ်နေလည်းမဖြစ်ပါ။"
        f"\n• လက်ရှိဆက်ဆံရေးတွင် မတည်ငြိမ်မှုရှိပါက၊ တဖြည်းဖြည်း ပို၍ရှင်းလင်းလာပါမည်။ သံသယဖြစ်စေသည့် အကြောင်းရင်းများ ပေါ်လာပြီး ဆုံးဖြတ်ချက်ချရာတွင် ကူညီပါမည်။"
        f"\n• ဆွေမျိုးသားချင်းအသစ်များအတွက်၊ အလုပ်၊ မိတ်ဆွေများမှတစ်ဆင့် သို့မဟုတ် လူမှုဆက်ဆံရေးတွင် စိတ်ဝင်စားဖွယ်လူတစ်ယောက်ကို တွေ့နိုင်ပါသည်။ သို့သော် စစ်မှန်သည့်စိတ်ဆန္ဒလား ရက်ရောမှုလား ခွဲခြမ်းစိတ်ဖြာပါ။"
        f"\n• ပြန်လည်ဆက်ဆံရေးအတွက်၊ နှစ်ဖက်စလုံး စစ်မှန်ပါက အခွင့်အရေးရှိသော်လည်း တစ်ဖက်တည်းက ကြိုးစားမှုဖြင့်မလုံလောက်ပါ။"
    )

    love_adv_extra = L(
        f"\n\n【具体行动建议】"
        f"\n\n1. 主动但不急躁：如果对某人有好感，可以主动约对方出来喝杯咖啡或参加共同活动，但不要一上来就表白或追问「我们是什么关系」。"
        f"\n2. 提升自身吸引力：这段时间适合把注意力放回自己身上——健身、读书、学新技能。当你变得更好时，自然会吸引到更匹配的人。"
        f"\n3. 沟通技巧：有伴侣的朋友，遇到分歧时试着用「我感觉……」而不是「你总是……」来表达。前者让对方愿意听，后者只会引发防御。"
        f"\n4. 红旗警示：如果对方长期不回复消息、总是找借口拒绝见面、或言行不一致，这可能是不够重视你的信号，需要认真评估这段关系。"
        f"\n5. 吉利信号：对方主动分享日常、记住你说过的小事、在你需要时出现——这些都是好感的积极迹象。",
        f"\n\n【具体的アクションアドバイス】"
        f"\n\n1. 主動的に、でも急がずに：気になる人がいたら、お茶や共通のイベントに誘いましょう。すぐに告白したり「何の関係？」と聞くのは避けて。"
        f"\n2. 自分磨き：今の時期は自分自身に注目——ジム、読書、新しいスキル。自分が良くなれば、自然と良い相手が引き寄せられます。"
        f"\n3. コミュニケーション術：パートナーとの意見の違いは「私はこう感じた」 instead of「あなたはいつも……」で伝えてください。前者は聞き入れられ、後者は拒絶反応を起こします。"
        f"\n4. 赤旗シグナル：相手が長時間返信しない、会うのをいつも断る、言行が一致しない——これはあなたを大切にしていないサインかもしれません。"        
        f"\n5. 好印象シグナル：相手から日常を共有してくる、あなたが言った小さなことを覚えて、必要な時にいてくれる——これらはすべて好意のサインです。",
        f"\n\n【Specific Action Advice】"
        f"\n\n1. Be proactive but not pushy: If you're interested in someone, suggest meeting for coffee or a shared activity. Don't confess feelings or ask 'what are we?' too early."
        f"\n2. Work on yourself: This is a great time to focus on self-improvement — exercise, reading, new skills. When you become your best self, you naturally attract better matches."
        f"\n3. Communication tips: When disagreeing with a partner, try 'I feel...' instead of 'You always...'. The former invites listening; the latter triggers defensiveness."
        f"\n4. Red flags: If someone consistently doesn't reply, makes excuses to avoid meeting, or their words don't match their actions — they may not value you enough. Reassess seriously."
        f"\n5. Positive signs: They share their day with you, remember small things you said, show up when you need them — these are genuine signs of interest.",
        f"\n\n【Hành động cụ thể】"
        f"\n\n1. Chủ động nhưng không vội vàng: Nếu thích ai đó, rủ đi uống cà phê hoặc tham gia hoạt động chung. Đừng tỏ tình ngay hoặc hỏi \"mối quan hệ của mình là gì\" quá sớm."
        f"\n2. Nâng cao bản thân: Giai đoạn này phù hợp tập trung vào mình — tập gym, đọc sách, học kỹ năng mới. Khi bạn tốt hơn, tự nhiên sẽ thu hút người phù hợp."
        f"\n3. Kỹ năng giao tiếp: Khi bất đồng với partner, thử nói \"cảm xúc của tôi là...\" thay vì \"bạn luôn...\". Cái trước khiến người ta muốn nghe, cái sau chỉ gây phản kháng."
        f"\n4. Dấu hiệu cảnh báo: Nếu người kia thường xuyên không trả lời tin nhắn, luôn tìm cớ từ chối gặp mặt, hoặc lời nói không đi đôi với hành động — có thể họ không coi trọng bạn enough. Hãy đánh giá lại nghiêm túc."
        f"\n5. Dấu hiệu tích cực: Họ chủ động chia sẻ ngày của họ, nhớ những điều nhỏ bạn nói, xuất hiện khi bạn cần — đó là dấu hiệu tốt đẹp.",
        f"\n\n【구체적인 행동 조언】"
        f"\n\n1. 주도적이되 서두르지 마세요: 호감 가는 사람이 있다면 커피나 공동 활동에 초대하세요. 바로 고백하거나 \"우리 관계가 뭐냐\"고 묻는 것은 피하세요."
        f"\n2. 자기 계발: 이 시기는 자신에게 집중하기 좋습니다 — 헬스, 독서, 새로운 기술. 자신이 좋아지면 자연스럽게 좋은 상대를 끌어들입니다."
        f"\n3. 소통 기술: 파트너와 의견이 다를 때 \"내가 이렇게 느꼈어\"라고 말하세요. \"너는 항상...\"이 아닙니다. 전자는 경청을 유도하고 후자는 방어 반응을 일으킵니다."
        f"\n4. 경고 신호: 상대가 항상 답장을 안 하고, 만나는 것을 거부하고,言行不一致하면 — 당신을 충분히 소중히 여기지 않는 신호일 수 있습니다. 진지하게 재평가하세요."
        f"\n5. 긍정 신호: 상대가 일상을 공유하고, 당신이 말한 작은 것을 기억하고, 필요할 때 나타나면 — 그것이 진정한 호감의 신호입니다.",
        f"\n\n【လက်တွေ့လုပ်ဆောင်ရန် အကြံပြုချက်များ】"
        f"\n\n၁။ တက်ကြွစွာပြုလုပ်ပါ၊ သို့သော် အလျင်စလိုမလုပ်ပါနှင့် — စိတ်ဝင်စားသည့်သူရှိပါက ကော်ဖီသောက်ဖို့ သို့မဟုတ် အတူတကွလုပ်ဆောင်စရာရှိသည်ကို ဖိတ်ကြားပါ။ ချစ်သူဖြစ်ကြောင်း ချက်ချင်းဝန်ခံခြင်း သို့မဟုတ် 'ကျွန်တော်/ကျွန်မတို့ ဘာဖြစ်တာလဲ'ဟု မမေးပါနှင့်။"
        f"\n၂။ ကိုယ့်ကိုယ်ကို တိုးတက်အောင်လုပ်ပါ — ဤအချိန်သည် ကိုယ်တိုင်အားဖြင့် အာရုံစိုက်ရန် သင့်တော်သည်။ အားကစားလုပ်ခြင်း၊ စာဖတ်ခြင်း၊ အသစ်သောကျွမ်းကျင်မှုများသင်ယူခြင်း စသည်တို့ဖြင့် ကိုယ့်ကိုယ်ကို ပိုကောင်းအောင်လုပ်ပါ။ သင်ပိုကောင်းလာသည်နှင့်အမျှ ပိုတိကျသည့်လူကို ဆွဲဆောင်နိုင်ပါမည်။"
        f"\n၃။ ဆက်သွယ်ရေးနည်းစနစ် — ချစ်သူနှင့် သဘောထားကွဲလွဲသည့်အခါ 'ကျွန်တော်/ကျွန်မ ခံစားရတာ...'ဟု ပြောပါ။ 'သင်က အမြဲတမ်း...'ဟု မပြောပါနှင့်။ ပထမက နားထောင်ချင်စေပြီး၊ ဒုတိယက ခုခံစိတ်ဖြစ်စေပါသည်။"
        f"\n၄။ သတိပေးချက် — အကယ်၍ ဆန့်ကျင်ဘက်က အမြဲတမ်း စာတုံ့ပြန်ခြင်းမရှိ၊ တွေ့ဆုံခြင်းကို အကြောင်းပြချက်ဖြင့်ငြင်းဆို၊ သို့မဟုတ် စကားနှင့်လုပ်ရပ်မတည် — ၎င်းသည် သင့်ကို လုံလောက်စွာ အရေးစိုက်ခြင်းမရှိကြောင်း အချက်ပြနေနိုင်ပါသည်။ ဤဆက်ဆံရေးကို အလေးအနက် ပြန်လည်သုံးသပ်ပါ။"
        f"\n၅။ ကောင်းသည့်လက္ခဏာများ — ဆန့်ကျင်ဘက်က သင့်နေ့စဉ်ဘဝကို မျှဝေ၊ သင်ပြောခဲ့သည့် အသေးအဖွဲ့ကို မှတ်မိ၊ သင့်လိုအပ်ချက်ရှိသည့်အခါ ရောက်လာပါက — ၎င်းတို့သည် စစ်မှန်သည့် စိတ်ဝင်စားမှု လက္ခဏာများဖြစ်သည်။"
    )

    analysis = {}
    analysis["love"] = block(
        L(love_title.get("zh", "恋爱 / 感情"), love_title.get("ja", "恋愛・感情"),
          love_title.get("en", "Love / Relationship"), love_title.get("vi", "Tình cảm / Yêu đương"),
          love_title.get("ko", "연애 / 감정"), love_title.get("my", "ချစ်ခြင်းမေတ္တာ")),
        L(love_desc.get("zh", "") + love_now_extra["zh"], love_desc.get("ja", "") + love_now_extra["ja"],
          love_desc.get("en", "") + love_now_extra["en"], love_desc.get("vi", "") + love_now_extra["vi"],
          love_desc.get("ko", "") + love_now_extra["ko"], love_desc.get("my", "") + love_now_extra["my"]),
        love_future_extra,
        love_adv_extra,
    )

    # ===== 工作 / 学业 =====
    career_core = interp.get("career", {})
    career_desc = career_core.get("desc", {})
    career_title = career_core.get("title", {})

    career_now_extra = L(
        f"\n\n从事业运势来看，你目前的工作/学业状态与「{focus_kin}」有密切关系。"
        f"\n\n• 如果你是上班族：最近可能面临项目截止、考核评估或人事变动的压力。卦象提醒你不要单打独斗，学会借助团队力量。遇到困难时主动向上级或同事求助，不是示弱而是聪明。"
        f"\n• 如果你是学生：学习上可能遇到了瓶颈，觉得努力了但成绩没有明显提升。这是正常的积累期，坚持下去会有突破。建议换个学习方法，比如从被动听课变为主动做笔记、画思维导图。"
        f"\n• 如果你在创业或自由职业：当前的业务增长可能不如预期，但方向是对的。不要因为短期波动而频繁调整策略，稳定执行比反复改变更重要。"
        f"\n• 如果你在找工作：简历投出去后回复较少是正常现象，不代表你不够好。可能是竞争激烈，也可能是你的简历没有突出亮点。建议请朋友帮忙看看简历，或者找行业内的人做内推。",
        f"\n\n事業運来看ると、今の仕事・学業は「{focus_kin}」と深く関係しています。"
        f"\n\n• 会社員の方：プロジェクトの締め切り、評価、人事異動などのプレッシャーがあるかもしれません。一人で抱え込まず、チームの力を借りましょう。困った時は上司や同僚に相談——それは弱さではなく賢さです。"
        f"\n• 学生の方：勉強のボトルネックに当たっているかもしれません。努力しているのに成績が上がらない——これは正常な蓄積期です。勉強法を変えてみましょう。受動的な聴講から、能動的なノート取りやマインドマップへ。"
        f"\n• 起業・フリーランスの方：今のビジネス成長は期待ほどではないかもしれませんが、方向性は正しいです。短期の変動で頻繁に戦略を変えず、安定した執行が大切です。"
        f"\n• 求職中の方：履歴書を出したのに返信が少ないのは正常現象です。競争が激しいか、履歴書に目立つポイントがないのかもしれません。友人に履歴書を見てもらったり、業界の人への推薦をお願いしてみましょう。",
        f"\n\nFrom a career perspective, your current work/study situation is closely tied to the '{focus_kin}' line."
        f"\n\n• If you're employed: You may face project deadlines, performance reviews, or organisational changes. Don't try to handle everything alone — leverage your team. Asking for help isn't weakness; it's wisdom."
        f"\n• If you're a student: You might hit a study plateau where effort doesn't show in grades. This is a normal accumulation phase — keep going. Try changing methods: from passive listening to active note-taking, mind maps, or teaching others."
        f"\n• If you're freelancing or running a business: Growth may be slower than expected, but the direction is right. Don't keep pivoting due to short-term fluctuations. Consistent execution beats constant changes."
        f"\n• If you're job hunting: Few replies to applications is normal — it doesn't mean you're not good enough. Competition is fierce, or your CV may not stand out. Ask friends to review your CV or seek internal referrals.",
        f"\n\nNhìn vào vận sự nghiệp, công việc/học tập hiện tại liên quan mật thiết đến '{focus_kin}'."
        f"\n\n• Nếu bạn là nhân viên: Có thể đối mặt áp lựcdeadline, đánh giá nhân sự. Đ đừng ôm đồm một mình, học cách nhờ team giúp đỡ. Gặp khó khăn chủ động nhờ cấp trên hoặc đồng nghiệp — đó là sự thông minh, không phải yếu đuối."
        f"\n\n• Nếu bạn là sinh viên: Có thể gặp bottleneck, cố gắng mà điểm không cải thiện. Đây là giai đoạn tích lũy bình thường, kiên trì sẽ có đột phá. Thử đổi phương pháp học — từ nghe thụ động sang ghi chép chủ động, sơ đồ tư duy."
        f"\n• Nếu bạn tự kinh doanh hoặc freelance: Tăng trưởng hiện tại có thể chưa như mong đợi, nhưng hướng đi đúng. Đừng frequently điều chỉnh chiến lược vì biến động ngắn hạn, thực thi ổn định quan trọng hơn."
        f"\n• Nếu bạn đang tìm việc: Ít phản hồi CV là hiện tượng bình thường, không có nghĩa bạn không giỏi. Có thể đối thủ mạnh hoặc CV chưa nổi bật. Nhờ bạn bè xem CV hoặc tìm người giới thiệu nội bộ.",
        f"\n\n직업운을 보면 현재 업무나 학업이 '{focus_kin}'과 깊게 연결되어 있습니다."
        f"\n\n• 직장인이라면: 프로젝트 마감, 인사 평가, 조직 변경 등의 압박이 있을 수 있습니다. 혼자 떠안지 말고 팀의 힘을 빌리세요. 어려울 때 상사나 동료에게 상담하는 것은 약함이 아니라 지혜입니다."
        f"\n\n• 학생이라면: 공부 플래이트에 부딪혔을 수 있습니다. 노력해도 성적이 안 오르면 정상적인 축적 기간입니다. 공부법을 바꿔보세요 — 수동적 청강에서 능동적 노트 작성, 마인드맵으로."
        f"\n• 프리랜서나 사업자라면: 현재 성장이 기대에 미치지 못할 수 있지만 방향은 맞습니다. 단기 변동 때문에 전략을 자주 바꾸지 마세요. 일관된 실행이 중요합니다."
        f"\n• 구직 중이라면: 지원서에 대한 회신이 적은 것은 정상입니다. 당신이 부족하다는 뜻이 아닙니다. 경쟁이 치열하거나 이력서가 눈에 띄지 않을 수 있습니다. 친구에게 이력서를 봐달라고 하거나 내부 추천을 구하세요.",
        f"\n\nအလုပ်/ပညာရေးအခြေအနေကို ကြည့်ပါက 「{focus_kin}」နှင့် နက်ရှိုင်းစွာ ချိတ်ဆက်နေပါသည်။"
        f"\n\n• ဝန်ထမ်းများ: စီမံကိန်း သတ်မှတ်ချက်၊ အကဲဖြတ်ခြင်း ဖိအားများ ရှိနိုင်ပါသည်။ တစ်ယောက်တည်း မလုပ်ပါနှင့်၊ အဖွဲ့၏ အင်အားကို အသုံးပြုပါ။ အခက်အခဲဖြစ်သောအခါ အထက်အရာရှိ သို့မဟုတ် လုပ်ဖော်ဆွေများထံ အကူအညီတောင်းပါ — ဒါသည် အားနည်းခြင်းမဟုတ်ဘဲ ပညာရှိခြင်းဖြစ်ပါသည်။"
        f"\n• ကျောင်းသားများ: ပညာရေးတွင် အတားအဆီးတစ်ခု ကြုံတွေ့နိုင်ပါသည်။ ကြိုးစားပေမယ့် ရလဒ်မတိုးတက်သည် — ဒါသည် ပုံမှန် စုဆောင်းခြင်းအဆင့်ဖြစ်ပြီး ဆက်လက်ကြိုးစားပါက ပေါက်ကွဲမှုရှိပါလိမ့်မည်။ သင်ယူနည်းပြောင်းလဲကြည့်ပါ — တက်ကြွစွာ မှတ်စုတင်ခြင်း၊ စိတ်ပုံဆွဲခြင်း စသည်တို့ဖြင့်။"
        f"\n• စီးပွားရေးလုပ်ငန်းရှင်များ: လက်ရှိတိုးတက်မှုသည် မျှော်လင့်ထားသည်ထက် နည်းနိုင်ပါသည်၊ သို့သော် ဦးတည်ချက်မှာ မှန်ပါသည်။ ရုတ်တရက်ပြောင်းလဲမှုများကြောင့် ဗျူဟာများကို မကြာခဏ မပြောင်းလဲပါနှင့်။"
        f"\n• အလုပ်ရှာနေသူများ: ဖောင်တင်ပြီးနောက် အကြောင်းကြားချက်နည်းခြင်းသည် ပုံမှန်ဖြစ်ပါသည်၊ သင်မကောင်းဟု မဆိုလိုပါ။ ပြိုင်ဆိုင်မှုပြင်းထန်ခြင်း သို့မဟုတ် ဖောင်တွင် ထင်ရှားသည့်အချက်မရှိခြင်း ဖြစ်နိုင်ပါသည်။ မိတ်ဆွေများထံ ဖောင်ကို ကြည့်ခိုင်းပါ သို့မဟုတ် လုပ်ငန်းတွင်း အကြံပေးရှာပါ။",
    )

    career_future_extra = L(
        f"\n\n事业方面的未来走向："
        f"\n\n• 短期（1-3个月）：可能会有一次重要的机会或挑战出现，比如新项目、晋升面试、考试等。卦象暗示这个机会需要你「主动争取」而不是等待。"
        f"\n• 中期（3-6个月）：如果前期打好了基础，这段时间会有明显的进展回报。可能是升职加薪、项目成功、学业突破等。"
        f"\n• 长期趋势：你的职业道路整体向好，但中间会有波动。关键是保持耐心，不要因为一时的得失而改变大方向。"
        f"\n• 贵人运：近期可能会遇到一位对你事业有帮助的前辈或导师，要珍惜这段关系。同时，你也可以成为别人的贵人——帮助他人也是在为自己积累福报。",
        f"\n\n事業の将来の流れ："
        f"\n\n• 短期（1-3ヶ月）：新しいプロジェクト、昇進面接、試験など、重要なチャンスやチャレンジが来るかもしれません。このチャンスは「待つ」のではなく「取りに行く」必要があります。"
        f"\n• 中期（3-6ヶ月）：前期の基礎がしっかりしていれば、この時期に明確な進展が見られるでしょう。昇進、プロジェクト成功、学業のブレイクスルーなど。"
        f"\n\n• 長期の傾向：全体的に良い方向に向いていますが、途中で揺れがあります。大切なのは忍耐——一時の損得で大方向を変えないこと。"
        f"\n• お貴人運：近いうちにキャリアに助けとなる先輩やメンターに出会うかもしれません。この縁を大切に。あなたも誰かのお貴人になれます——人を助けることは自分の福を積むことでもあります。",
        f"\n\nCareer future outlook:"
        f"\n\n• Short-term (1-3 months): An important opportunity or challenge may arise — a new project, promotion interview, exam. The hexagram suggests you need to actively pursue this opportunity rather than wait."
        f"\n• Medium-term (3-6 months): If you've built solid foundations, this period brings clear rewards — promotion, project success, academic breakthrough."
        f"\n• Long-term trend: Your career path is generally positive, but expect fluctuations. The key is patience — don't change your direction over temporary gains or losses."
        f"\n\n• Mentor luck: You may encounter a senior or mentor who helps your career. Cherish this connection. You can also be someone else's mentor — helping others accumulates your own good fortune.",
        f"\n\nTương lai sự nghiệp:"
        f"\n\n• Ngắn hạn (1-3 tháng): Có thể có cơ hội hoặc thử thách quan trọng — dự án mới, phỏng vấn thăng chức, kỳ thi. Quẻ hint bạn cần「chủ động tranh thủ」không phải chờ đợi."
        f"\n\n• Trung hạn (3-6 tháng): Nếu nền tảng tốt, giai đoạn này sẽ có tiến triển rõ rệt — thăng chức, dự án thành công, đột phá học tập."
        f"\n• Xu hướng dài hạn: Con đường sự nghiệp tổng thể tích cực, nhưng có dao động. Chìa khóa là kiên trì, đừng thay đổi hướng lớn vì được mất nhất thời."
        f"\n• Quý nhân: Có thể gặp tiền bối hoặc người cố vấn giúp sự nghiệp. Hãy trân trọng mối quan hệ này. Bạn cũng có thể trở thành quý nhân của người khác — giúp người cũng là tích phúc cho mình.",
        f"\n\n직업의 미래 흐름:"
        f"\n\n• 단기(1-3개월): 새로운 프로젝트, 승진 면접, 시험 등 중요한 기회나 도전이 올 수 있습니다. 이 기회는「기다리는」것이 아니라「적극적으로 취하는」것이 필요합니다."
        f"\n• 중기(3-6개월): 초기 기반이 단단하다면 이 시기에 명확한 진전이 보일 것입니다. 승진, 프로젝트 성공, 학업 돌파구 등."
        f"\n• 장기적 경향: 전반적으로 좋지만 중간에 변동이 있습니다. 중요한 것은 인내 — 일시적인 득실로 큰 방향을 바꾸지 마세요."
        f"\n• 귀인운: 가까운 시일에 경력에 도움이 되는 선배나 멘토를 만날 수 있습니다. 이 인연을 소중히 하세요. 당신도 누군가의 귀인이 될 수 있습니다.",
        f"\n\nအလုပ်/ပညာရေး အနာဂတ်လမ်းကြောင်း —"
        f"\n\n• ရုတ်တရက် (၁-၃ လ) — အရေးကြီးသည့် အခွင့်အရေး သို့မဟုတ် စိန်ခေါ်မှု ပေါ်လာနိုင်ပါသည် — စီမံကိန်းအသစ်၊ ရာထူးတိုးတင်ခြင်း၊ စာမေးပွဲ စသည်တို့ဖြစ်သည်။ ဤအခွင့်အရေးသည် 'စောင့်ဆိုင်း'ရန်မဟုတ်ဘဲ 'တက်ကြွစွာ ရယူ'ရန် လိုအပ်ပါသည်။"
        f"\n• အလယ်အလတ် (၃-၆ လ) — အစပိုင်း အခြေခံကောင်းစွာ တည်ဆောက်ထားပါက ဤကာလတွင် ထင်ရှားသည့် တိုးတက်မှုများ ရရှိနိုင်ပါသည် — ရာထူးတိုးခြင်း၊ စီမံကိန်းအောင်မြင်ခြင်း၊ ပညာရေးတွင် ပေါက်ကွဲမှု စသည်တို့ဖြစ်သည်။"
        f"\n• ရေရှည်လမ်းကြောင်း — သင့်အလုပ်လမ်းကြောင်းသည် အထွေထွေကောင်းမွန်သော်လည်း အလယ်တွင် တုန်ခါမှုများ ရှိနိုင်ပါသည်။ အရေးကြီးဆုံးမှာ စိတ်ရှည်ရှည်ထားခြင်းဖြစ်သည် — ခဏတာ ရရှိခြင်း/ဆုံးရှုံးခြင်းကြောင့် ကြီးမားသည့် ဦးတည်ချက်ကို မပြောင်းလဲပါနှင့်။"
        f"\n• ကောင်းချက် — မကြာမီကာလတွင် သင့်အလုပ်တွင် အကူအညီဖြစ်စေနိုင်သည့် အကြံပေး သို့မဟုတ် ဆရာတစ်ယောက်ကို တွေ့နိုင်ပါသည်။ ဤဆက်ဆံရေးကို တန်ဖိုးထားပါ။ သင်ကလည်း အခြားသူတစ်ယောက်၏ ကောင်းချက် ဖြစ်နိုင်ပါသည် — အခြားသူများကို ကူညီခြင်းသည် ကိုယ့်အတွက် ကောင်းချက်စုဆောင်းခြင်းဖြစ်သည်။"
    )

    career_adv_extra = L(
        f"\n\n【具体行动建议】"
        f"\n\n1. 主动汇报工作进度：不要等领导来问，定期主动汇报会让上级觉得你靠谱。"
        f"\n2. 拓展人脉：参加行业活动、加入专业社群，认识更多同行。人脉是事业的隐形资产。"
        f"\n3. 持续学习：无论多忙，每天抽出30分钟学习新知识或提升技能。复利效应会在半年后显现。"
        f"\n4. 管理时间：用四象限法则（重要紧急/重要不紧急/紧急不重要/不重要不紧急）来安排每天的任务。"
        f"\n5. 保持健康：身体是革命的本钱。如果经常加班，要注意补充营养和睡眠，不要透支健康换业绩。",
        f"\n\n【具体的アクションアドバイス】"
        f"\n\n1. 進捗を能動的に報告：上司から聞かれる前に定期的に報告すれば、頼りにされるようになります。"
        f"\n2. 人脈を広げ：業界イベントや専門コミュニティに参加して、同業者と知り合いましょう。人脈はキャリアの隐形資産です。"
        f"\n3. 学び続ける：どんなに忙しくても毎日30分は新しい知識やスキルアップに。複利効果は半年後に現れます。"
        f"\n4. 時間管理：四象限法則（重要緊急/重要非緊急/緊急非重要/非重要非緊急）で毎日のタスクを整理。"
        f"\n5. 健康維持：体は革命の资本です。残業が多い場合は栄養補給と睡眠を意識し、健康を犠牲にしないでください。",
        f"\n\n【Specific Action Advice】"
        f"\n\n1. Report progress proactively: Don't wait for your boss to ask. Regular updates make you look reliable."
        f"\n2. Expand your network: Attend industry events, join professional communities. Your network is your career's hidden asset."
        f"\n3. Keep learning: Even when busy, spend 30 minutes daily on new knowledge or skills. Compound interest kicks in after six months."
        f"\n4. Manage time: Use the Eisenhower matrix (urgent-important/not-urgent-important/urgent-not-important/not-urgent-not-important) to organise daily tasks."
        f"\n5. Stay healthy: Health is your most valuable asset. If you work overtime often, prioritise nutrition and sleep — don't trade health for performance.",
        f"\n\n【Hành động cụ thể】"
        f"\n\n1. Chủ động báo cáo tiến độ: Đừng chờ cấp trên hỏi, báo cáo định kỳ khiến cấp trên thấy bạn đáng tin cậy."
        f"\n\n2. Mở rộng mạng lưới: Tham gia sự kiện ngành, cộng đồng chuyên môn, quen biết nhiều đồng nghiệp hơn. Mạng lưới là tài sản ẩn của sự nghiệp."
        f"\n\n3. Học hỏi liên tục: Bận đến đâu cũng dành 30 phút mỗi ngày học kiến thức mới hoặc nâng cao kỹ năng. Hiệu ứng kép sẽ phát huy sau 6 tháng."
        f"\n\n4. Quản lý thời gian: Dùng quy tắc 4 ô (quan trọng khẩn cấp/quan trọng không khẩn cấp/khẩn cấp không quan trọng/không quan trọng không khẩn cấp) để sắp xếp công việc hàng ngày."
        f"\n\n5. Giữ sức khỏe: Sức khỏe là nền tảng. Nếu thường xuyên làm thêm giờ, chú ý bổ sung dinh dưỡng và giấc ngủ, đừng đánh đổi sức khỏe lấy thành tích.",
        f"\n\n【구체적인 행동 조언】"
        f"\n\n1. 진행 상황을 능동적으로 보고하세요: 상사가 물어보기 전에 정기적으로 보고하면 신뢰감을 줍니다."
        f"\n\n2. 인맥을 넓히세요: 업계 행사, 전문 커뮤니티에 참가해서 동료들을 많이 만나세요. 인맥은 경력의 보이지 않는 자산입니다."
        f"\n\n3. 배움을 계속하세요: 아무리 바빠도 매일 30분은 새로운 지식이나 기술 향상에 투자하세요. 복리 효과는 6개월 후 나타납니다."
        f"\n\n4. 시간 관리: 4분면 법칙(중요 긴급/중요 비긴급/긴급 비중요/비중요 비긴급)으로 매일 할 일을 정리하세요."
        f"\n\n5. 건강 유지: 건강이 가장 큰 자산입니다. 야근이 많다면 영양 보충과 수면을 신경 쓰세요. 건강을 희생하여 성과를换取하지 마세요.",
        f"\n\n【လက်တွေ့လုပ်ဆောင်ရန် အကြံပြုချက်များ】"
        f"\n\n၁။ တက်ကြွစွာ အစီရင်ခံပါ — အထက်အရာရှိက မေးမြန်းခင် ပုံမှန်အစီရင်ခံခြင်းဖြင့် သင့်ကို ယုံကြည်စိတ်ချစရာကောင်းသည့်လူအဖြစ် မြင်ပါမည်။"
        f"\n၂။ ဆက်သွယ်ရေးကွန်ယက် ချဲ့ပါ — လုပ်ငန်းနယ်ပယ် လုပ်ဆောင်ပွဲများတက်ခြင်း၊ ကျွမ်းကျင်သူများ အုပ်စုများထဲ ဝင်ခြင်းဖြင့် ပိုမိုများပြားသည့် လုပ်ဖော်ဆွေများကို တွေ့နိုင်ပါသည်။ ဆက်သွယ်ရေးကွန်ယက်သည် အလုပ်၏ မမြင်နိုင်သည့် ပိုင်ဆိုင်မှုဖြစ်သည်။"
        f"\n၃။ ဆက်လက်သင်ယူပါ — ဘယ်လောက်ပဲ အလုပ်များပါစေ၊ တစ်နေ့လျှင် မိနစ် ၃၀ ခန့် အသစ်သော ဗဟုသုတ သို့မဟုတ် ကျွမ်းကျင်မှု တိုးတက်အောင် ရင်းနှီးမြှပ်နှံပါ။ ဆပ်ကပ်အကျိုးသက်ရောက်မှုသည် လပေါင်း ၆ အကြာတွင် ပေါ်လာပါမည်။"
        f"\n၄။ အချိန်စီမံခန့်ခွဲပါ — ဘေးနှစ်ခြမ်းနည်းစနစ် (အရေးကြီး/အရေးကြီးမဟုတ် × အရေးပေါ်/အရေးပေါ်မဟုတ်) ဖြင့် နေ့စဉ်အလုပ်များကို စီစဉ်ပါ။"
        f"\n၅။ ကျန်းမာရေး ထိန်းသိမ်းပါ — ကျန်းမာရေးသည် အကြီးဆုံးပိုင်ဆိုင်မှုဖြစ်သည်။ ညဘက်အလုပ်လုပ်ခြင်းများပါက အာဟာရဖြည့်တင်ခြင်းနှင့် အိပ်စက်ခြင်းကို ဂရုစိုက်ပါ။ ကျန်းမာရေးကို စွန့်လွှတ်ပြီး ရလဒ်များ မလုပ်ပါနှင့်။"
    )

    analysis["career"] = block(
        L(career_title.get("zh", "工作 / 学业"), career_title.get("ja", "仕事・学業"),
          career_title.get("en", "Career / Study"), career_title.get("vi", "Công việc / Học tập"),
          career_title.get("ko", "직업 / 학업"), career_title.get("my", "အလုပ် / ပညာရေး")),
        L(career_desc.get("zh", "") + career_now_extra["zh"], career_desc.get("ja", "") + career_now_extra["ja"],
          career_desc.get("en", "") + career_now_extra["en"], career_desc.get("vi", "") + career_now_extra["vi"],
          career_desc.get("ko", "") + career_now_extra["ko"], career_desc.get("my", "") + career_now_extra["my"]),
        career_future_extra,
        career_adv_extra,
    )

    # ===== 金钱 / 财运 =====
    wealth_core = interp.get("wealth", {})
    wealth_desc = wealth_core.get("desc", {})
    wealth_title = wealth_core.get("title", {})

    wealth_now_extra = L(
        f"\n\n财运方面，「{focus_kin}」对你的财务状况有直接影响。"
        f"\n\n• 正财（工资/固定收入）：近期正财运势平稳，适合通过努力工作获得收入增长。如果有加薪或奖金的机会，建议主动争取。"
        f"\n• 偏财（投资/副业/意外收入）：偏财运势波动较大，不适合做高风险投资（如炒股、炒币、赌博）。如果有人推荐「稳赚不赔」的项目，务必保持警惕。"
        f"\n• 消费习惯：最近可能有冲动消费的倾向，尤其是网购和社交场合的面子消费。建议每次花钱前问自己三个问题：「这是必需品吗？」「能等一周再买吗？」「有没有更便宜的替代品？」"
        f"\n• 债务管理：如果有欠款或信用卡账单，优先处理高利息的债务。不要以贷养贷，这样只会让窟窿越来越大。",
        f"\n\n金運方面、「{focus_kin}」があなたの財務に直接影响しています。"
        f"\n\n• 正財（給料/固定収入）：近期の正財運は穏やかで、努力による収入増が見込みます。昇進やボーナスのチャンスがあれば、積極的に取りに行きましょう。"
        f"\n• 偏財（投資/副業/予期せぬ収入）：偏財運は変動が大きく、ハイリスク投資（株、暗号資産、ギャンブル）には向きません。「絶対儲かる」と勧められたプロジェクトには警戒を。"
        f"\n• 消費習慣：最近衝動買いの傾向があるかもしれません。特にネットショッピングや社交での面子消費。買い物前に「必需品か？」「一週間待てるか？」「もっと安い代替品はあるか？」の三問を。"
        f"\n• 借金管理：ローンやクレジットカードがある場合は、高金利の債務を優先的に返済。借金で借金を返すのは穴を広げるだけです。",
        f"\n\nWealth-wise, '{focus_kin}' directly affects your finances."
        f"\n\n• Earned income (salary/fixed): Recent earned income luck is stable — effort translates to income growth. If there's a raise or bonus opportunity, pursue it actively."
        f"\n\n• Windfall income (investments/side income): Windfall luck is volatile — avoid high-risk investments (stocks, crypto, gambling). Be wary of 'guaranteed returns' pitches."
        f"\n\n• Spending habits: You may feel impulsive spending urges, especially online shopping and social face-saving purchases. Before each purchase ask: 'Is this a necessity?', 'Can I wait a week?', 'Is there a cheaper alternative?'"
        f"\n\n• Debt management: If you have loans or credit card debt, prioritise paying off high-interest debt first. Don't borrow to repay — that only deepens the hole.",
        f"\n\nVề tài chính, '{focus_kin}' ảnh hưởng trực tiếp đến tình hình tài chính của bạn."
        f"\n\n• Thu nhập chính (lương/thu nhập cố định): Vận thu nhập chính gần đây ổn định, phù hợp nỗ lực làm việc để tăng thu nhập. Nếu có cơ hội tăng lương hoặc thưởng, hãy chủ động tranh thủ."
        f"\n\n• Thu nhập phụ (đầu tư/kiếm thêm/thu nhập bất ngờ): Vận thu nhập phụ dao động mạnh, không phù hợp đầu tư rủi ro cao (cổ phiếu, tiền mã hóa, cờ bạc). Cẩn thận với các dự án \"đảm bảo lời\"."
        f"\n\n• Thói quen tiêu dùng: Có thể có xu hướng tiêu xài bốc đồng, đặc biệt mua sắm online và chi tiêu vì mặt mũi. Trước mỗi khoản chi hãy hỏi: \"Đây có phải đồ cần thiết không?\", \"Có thể đợi 1 tuần không?\", \"Có thay thế rẻ hơn không?\""
        f"\n\n• Quản lý nợ: Nếu có khoản vay hoặc thẻ tín dụng, ưu tiên trả nợ lãi suất cao. Đừng lấy nợ trả nợ, chỉ khiến lỗ hổng ngày càng lớn.",
        f"\n\n재정 면에서 '{focus_kin}'이 재정 상태에 직접적인 영향을 줍니다."
        f"\n\n• 정기 소득(급여/고정 수입): 최근 정기 소득 운은 안정적이며, 노력에 의한 수입 증가가 기대됩니다. 승진이나 보너스 기회가 있다면 적극적으로 찾아가세요."
        f"\n\n• 간헐적 소득(투자/부업/예상치 못한 수입): 간헐적 소득 운은 변동이 크므로 고위험 투자(주식, 가상화폐, 도박)에 적합하지 않습니다. \"절대 벌 수 있다\"는 추천에는 경계하세요."
        f"\n\n• 소비 습관: 최근 충동 구매 성향이 있을 수 있습니다. 특히 온라인 쇼핑과 사회적 체면 소비. 구매 전에 \"필수품인가?\", \"일주일 기다릴 수 있는가?\", \"더 저렴한 대안이 있는가?\" 세 가지 질문을 하세요."
        f"\n\n• 부채 관리: 대출이나 신용카드 빚이 있다면 고이자 부채를 우선 상환하세요. 빚으로 빚을 갚는 것은 구멍을 더 키울 뿐입니다.",
        f"\n\nငွေကြေးနှင့်ပတ်သက်၍ '{focus_kin}'သည် သင့်ငွေကြေးအခြေအနေကို တိုက်ရိုက်သက်ရောက်ပါသည်။"
        f"\n\n• မူလဝင်ငွေ (လုပ်ခ/ပုံမှန်ဝင်ငွေ) — မကြာသေးခင်က မူလဝင်ငွေကံသည် တည်ငြိမ်ပြီး ကြိုးစားအားထုတ်မှုဖြင့် ဝင်ငွေတိုးတက်မှု ရရှိနိုင်ပါသည်။ လုပ်ခတိုးခြင်း သို့မဟုတ် ဘောနပ်စ်ရရှိခြင်း အခွင့်အရေးရှိပါက တက်ကြွစွာ ရယူပါ။"
        f"\n• ဘေးချိတ်ဝင်ငွေ (ရင်းနှီးမြှပ်နှံခြင်း/အပိုင်းချိတ်အလုပ်/မထင်မှတ်ဘဲရသည့်ဝင်ငွေ) — ဘေးချိတ်ဝင်ငွေကံသည် တုန်ခါမှုများပြားပြီး မြင့်မားသည့်အန္တရာယ်ရှိသည့် ရင်းနှီးမြှပ်နှံခြင်း (ရှယ်ယာ၊ ကရစ်ပိုက်၊ လောင်းကစား) အတွက် မသင့်တော်ပါ။ 'သေချာစွာအနိုင်ရမည်'ဟု အကြံပေးသူများကို သတိထားပါ။"
        f"\n• သုံးစွဲမှုပုံစံ — မကြာသေးခင်က ရုတ်တရက်သုံးစွဲလိုသည့် အလေ့အထရှိနိုင်ပါသည်။ အထူးသဖြင့် အွန်လိုင်းစျေးဝယ်ခြင်းနှင့် လူမှုရေးအရ မျက်နှာချင်းဆိုင် သုံးစွဲခြင်းများဖြစ်သည်။ ငွေသုံးမစတင်ခင် 'ဒါက လိုအပ်တဲ့အရာလား၊ ရက် ၇ ကြာအောင်စောင့်နိုင်လား၊ ပိုပြီးတန်ဖိုးနည်းတဲ့ အစားထိုးစရာရှိလား'ဟု ကိုယ့်ကိုယ်ကို မေးပါ။"
        f"\n• အကြွေးစီမံခန့်ခွဲပါ — အကြွေးရှိပါက မြင့်မားသည့်အတိုးနှုန်းရှိသည့် အကြွေးများကို ဦးစားပေးပေးဆပ်ပါ။ အကြွေးဖြင့် အကြွေးပေးဆပ်ခြင်းသည် အပေါက်ကို ပိုကြီးအောင်သာ လုပ်ပါသည်။"
    )

    wealth_future_extra = L(
        f"\n\n财运未来走势："
        f"\n\n• 短期：近期适合「守」而非「攻」。不要做大额投资或冲动消费，把钱存在安全的地方（如定期存款、货币基金）。"
        f"\n• 中期：如果能控制住消费欲望，3-6个月后会有明显的积蓄增长。这段时间适合制定年度财务计划。"
        f"\n• 转机信号：当你收到一笔意外的小收入（如红包、报销、小奖金）时，往往预示着更大的财运即将到来。"
        f"\n• 风险提示：避免给他人做担保、借大额资金给朋友、参与不熟悉的金融产品。这些都可能让你陷入财务困境。",
        f"\n\n金運の将来の流れ："
        f"\n\n• 短期：今は「守り」の時期。大きな投資や衝動買いは避け、安全な場所（定期預金・MMFなど）に資金を置いて。"
        f"\n\n• 中期：消費欲を抑えられれば、3-6ヶ月後に貯蓄が明確に増えるでしょう。年間の資金計画を立てるのに適した時期です。"
        f"\n\n• 転機のサイン：小さな予期せぬ収入（お年玉、経費精算、小さなボーナス）があった時、それは更大的な金運の前触れであることが多いです。"
        f"\n\n• リスク警告：他人の保証人になること、友人に大金を貸すこと、馴染みのない金融商品への参加は避けてください。いずれも財務的困境に陥る可能性があります。",
        f"\n\nWealth future trends:"
        f"\n\n• Short-term: This is a 'defend' period. Don't make large investments or impulse purchases. Keep money in safe places (fixed deposits, money market funds)."
        f"\n\n• Medium-term: If you control spending, savings will grow noticeably in 3-6 months. Good time to create an annual financial plan."
        f"\n\n• Turning point signal: When you receive a small unexpected income (red envelope, reimbursement, small bonus), it often signals bigger wealth luck coming."
        f"\n\n• Risk warning: Avoid being a guarantor for others, lending large sums to friends, or joining unfamiliar financial products. All can lead to financial trouble.",
        f"\n\nTương lai tài chính:"
        f"\n\n• Ngắn hạn: Giai đoạn「phòng thủ」. Đừng đầu tư lớn hoặc tiêu xài bốc đồng, cất tiền ở nơi an toàn (tiền gửi có kỳ hạn, quỹ tiền tệ)."
        f"\n\n• Trung hạn: Nếu kiểm soát được ham muốn tiêu dùng, 3-6 tháng nữa tiết kiệm sẽ tăng rõ rệt. Đây là lúc lập kế hoạch tài chính năm phù hợp."
        f"\n\n• Dấu hiệu chuyển biến: Khi nhận được thu nhập bất ngờ nhỏ (lì xì, hoàn tiền, thưởng nhỏ), thường báo hiệu tài chính lớn hơn đang đến."
        f"\n\n• Cảnh báo rủi ro: Tránh làm người bảo đảm cho người khác, cho bạn bè vay tiền lớn, tham gia sản phẩm tài chính không quen thuộc. Tất cả đều có thể dẫn đến khó khăn tài chính.",
        f"\n\n재정의 미래 흐름:"
        f"\n\n• 단기: 지금은「방어」의 시기입니다. 큰 투자나 충동 구매는 피하고 안전한 곳(정기예금, 머니마켓펀드)에 자금을 보관하세요."
        f"\n\n• 중기: 소비 욕구를 억제할 수 있다면 3-6개월 후 저축이 눈에 띄게 늘어날 것입니다. 연간 재정 계획을 세우기에 좋은 시기입니다."
        f"\n\n• 전환점 신호: 작은 예상치 못한 수입(세뱃돈, 비용 정산, 작은 보너스)을 받을 때, 그것은 더 큰 재운의 전조인 경우가 많습니다."
        f"\n\n• 리스크 경고: 타인의 보증인이 되거나, 친구에게 큰 돈을 빌려주거나, 익숙하지 않은 금융 상품에 참여하는 것은 피하세요. 모두 재정적 궁지에 빠질 수 있습니다.",
        f"\n\nငွေကြေးအနာဂတ်လမ်းကြောင်း —"
        f"\n\n• ရုတ်တရက် — ဤကာလသည် 'ကာကွယ်ရေး' ကာလဖြစ်ပါသည်။ ကြီးမားသည့် ရင်းနှီးမြှပ်နှံခြင်း သို့မဟုတ် ရုတ်တရက်သုံးစွဲခြင်းကို ရှောင်ပါ။ ငွေကို လုံခြုံသည့်နေရာတွင် ထားပါ (အပိုင်းအစအစုရှယ်ယာ၊ ငွေကြေးဖန်တီးမှုဖန်တီးမှုဖန်တီးမှုဖန်တီးမှု)။"
        f"\n• အလယ်အလတ် — သုံးစွဲလိုသည့်ဆန္ဒကို ထိန်းချုပ်နိုင်ပါက လပေါင်း ၃-၆ အကြာတွင် စုဆောင်းငွေ ထင်ရှားစွာ တိုးတက်လာပါမည်။ နှစ်စဉ်ငွေကြေးအစီအစဉ် ရေးဆွဲရန် သင့်တော်သည့်အချိန်ဖြစ်သည်။"
        f"\n• ပြောင်းလဲမှုလက္ခဏာ — မထင်မှတ်ဘဲ အသေးစားဝင်ငွေ (လက်ဆောင်ငွေ၊ ပြန်အမ်းငွေ၊ အသေးစားဘောနပ်စ်) ရရှိသည့်အခါ ပိုကြီးသည့်ငွေကံ လာတော့မည်ဖြစ်ကြောင်း ညွှန်ပြနေခြင်းဖြစ်တတ်ပါသည်။"
        f"\n• အန္တရာယ်သတိပေးချက် — အခြားသူတစ်ယောက်အတွက် အာမခံလုပ်ခြင်း၊ မိတ်ဆွေကြီးကြီးတစ်ယောက်ထံ ငွေကြီးကြီး ချေးငှားခြင်း၊ မရင်းနှီးသည့် ငွေကြေးထုတ်ကုန်များတွင် ပါဝင်ခြင်းတို့ကို ရှောင်ပါ။ ဤအရာအားလုံးသည် ငွေကြေးအခက်အခဲသို့ ဦးတည်စေနိုင်ပါသည်။"
    )

    wealth_adv_extra = L(
        f"\n\n【具体行动建议】"
        f"\n\n1. 记账习惯：用手机记账APP记录每笔开支，月底复盘。你会发现很多「不必要的开支」。"
        f"\n2. 自动储蓄：每月工资到账后，自动转一笔固定金额到储蓄账户。「先存后花」比「花剩再存」有效10倍。"
        f"\n3. 理财学习：花时间了解基本的理财知识（如基金定投、保险配置、税务规划），这些知识会帮你省下或赚到更多钱。"
        f"\n4. 副业探索：如果主业收入稳定，可以考虑发展一个副业。但要选择与自己技能匹配的方向，不要盲目跟风。"
        f"\n5. 紧急备用金：确保至少有3-6个月生活费的紧急备用金。这是你的财务安全网。",
        f"\n\n【具体的アクションアドバイス】"
        f"\n\n1. 家計簿習慣：スマホの家計簿アプリで毎日の出費を記録し、月末に振り返りましょう。「不要な出費」がたくさん見つかるはずです。"
        f"\n\n2. 自動貯蓄：給料が入ったら自動で一定額を貯蓄口座に移す。「先に貯めてから使う」は「使って残りを貯める」の10倍効果的です。"
        f"\n\n3. 金融リテラシー：基本的な金融知識（投資信託、保険、税金）を学びましょう。これら的知识がお金を節約したり増やしたりします。"
        f"\n\n4. 副業探求：本業の収入が安定していれば、副業も考えてみましょう。自分のスキルと合った方向を選び、流行りに乗るのは避けて。"
        f"\n\n5. 緊急預金：最低でも3-6ヶ月分の生活費を緊急預金として確保。これはあなたの財務の安全ネットです。",
        f"\n\n【Specific Action Advice】"
        f"\n\n1. Track expenses: Use a budgeting app to record every expense and review monthly. You'll discover many 'unnecessary expenditures'."
        f"\n\n2. Auto-save: When salary arrives, automatically transfer a fixed amount to savings. 'Save first, spend later' is 10x more effective than 'spend first, save what's left'."
        f"\n\n3. Financial literacy: Spend time learning basic financial knowledge (fund investing, insurance, tax planning). This knowledge saves and earns you more money."
        f"\n\n4. Side income: If your main income is stable, consider developing a side hustle. Choose something matching your skills — don't blindly follow trends."
        f"\n\n5. Emergency fund: Ensure you have at least 3-6 months of living expenses as an emergency fund. This is your financial safety net.",
        f"\n\n【Hành động cụ thể】"
        f"\n\n1. Thói quen ghi chép: Dùng app ghi chép chi tiêu trên điện thoại, cuối tháng tổng kết. Bạn sẽ phát hiện nhiều「khoản chi không cần thiết」."
        f"\n\n2. Tự động tiết kiệm: Khi lương về, tự động chuyển một khoản cố định vào tài khoản tiết kiệm.「Tiết kiệm trước chi tiêu sau」hiệu quả gấp 10 lần「tiêu xong còn lại mới tiết kiệm」."
        f"\n\n3. Học tài chính: Dành thời gian tìm hiểu kiến thức tài chính cơ bản (đầu tư quỹ, bảo hiểm, thuế). Kiến thức này sẽ giúp bạn tiết kiệm hoặc kiếm được nhiều hơn."
        f"\n\n4. Khám phá thu nhập phụ: Nếu thu nhập chính ổn định, có thể phát triển nghề phụ. Nhưng chọn hướng phù hợp với kỹ năng, đừng chạy theo xu hướng."
        f"\n\n5. Quỹ khẩn cấp: Đảm bảo có ít nhất 3-6 tháng chi phí sinh hoạt làm quỹ khẩn cấp. Đây là mạng lưới an toàn tài chính của bạn.",
        f"\n\n【구체적인 행동 조언】"
        f"\n\n1. 가계부 습관: 스마트폰 가계부 앱으로 매일 지출을 기록하고 월말에 리뷰하세요. \"불필요한 지출\"이 많이 발견될 것입니다."
        f"\n\n2. 자동 저축: 급여가 들어오면 자동으로 일정액을 저축 계좌로 이체하세요. \"먼저 저축하고 나서 쓰기\"는 \"쓰고 남은 것 저축하기\"보다 10배 효과적입니다."
        f"\n\n3. 금융 리터러시: 기본적인 금융 지식(펀드투자, 보험, 세금)을 배우세요. 이 지식이 돈을 절약하거나 더 많이 벌게 해줍니다."
        f"\n\n4. 부업 탐색: 본업 소득이 안정적이라면 부업도 고려해보세요. 자신의 기술과 맞는 방향을 선택하고 유행에 무작정 따르지는 마세요."
        f"\n\n5. 비상금: 최소 3-6개월 생활비를 비상금으로 확보하세요. 이것이 당신의 재정 안전망입니다.",
        f"\n\n【လက်တွေ့လုပ်ဆောင်ရန် အကြံပြုချက်များ】"
        f"\n\n၁။ ငွေစာရင်းမှတ်တမ်း ထားပါ — ဖုန်းငွေစာရင်း app ဖြင့် သုံးစွဲငွေတိုင်းကို မှတ်ပြီး လပြတ်ပြန်လည်သုံးသပ်ပါ။ 'မလိုအပ်သည့် သုံးစွဲမှု' များစွာ တွေ့ရပါမည်။"
        f"\n၂။ အလိုအလျောက် စုဆောင်းပါ — လုပ်ခထွက်သည်နှင့်အမျှ ငွေပမာဏတစ်ခုကို အလိုအလျောက် စုဆောင်းငွေအကောင့်သို့ ပြောင်းပါ။ 'ပထမစုပြီးမှသုံး' သည် 'သုံးပြီးမှကျန်တာစု' ထက် ဆယ်ဆပိုထိရောက်ပါသည်။"
        f"\n၃။ ငွေကြေးပညာ သင်ယူပါ — အခြေခံငွေကြေးဗဟုသုတ (ဖန်တီးမှုဖန်တီးမှု၊ အာမခံ၊ အခွန်) ကို အချိန်ပေး၍ လေ့လာပါ။ ဤဗဟုသုတသည် ငွေကို ချွေတာခြင်း သို့မဟုတ် ပိုမိုရရှိခြင်းတို့ကို ကူညီပါမည်။"
        f"\n၄။ အပိုင်းချိတ်အလုပ် ရှာဖွေပါ — အဓိကအလုပ်မှ ဝင်ငွေတည်ငြိမ်ပါက အပိုင်းချိတ်အလုပ်ကို တိုးချဲ့နိုင်ပါသည်။ သို့သော် ကိုယ့်ကျွမ်းကျင်မှုနှင့် ကိုက်ညီသည့် ဦးတည်ချက်ကိုသာ ရွေးပါ၊ ခေတ်စီးကို မျက်စိမှိတ်၍ မလိုက်ပါနှင့်။"
        f"\n၅။ အရေးပေါ်ငွေ — အနည်းဆုံး လပေါင်း ၃-၆ ခု နေထိုင်စရိတ်ကို အရေးပေါ်ငွေအဖြစ် သိမ်းဆည်းထားပါ။ ဒါက သင့်ငွေကြေးလုံခြုံရေး ကွန်ယက်ဖြစ်ပါသည်။"
    )

    analysis["wealth"] = block(
        L(wealth_title.get("zh", "金钱 / 财运"), wealth_title.get("ja", "金運・お金"),
          wealth_title.get("en", "Wealth / Money"), wealth_title.get("vi", "Tiền bạc / Tài vận"),
          wealth_title.get("ko", "금전 / 재운"), wealth_title.get("my", "ငွေကြေး")),
        L(wealth_desc.get("zh", "") + wealth_now_extra["zh"], wealth_desc.get("ja", "") + wealth_now_extra["ja"],
          wealth_desc.get("en", "") + wealth_now_extra["en"], wealth_desc.get("vi", "") + wealth_now_extra["vi"],
          wealth_desc.get("ko", "") + wealth_now_extra["ko"], wealth_desc.get("my", "") + wealth_now_extra["my"]),
        wealth_future_extra,
        wealth_adv_extra,
    )

    # ===== 健康 =====
    health_core = interp.get("health", {})
    health_desc = health_core.get("desc", {})
    health_title = health_core.get("title", {})

    health_now_extra = L(
        f"\n\n健康方面，「{focus_kin}」提示你需要特别关注以下领域："
        f"\n\n• 身体信号：近期如果出现头痛、失眠、肠胃不适、肩颈酸痛等症状，不要忽视。这些是身体在提醒你需要调整生活方式。"
        f"\n• 心理健康：压力大的时候容易焦虑或情绪低落。建议每天给自己15分钟「放空时间」——散步、听音乐、冥想都可以。"
        f"\n• 饮食建议：近期适合清淡饮食，少吃油腻、辛辣和生冷食物。多吃蔬菜水果，保持规律的三餐时间。"
        f"\n• 运动建议：不需要剧烈运动，每天30分钟的中等强度运动（快走、游泳、骑车）就足够了。关键是坚持，而不是强度。"
        f"\n• 作息调整：尽量在晚上11点前入睡。睡眠不足会影响免疫力和判断力。如果经常熬夜，试着把手机放在够不到的地方。",
        f"\n\n健康方面、「{focus_kin}」は以下の領域への特別な注意を示しています。"
        f"\n\n• 身体のサイン：最近頭痛、不眠、胃腸の不調、肩こりなどの症状が出たら見逃さないでください。体が生活習慣の改善を伝えています。"
        f"\n\n• 心の健康：ストレスが多いと不安や落ち込みが出やすいです。毎日15分の「リラックスタイム」を——散歩、音楽、瞑想など。"
        f"\n\n• 食事のアドバイス：最近は清淡な食事が向いています。脂っこいもの、辛いもの、冷たいものを控えめに。野菜と果物を多めに、三食を規則正しく。"
        f"\n\n• 運動のアドバイス：激しい運動は不要です。毎日30分の中程度の運動（早歩き、水泳、サイクリング）で十分。大切なのは継続、強度ではありません。"
        f"\n\n• 生活リズム：なるべく夜11時までに寝るように。睡眠不足は免疫力と判断力に影響します。夜更かしが多い場合は、スマホを手の届かない場所に置くのが効果的です。",
        f"\n\nHealth-wise, '{focus_kin}' signals you should pay special attention to:"
        f"\n\n• Body signals: If you experience headaches, insomnia, digestive issues, or neck/shoulder pain recently, don't ignore them. Your body is telling you to adjust your lifestyle."
        f"\n\n• Mental health: High stress can lead to anxiety or low mood. Give yourself 15 minutes of 'empty time' daily — walking, music, or meditation."
        f"\n\n• Diet advice: Eat lightly recently. Reduce greasy, spicy, and cold foods. Eat more vegetables and fruits, keep regular meal times."
        f"\n\n• Exercise advice: No need for intense workouts. 30 minutes of moderate exercise daily (brisk walking, swimming, cycling) is enough. Consistency matters more than intensity."
        f"\n\n• Sleep adjustment: Try to sleep before 11 PM. Sleep deprivation affects immunity and judgement. If you often stay up late, put your phone out of reach.",
        f"\n\nVề sức khỏe, '{focus_kin}' nhắc bạn cần đặc biệt lưu ý các lĩnh vực sau:"
        f"\n\n• Tín hiệu cơ thể: Nếu gần đây có triệu chứng đau đầu, mất ngủ, rối loạn tiêu hóa, đau vai gáy, đừng bỏ qua. Cơ thể đang nhắc bạn điều chỉnh lối sống."
        f"\n\n• Sức khỏe tinh thần: Áp lực lớn dễ gây lo lắng hoặc chán nản. Dành 15 phút mỗi ngày cho「thời gian thả trống」— đi bộ, nghe nhạc, thiền đều được."
        f"\n\n• Lời khuyên ăn uống: Giai đoạn này phù hợp ăn nhạt, ít dầu mỡ, cay, lạnh. Nhiều rau củ quả hơn, giữ bữa ăn đúng giờ."
        f"\n\n• Lời khuyên vận động: Không cần vận động mạnh. 30 phút vận động cường độ trung bình mỗi ngày (đi bộ nhanh, bơi, đạp xe) là đủ. Quan trọng là sự kiên trì, không phải cường độ."
        f"\n\n• Điều chỉnh giấc ngủ: Cố gắng ngủ trước 23 giờ. Thiếu ngủ ảnh hưởng đến miễn dịch và phán đoán. Nếu thường xuyên thức khuya, thử để điện thoại ở nơi không với tới.",
        f"\n\n건강 면에서 '{focus_kin}'은 다음 영역에 특별한 주의를 기울여야 함을 나타냅니다:"
        f"\n\n• 신체 신호: 최근 두통, 불면, 소화 장애, 어깨 결림 등의 증상이 있다면 무시하지 마세요. 몸이 생활 습관 조정을 알리고 있습니다."
        f"\n\n• 정신 건강: 스트레스가 많으면 불안이나 우울감이 쉽게 생깁니다. 매일 15분의 \"이완 시간\"을 가지세요 — 산책, 음악, 명상 등."
        f"\n\n• 식단 조언: 최근에는 담백한 음식이 적합합니다. 기름진 것, 매운 것, 차가운 것을 줄이세요. 채소와 과일을 많이, 식사를 규칙적으로."
        f"\n\n• 운동 조언: 격렬한 운동은 필요 없습니다. 매일 30분의 중간 강도 운동(빠른 걷기, 수영, 자전거 타기)이면 충분합니다. 중요한 것은 지속성, 강도가 아닙니다."
        f"\n\n• 수면 조정: 가능하면 밤 11시 이전에 주무세요. 수면 부족은 면역력과 판단력에 영향을 줍니다. 야근이 잦다면 스마트폰을 손이 닿지 않는 곳에 두는 것이 효과적입니다.",
        f"\n\nကျန်းမာရေးနှင့်ပတ်သက်၍ '{focus_kin}'သည် အောက်ပါနယ်ပယ်များတွင် အထူးအာရုံစိုက်ရန် လိုအပ်ကြောင်း ညွှန်ပြနေပါသည် —"
        f"\n\n• ခန္ဓာကိုယ်လက္ခဏာ — မကြာသေးခင်က ခေါင်းကိုက်ခြင်း၊ အိပ်မပျောခြင်း၊ အစာခြေစနစ်မကောင်းခြင်း၊ ပခုံး/လည်ပင်နာခြင်း စသည့် လက္ခဏာများ ရှိပါက မလျှော့ပါနှင့်။ ခန္ဓာကိုယ်က နေထိုင်မှုပုံစံပြောင်းလဲရန် သတိပေးနေခြင်းဖြစ်သည်။"
        f"\n• စိတ်ပိုင်းဆိုင်ရာကျန်းမာရေး — ဖိအားများသည့်အခါ စိတ်ပူပူထောင့်ကျခြင်း သို့မဟုတ် စိတ်ကျခြင်း ဖြစ်လွယ်ပါသည်။ တစ်နေ့လျှင် မိနစ် ၁၅ ခန့် 'အာရုံလွှတ်ချိန်' ထားပါ — လမ်းလျှောက်ခြင်း၊ ဂီတနားထောင်ခြင်း၊ တရားထိုင်ခြင်း စသည်တို့ဖြစ်သည်။"
        f"\n• အစားအစာအကြံ — မကြာသေးခင်က အညံ့စားအစားအစာ သင့်တော်ပါသည်။ ဆီများ၊ ငရုတ်ကောင်း၊ အေးသည့်အစားအစာများကို လျှော့စားပါ။ ဟင်းသီးဟင်းရွက်နှင့် အသီးအနှံများ ပိုစားပါ။ အစားအစာချိန်ကို ပုံမှန်ထားပါ။"
        f"\n• ကိုယ်လက်လှုပ်ရှား — ပြင်းထန်သည့် ကိုယ်လက်လှုပ်ရှားခြင်း မလိုပါ။ တစ်နေ့လျှင် မိနစ် ၃၀ ခန့် အလယ်အလတ်အားထုတ်မှုဖြင့် ကိုယ်လက်လှုပ်ရှားခြင်း (မြန်မြန်လျှောက်ခြင်း၊ ရေကူးခြင်း၊ စက်ဘီးစီးခြင်း) ဖြင့် လုံလောက်ပါသည်။ ဆက်လက်လုပ်ဆောင်ခြင်းသည် အရေးကြီးပါသည်။"
        f"\n• အိပ်စက်ခြင်းညှဉ်းပြင် — ည ၁၁ နာရီမတိုင်ခင် အိပ်ရောက်အောင် ကြိုးစားပါ။ အိပ်စက်ခြင်းမလုံလောက်ခြင်းသည် ခုခံအားနှင့် ဆုံးဖြတ်ချက်ချမှတ်ခြင်းကို ထိခိုက်စေပါသည်။ မကြာခဏ ညဘက်နေပါက ဖုန်းကို မရောက်နိုင်သည့်နေရာတွင် ထားကြည့်ပါ။"
    )

    health_future_extra = L(
        f"\n\n健康未来趋势："
        f"\n\n• 如果你现在开始调整生活习惯，1-2个月内会明显感觉到精力提升、睡眠改善。"
        f"\n• 如果继续保持不良习惯（熬夜、久坐、饮食不规律），3个月后可能会出现更明显的健康问题。"
        f"\n• 季节性提醒：换季时节容易感冒或过敏，注意增减衣物。"
        f"\n• 定期体检：如果有条件，建议做一次全面体检。早发现早治疗，远比生病后才重视要好。",
        f"\n\n健康の将来の流れ："
        f"\n\n• 生活習慣を今から整え始めれば、1-2ヶ月で精力の向上と睡眠の改善が実感できるでしょう。"
        f"\n\n• 悪い習慣（夜更かし、長時間座りっぱなし、不規則な食事）を続けると、3ヶ月後により顕著な健康問題が出る可能性があります。"
        f"\n\n• 季節の注意：季節の変わり目は風邪やアレルgiーにかかりやすいです。衣服の加減に気をつけて。"
        f"\n\n• 定期健診：可能であれば全面的な健診を。早期発見・早期治療が、病気になってから大切にするよりはるかに良いです。",
        f"\n\nHealth future trends:"
        f"\n\n• If you start adjusting habits now, you'll notice increased energy and better sleep within 1-2 months."
        f"\n• If you keep不良 habits (late nights, prolonged sitting, irregular meals), more noticeable health issues may emerge in 3 months."
        f"\n\n• Seasonal reminder: Changing seasons bring colds and allergies. Adjust your clothing accordingly."
        f"\n\n• Regular check-ups: If possible, get a comprehensive health check. Early detection and treatment is far better than caring only after getting sick.",
        f"\n\nTương lai sức khỏe:"
        f"\n\n• Nếu bạn bắt đầu điều chỉnh thói quen từ bây giờ, 1-2 tháng nữa sẽ cảm thấy rõ sự cải thiện năng lượng và giấc ngủ."
        f"\n\n• Nếu tiếp tục thói quen xấu (thức khuya, ngồi lâu, ăn uống không đều), 3 tháng nữa có thể xuất hiện vấn đề sức khỏe rõ ràng hơn."
        f"\n\n• Nhắc nhở theo mùa: Đổi mùa dễ bị cảm hoặc dị ứng, chú ý mặc thêm/bớt quần áo."
        f"\n\n• Khám sức khỏe định kỳ: Nếu có điều kiện, nên khám toàn diện. Phát hiện sớm điều trị sớm, tốt hơn nhiều so với khi bệnh mới lo.",
        f"\n\n건강의 미래 흐름:"
        f"\n\n• 지금부터 생활 습관을 조정하기 시작하면 1-2개월 내에 에너지 향상과 수면 개선이 뚜렷이 느껴질 것입니다."
        f"\n\n• 나쁜 습관(야근, 장시간 야식, 불규칙 식사)을 계속하면 3개월 후 더 뚜렷한 건강 문제가 나타날 수 있습니다."
        f"\n\n• 계절별 주의: 계절이 바뀔 때 감기나 알레르기에 걸리기 쉽습니다. 옷차림에 신경 쓰세요."
        f"\n\n• 정기 건강검진: 가능하다면 종합 건강검진을 받으세요. 조기 발견 조기 치료가, 아프고 나서 신경 쓰는 것보다 훨씬 좋습니다.",
        f"\n\nကျန်းမာရေး အနာဂတ်လမ်းကြောင်း —"
        f"\n\n• သင့်နေထိုင်မှုပုံစံကို ယခုမှ စတင်ညှဉ်းပြင်ပါက လပေါင်း ၁-၂ အကြာတွင် စွမ်းအင်တိုးတက်ခြင်းနှင့် အိပ်စက်ခြင်း ပိုကောင်းလာခြင်းကို ထင်ရှားစွာ ခံစားရပါမည်။"
        f"\n• မကောင်းသည့် အလေ့အထများ (ညဘက်နေခြင်း၊ ကြာကြာထိုင်ခြင်း၊ ပုံမှန်မစားခြင်း) ကို ဆက်လက်ထားပါက လပေါင်း ၃ အကြာတွင် ပို၍ထင်ရှားသည့် ကျန်းမာရေးပြဿနာများ ပေါ်လာနိုင်ပါသည်။"
        f"\n• ရာသီဥတုသတိပေးချက် — ရာသီပြောင်းချိန်တွင် အအေးမိခြင်း သို့မဟုတ် ဓာတ်မတည့်ခြင်း ဖြစ်လွယ်ပါသည်။ အဝတ်အစား ထည့်/ချွေတာရန် ဂရုစိုက်ပါ။"
        f"\n• ပုံမှန်ကျန်းမာရေးစစ်ဆေးခြင်း — အခွင့်အရေးရှိပါက အပြည့်အစုံကျန်းမာရေးစစ်ဆေးပါ။ စောစောတွေ့ခြင်းနှင့် စောစောကုခြင်းသည် ဖျားနာပြီးမှ ဂရုစိုက်ခြင်းထက် ပို၍ကောင်းပါသည်။"
    )

    health_adv_extra = L(
        f"\n\n【具体行动建议】"
        f"\n\n1. 建立作息规律：设定固定的起床和睡觉时间，即使是周末也尽量保持。"
        f"\n2. 工间休息：每工作1小时，站起来活动5分钟。做做伸展运动，看看远处。"
        f"\n3. 呼吸练习：感到压力大时，试试4-7-8呼吸法（吸气4秒、屏气7秒、呼气8秒），重复3-5次。"
        f"\n4. 社交与健康：和朋友一起运动比独自坚持更容易。找一个运动伙伴或加入运动群。"
        f"\n5. 中医养生：根据卦象，近期适合养「{focus_kin}」相关的脏腑。可以咨询中医师了解具体的调理方案。",
        f"\n\n【具体的アクションアドバイス】"
        f"\n\n1. 生活リズムの確立：決まった時間に起きる・寝る時間を設定し、週末でもなるべく維持。"
        f"\n\n2. 作業中の休憩：1時間ごとに立ち上がって5分動く。ストレッチをしたり、遠くを見たり。"
        f"\n\n3. 呼吸練習：ストレスを感じたら4-7-8呼吸法（4秒吸う・7秒止める・8秒吐く）を3-5回繰り返してみてください。"
        f"\n\n4. 社交と健康：友人と一緒に運動する方が一人で続けるより簡単です。運動パートナーやグループを見つけましょう。"
        f"\n\n5. 東洋医学養生：卦から見ると、「{focus_kin}」に関連する臓器を養う時期です。漢方の先生に具体的な養生法を聞いてみてください。",
        f"\n\n【Specific Action Advice】"
        f"\n\n1. Establish routines: Set fixed wake-up and bedtime, even on weekends."
        f"\n\n2. Work breaks: Every hour, stand up and move for 5 minutes. Stretch, look at something distant."
        f"\n\n3. Breathing exercises: When stressed, try 4-7-8 breathing (inhale 4 sec, hold 7 sec, exhale 8 sec), repeat 3-5 times."
        f"\n\n4. Social health: Exercising with friends is easier than alone. Find a workout buddy or join a fitness group."
        f"\n\n5. TCM wellness: According to the hexagram, this is a good time to nurture organs related to '{focus_kin}'. Consult a TCM practitioner for specific advice.",
        f"\n\n【Hành động cụ thể】"
        f"\n\n1. Thiết lập thói quen sinh hoạt: Đặt giờ ngủ và dậy cố định, dù cuối tuần cũng cố gắng giữ nguyên."
        f"\n\n2. Nghỉ giải lao khi làm việc: Mỗi tiếng đứng dậy hoạt động 5 phút. Tập kéo giãn, nhìn xa."
        f"\n\n3. Bài tập thở: Khi cảm thấy áp lực, thử bài thở 4-7-8 (hít vào 4 giây, giữ 7 giây, thở ra 8 giây), lặp lại 3-5 lần."
        f"\n\n4. Giao tiếp và sức khỏe: Tập thể thao cùng bạn bè dễ hơn tập một mình. Tìm bạn tập hoặc nhóm thể thao."
        f"\n\n5. Dưỡng sinh Đông y: Theo quẻ, giai đoạn này phù hợp dưỡng tạng phủ liên quan đến '{focus_kin}'. Có thể tham khảo bác sĩ Đông y để tìm hiểu phương pháp cụ thể.",
        f"\n\n【구체적인 행동 조언】"
        f"\n\n1. 생활 리듬 확립: 정해진 기상/취침 시간을 설정하고 주말에도 가능한 한 유지하세요."
        f"\n\n2. 작업 중 휴식: 1시간마다 일어나서 5분 움직이세요. 스트레칭을 하거나 먼 곳을 바라보세요."
        f"\n\n3. 호흡 연습: 스트레스를 느낄 때 4-7-8 호흡법(들이마시기 4초, 멈추기 7초, 내쉬기 8초)을 3-5번 반복해보세요."
        f"\n\n4. 사회적 건강: 친구와 함께 운동하는 것이 혼자 하는 것보다 쉽습니다. 운동 파트너나 그룹을 찾아보세요."
        f"\n\n5. 한의학 양생:괘에 따르면 '{focus_kin}'과 관련된 장기를 기르기에 좋은 시기입니다. 한의사에게 구체적인 조언을 구해보세요.",
        f"\n\n【လက်တွေ့လုပ်ဆောင်ရန် အကြံပြုချက်များ】"
        f"\n\n၁။ နေထိုင်မှုပုံစံ သတ်မှတ်ပါ — အိပ်ရောက်ချိန်နှင့် နိုးထချိန်ကို သတ်မှတ်ပြီး စနေ/တနင်္ဂနွေတွင်ပါ တတ်နိုင်သမျှ ထိန်းသိမ်းပါ။"
        f"\n၂။ အလုပ်ခွင်အနား — နာရီတိုင်း မတ်တပ်ရပ်ပြီး မိနစ် ၅ ခန့် လှုပ်ရှားပါ။ ကိုယ်လက်ဆန့်ကျင်လေ့ကျင့်ခြင်း၊ အဝေးကြည့်ခြင်း လုပ်ပါ။"
        f"\n၃။ အသက်ရှူလေ့ကျင့်ခန်း — ဖိအားများသည့်အခါ ၄-၇-၈ အသက်ရှူနည်း (မိနစ် ၄ ရှူ၊ မိနစ် ၇ ထိန်း၊ မိနစ် ၈ ထွက်) ကို ၃-၅ ကြိမ် ပြန်လုပ်ကြည့်ပါ။"
        f"\n၄။ လူမှုဆက်ဆံနှင့် ကျန်းမာရေး — မိတ်ဆွေများနှင့်အတူ ကိုယ်လက်လှုပ်ရှားခြင်းသည် တစ်ယောက်တည်း လုပ်ဆောင်ခြင်းထက် လွယ်ကူပါသည်။ အားကစားဖော် သို့မဟုတ် အုပ်စုတစ်ခုကို ရှာပါ။"
        f"\n၅။ တရုတ်ဆေးပညာ — ဗေဒအရ '{focus_kin}' နှင့်ဆက်စပ်သည့် အင်္ဂါများကို ထိန်းသိမ်းရန် သင့်တော်သည့်အချိန်ဖြစ်သည်။ တရုတ်ဆရာဝန်ထံ အသေးစိတ်အကြံဉာဏ် တောင်းခံကြည့်ပါ။"
    )

    analysis["health"] = block(
        L(health_title.get("zh", "健康"), health_title.get("ja", "健康"),
          health_title.get("en", "Health"), health_title.get("vi", "Sức khỏe"),
          health_title.get("ko", "건강"), health_title.get("my", "ကျန်းမာရေး")),
        L(health_desc.get("zh", "") + health_now_extra["zh"], health_desc.get("ja", "") + health_now_extra["ja"],
          health_desc.get("en", "") + health_now_extra["en"], health_desc.get("vi", "") + health_now_extra["vi"],
          health_desc.get("ko", "") + health_now_extra["ko"], health_desc.get("my", "") + health_now_extra["my"]),
        health_future_extra,
        health_adv_extra,
    )

    # ===== 人际 / 出行 =====
    travel_core = interp.get("travel", {})
    travel_desc = travel_core.get("desc", {})
    travel_title = travel_core.get("title", {})

    travel_now_extra = L(
        f"\n\n人际/出行方面，「{focus_kin}」对你的社交和出行有以下影响："
        f"\n\n• 人际关系：近期你的人际圈可能会有变化——可能结识新朋友，也可能与某些人渐行渐远。这是正常的社交更替，不必过于纠结。"
        f"\n• 职场关系：与同事、上级的关系需要用心维护。遇到意见不合时，先听对方说完再表达自己的看法。"
        f"\n• 家庭关系：如果最近和家人有矛盾，不妨主动打破僵局。一句「辛苦了」或一顿家常饭，比讲道理更有效。"
        f"\n• 出行安全：近期出行建议选择熟悉的路线和交通工具。如果要去陌生的地方，提前做好攻略。开车的朋友注意遵守交通规则，不要疲劳驾驶。"
        f"\n• 社交场合：参加聚会或社交活动时，多倾听少说话。观察谁是真诚的、谁是敷衍的。真正的朋友不需要你刻意讨好。",
        f"\n\n人际/出行方面、「{focus_kin}」はあなたの社交と出行に以下のような影響を与えています。"
        f"\n\n• 人間関係：最近の交友関係に変化が——新しい人に出会ったり、 certainな人とは疎遠になったり。これは正常的な社交の入れ替わりです。"
        f"\n\n• 職場の人間関係：同僚や上司との関係は意識的に維持しましょう。意見が異なる時は、まず相手を最後まで聞いてから自分の意見を。"
        f"\n\n• 家族関係：最近家族と問題があったなら、自分から僵局を破りましょう。「お疲れさま」や手作りの食事は、道理を説くより効果的です。"
        f"\n\n• 出行安全：最近の出行は馴染みのルートと交通手段がおすすめ。知らない場所に行く場合は事前にリサーチを。車を運転する方は交通ルールを守り、疲労運転を避けて。"
        f"\n\n• 社交の場：パーティーやイベントでは、多く聞き少なく語りましょう。誰が誠実で誰が表面的か観察してください。本当の友人は取り入る必要がありません。",
        f"\n\nPeople/travel-wise, '{focus_kin}' affects your social life and travel as follows:"
        f"\n\n• Social circles: Your network may change recently — meeting new people, drifting from others. This is normal social turnover."
        f"\n\n• Workplace relationships: Maintain connections with colleagues and supervisors. When opinions differ, listen fully before expressing yours."
        f"\n\n• Family: If there's been tension with family, break the ice first. A simple 'thanks for your hard work' or a home-cooked meal works better than reasoning."
        f"\n\n• Travel safety: Stick to familiar routes and transport recently. Research unfamiliar destinations in advance. If driving, follow traffic rules and avoid fatigue driving."
        f"\n\n• Social events: At gatherings, listen more than you speak. Observe who's sincere and who's superficial. True friends don't require you to go out of your way to please them.",
        f"\n\nVề quan hệ/đi lại, '{focus_kin}' ảnh hưởng đến giao tiếp và đi lại của bạn như sau:"
        f"\n\n• Mạng lưới xã hội: Vòng tròn quan hệ có thể thay đổi — quen người mới, xa dần người khác. Đây là sự thay thế xã hội bình thường."
        f"\n\n• Quan hệ công sở: Duy trì mối quan hệ với đồng nghiệp, cấp trên. Khi bất đồng, nghe hết rồi mới diễn đạt quan điểm."
        f"\n\n• Quan hệ gia đình: Nếu gần đây có mâu thuẫn với gia đình, hãy chủ động phá vỡ bế tắc. Một câu「vất vả rồi」hoặc một bữa cơm nhà hiệu quả hơn nhiều so với nói lý."
        f"\n\n• An toàn đi lại: Giai đoạn này nên chọn tuyến đường và phương tiện quen thuộc. Đi nơi lạ thì tìm hiểu trước. Lái xe tuân thủ luật giao thông, tránh lái xe mệt mỏi."
        f"\n\n• Giao lưu xã hội: Khi tham dự tiệc hoặc sự kiện, nghe nhiều nói ít. Quan sát ai chân thành, ai hời hợt. Bạn bè thật sự không cần bạn cố gắng lấy lòng.",
        f"\n\n인간관계/여행 면에서 '{focus_kin}'이 당신의 사교와여행에 다음과 같은 영향을 줍니다:"
        f"\n\n• 사교 관계: 최근 교제 범위에 변화가 있을 수 있습니다 — 새로운 사람을 만나거나, 특정 사람과 멀어지는 것. 이는 정상적인 사교 교체입니다."
        f"\n\n• 직장 관계: 동료, 상사와의 관계를 의식적으로 유지하세요. 의견이 다를 때는 먼저 상대의 말을 끝까지 듣고 자신의 의견을 표현하세요."
        f"\n\n• 가족 관계: 최근 가족과 갈등이 있었다면 먼저 얼어붙은 관계를 깨세요. \"수고했어\"라는 말이나 집밥 한 끼가이치를 설명하는 것보다 효과적입니다."
        f"\n\n• 여행 안전: 최근에는 익숙한 경로와 교통수단이 좋습니다. 낯선 곳에 갈 때는 미리 조사하세요. 운전자는 교통 규칙을 준수하고 피곤한 상태로 운전하지 마세요."
        f"\n\n• 사교 행사: 모임이나 행사에서는 많이 듣고 적게 말하세요. 누가 진실되고 누가 겉치레인지 관찰하세요. 진정한 친구는 당신이 아첨할 필요가 없습니다.",
        f"\n\nလူမှုဆက်ဆံရေး/ခရီးသွားခြင်းနှင့်ပတ်သက်၍ '{focus_kin}'သည် သင့်လူမှုဆက်ဆံရေးနှင့် ခရီးသွားခြင်းကို အောက်ပါအတိုင်း သက်ရောက်ပါသည် —"
        f"\n\n• လူမှုဆက်ဆံရေး — မကြာသေးခင်က သင့်လူမှုဆက်ဆံရေးအသိုက်အဝန်းတွင် ပြောင်းလဲမှုများ ရှိနိုင်ပါသည် — အသစ်သောမိတ်ဆွေများနှင့် တွေ့နိုင်သလို အချို့သောသူများနှင့် ဝေးကွာသွားနိုင်ပါသည်။ ဒါသည် ပုံမှန်လူမှုဆက်ဆံရေး အပြောင်းအလဲဖြစ်ပြီး အလွန်စိတ်ပူစရာ မလိုပါ။"
        f"\n• အလုပ်ခွင်ဆက်ဆံရေး — လုပ်ဖော်ဆွေများ၊ အထက်အရာရှိများနှင့် ဆက်ဆံရေးကို စိတ်နှလုံးထား၍ ထိန်းသိမ်းပါ။ သဘောထားကွဲလွဲသည့်အခါ ဆန့်ကျင်ဘက်က နောက်ဆုံးထိ နားထောင်ပြီးမှ ကိုယ့်အမြင်ကို ပြောပါ။"
        f"\n• မိသားစုဆက်ဆံရေး — မကြာသေးခင်က မိသားစုနှင့် ပဋိပက္ခရှိပါက တက်ကြွစွာ ရုတ်သိမ်းပါ။ 'ပင်ပန်းပါတယ်' ဟု တစ်ခွန်းနှစ်ခွန်း ပြောခြင်း သို့မဟုတ် အိမ်ချက်ထမင်းစားခြင်းသည် အကြောင်းရင်းရှည်ရှည်ပြောခြင်းထက် ပို၍ထိရောက်ပါသည်။"
        f"\n• ခရီးသွားလာရေးလုံခြုံရေး — မကြာသေးခင်က ရင်းနှီးသည့် လမ်းကြောင်းနှင့် သွားလာရေးယာဉ်ကို ရွေးချယ်ပါ။ ရင်းနှီးမကျွမ်းသည့်နေရာသို့ သွားပါက ကြိုတင်စီစဉ်ပါ။ ကားမောင်းသူများက အရေးပေါ်ဥပဒေကို လိုက်နာပြီး ပင်ပန်းနေချိန် မမောင်းပါနှင့်။"
        f"\n• လူမှုရေးလုပ်ဆောင်ပွဲများ — ပွဲလှည့်ပွဲ သို့မဟုတ် လူမှုရေးလုပ်ဆောင်ပွဲများတွင် များများနားထောင်ပြီး နည်းနည်းပြောပါ။ ဘယ်သူက စစ်မှန်၊ ဘယ်သူက မျက်နှာပြချည်းဖြစ်ကြောင်း ကြည့်ပါ။ စစ်မှန်သည့်မိတ်ဆွေများသည် သင့်ကို ထောက်ခံအားပေးစရာ မလိုပါ။"
    )

    travel_future_extra = L(
        f"\n\n人际/出行未来趋势："
        f"\n\n• 社交机遇：未来1-3个月，你可能会在工作、学习或兴趣活动中遇到志同道合的人。保持开放心态，主动与人交流。"
        f"\n\n• 需要远离的人：如果某段关系让你感到消耗、疲惫或不被尊重，适当保持距离不是冷漠，而是自我保护。"
        f"\n\n• 出行吉日：如果有出行计划，选择天气好、心情好的日子出发。旅行时保持灵活，不要太执着于原定计划。"
        f"\n\n• 贵人方位：近期你的贵人可能出现在「{focus_kin}」相关的方位或场合。多关注这个方向的人和事。",
        f"\n\n人际/出行の将来の流れ："
        f"\n\n• 社交チャンス：今後1-3ヶ月、仕事・学習・趣味の場で志を同じくする人に出会えるかもしれません。オープンな姿勢で積極的に交流を。"
        f"\n\n• 離れるべき相手：ある関係が消耗感や疲労感、尊重されない気持ちを与えるなら、適度な距離を保つのは冷淡ではなく自己防衛です。"
        f"\n\n• 出行の吉日：旅行计划があるなら、天気と気分の良い日に。旅行中は柔軟に、予定通りに行かないことも受け入れましょう。"
         f"\n\n• お貴人の方角：近いうちにあなたの貴人は「{focus_kin}」に関連する方角や場に現れるかもしれません。この方向の人と事に関心を。"
        ,
        f"\n\nPeople/travel future trends:"
        f"\n\n• Social opportunities: In the next 1-3 months, you may meet like-minded people through work, study, or hobbies. Stay open and engage actively."
        f"\n\n• People to distance from: If a relationship drains you, makes you tired, or feels disrespected, keeping appropriate distance isn't cold — it's self-protection."
        f"\n\n• Auspicious travel: If you have travel plans, depart on days with good weather and mood. Stay flexible during travel — don't cling too tightly to original plans."
        f"\n\n• Mentor direction: Your mentor may appear in a setting related to '{focus_kin}'. Pay attention to people and events in this direction.",
        f"\n\nĐi lại tương lai:"
        f"\n\n• Cơ hội xã hội: Trong 1-3 tháng tới, bạn có thể gặp người cùng chí hướng qua công việc, học tập hoặc sở thích. Giữ thái độ mở, chủ động giao tiếp."
        f"\n\n• Người nên xa: Nếu mối quan hệ nào đó khiến bạn cảm thấy kiệt sức, mệt mỏi hoặc không được tôn trọng, giữ khoảng cách phù hợp không phải lạnh nhạt mà là tự bảo vệ."
        f"\n\n• Ngày đi lại tốt: Nếu có kế hoạch đi lại, xuất phát vào ngày thời tiết tốt và tâm trạng vui. Khi đi du lịch giữ sự linh hoạt, đừng bám quá chặt vào kế hoạch gốc."
        f"\n\n• Hướng quý nhân: Gần đây quý nhân có thể xuất hiện ở「{focus_kin}」liên quan đến phương hướng hoặc hoàn cảnh. Chú ý đến con người và sự việc ở hướng này.",
        f"\n\n인간관계/여행 미래 흐름:"
        f"\n\n• 사교 기회: 향후 1-3개월 내에 업무, 학습, 취미 활동을 통해 뜻이 같은 사람을 만날 수 있습니다. 열린 자세로 적극적으로 소통하세요."
        f"\n\n• 멀리해야 할 사람: 어떤 관계가 소진감, 피로감, 존중받지 못하는 느낌을 준다면 적절한 거리를 두는 것은 냉담함이 아니라 자기 보호입니다."
        f"\n\n• 여행 길일: 여행 계획이 있다면 날씨가 좋고 기분이 좋은 날에 출발하세요. 여행 중에는 유연하게, 원래 계획대로 되지 않는 것도 받아들이세요."
        f"\n\n• 귀인 방향: 가까운 시일에 귀인이 '{focus_kin}'과 관련된 방향이나 상황에 나타날 수 있습니다. 이 방향의 사람과 일에 관심을 기울이세요.",
        f"\n\nလူမှုဆက်ဆံရေး/ခရီးသွားခြင်း အနာဂတ်လမ်းကြောင်း —"
        f"\n\n• လူမှုဆက်ဆံရေးအခွင့်အရေး — နောက်လပေါင်း ၁-၃ အတွင်း အလုပ်၊ ပညာရေး သို့မဟုတ် ဝါသနာလုပ်ဆောင်ချက်များမှတစ်ဆင့် တူညီသည့် စိတ်ကူးရှိသူများကို တွေ့နိုင်ပါသည်။ ဖွင့်ထားသည့် စိတ်ဓာတ်ဖြင့် တက်ကြွစွာ ဆက်သွယ်ပါ။"
        f"\n• ဝေးကွာသင့်သည့်သူများ — ဆက်ဆံရေးတစ်ခုက သင့်ကို ပင်ပန်းစေ၊ မောပန်းစေ သို့မဟုတ် တန်ဖိုးမထားကြောင်း ခံစားရပါက သင့်တော်သည့်အကွာအဝေးထားခြင်းသည် အေးစိမ်းခြင်းမဟုတ်ဘဲ ကိုယ့်ကိုယ်ကို ကာကွယ်ခြင်းဖြစ်သည်။"
        f"\n• ခရီးသွားခြင်း ကောင်းသည့်နေ့ — ခရီးသွားခြင်း အစီအစဉ်ရှိပါက ရာသီဥတုကောင်းပြီး စိတ်ချမ်းသာသည့်နေ့တွင် ထွက်ပါ။ ခရီးတွင် လိုက်လျောညီထွေရှိပြီး မူလအစီအစဉ်ကို တင်းကျပ်စွာ မကိုင်စွဲပါနှင့်။"
        f"\n• ကောင်းချက်ဦးတည်ချက် — မကြာမီကာလတွင် သင့်ကောင်းချက်သည် '{focus_kin}' နှင့်ဆက်စပ်သည့် ဦးတည်ချက် သို့မဟုတ် အခြေအနေတွင် ပေါ်လာနိုင်ပါသည်။ ဤဦးတည်ချက်မှ လူများနှင့် ဖြစ်ရပ်များကို အာရုံစိုက်ပါ။"
    )

    travel_adv_extra = L(
        f"\n\n【具体行动建议】"
        f"\n\n1. 主动破冰：如果和某人有误会，主动发一条消息或打一个电话。大多数矛盾都源于沟通不足。"
        f"\n\n2. 真诚赞美：发现别人的优点并真诚地说出来。一句具体的赞美（如「你今天的方案做得很好」）比泛泛的夸奖（如「你真棒」）更让人暖心。"
        f"\n\n3. 学会拒绝：不想参加的聚会、不合理的要求，礼貌但坚定地拒绝。你的时间和精力是有限的资源。"
        f"\n\n4. 出行准备：长途旅行前检查证件、预订住宿、了解当地天气和文化。随身携带常用药品。"
        f"\n\n5. 记录美好：旅行或聚会时拍些照片、写些日记。这些记录会在将来成为美好的回忆。",
        f"\n\n【具体的アクションアドバイス】"
        f"\n\n1. 自ら冰を砕く：誰かと誤解があるなら、自分からメッセージや電話を。ほとんどの問題はコミュニケーション不足から来ています。"
        f"\n\n2. 真摯な褒め言葉：相手の長所を発見して真心で伝えましょう。具体的な褒め言葉（「今日の提案、とてもよかった」）は、曖昧な称賛（「すごいね」）より心に届きます。"
        f"\n\n3. 断る力を：参加したくないパーティー、不合理な要請は丁寧にしかし毅然と断りましょう。あなたの時間とエネルギーは限られた資源です。"
        f"\n\n4. 出行準備：長期旅行前には書類確認、宿泊予約、現地の天気と文化の確認を。常用薬も携帯を。"
        f"\n\n5. 美しい記録：旅行や聚会で写真を撮ったり日記を書いたり。これらの記録は将来美好的な思い出になります。",
        f"\n\n【Specific Action Advice】"
        f"\n\n1. Break the ice: If there's a misunderstanding with someone, message or call first. Most conflicts stem from insufficient communication."
        f"\n\n2. Genuine compliments: Notice others' strengths and say them sincerely. A specific compliment ('your proposal today was excellent') warms hearts more than generic praise ('you're great')."
        f"\n\n3. Learn to decline: Politely but firmly refuse gatherings you don't want to attend or unreasonable requests. Your time and energy are limited resources."
        f"\n\n4. Travel prep: Before long trips, check documents, book accommodation, research local weather and culture. Carry common medicines."
        f"\n\n5. Record the good: Take photos or keep a journal during travel or gatherings. These records become beautiful memories in the future.",
        f"\n\n【Hành động cụ thể】"
        f"\n\n1. Chủ động phá vỡ: Nếu có hiểu lầm với ai đó, chủ động gửi tin nhắn hoặc gọi điện. Hầu hết mâu thuẫn đều do giao tiếp không đủ."
        f"\n\n2. Khen ngợi chân thành: Nhận ra điểm mạnh của người khác và nói ra bằng sự chân thành. Một lời khen cụ thể（「hôm nay proposal của bạn rất tốt」）ấm lòng hơn khen chung chung."
        f"\n\n3. Học cách từ chối: Từ chối lịch sự nhưng kiên quyết những buổi tiệc không muốn tham gia, yêu cầu không hợp lý. Thời gian và năng lượng của bạn là tài nguyên có hạn."
        f"\n\n4. Chuẩn bị đi lại: Trước chuyến đi xa, kiểm tra giấy tờ, đặt chỗ ở, tìm hiểu thời tiết và văn hóa địa phương. Mang theo thuốc thường dùng."
        f"\n\n5. Lưu giữ kỷ niệm đẹp: Chụp ảnh hoặc viết nhật ký khi đi du lịch hoặc dự tiệc. Những kỷ niệm này sẽ trở thành ký ức đẹp trong tương lai.",
        f"\n\n【구체적인 행동 조언】"
        f"\n\n1. 얼음 깨기: 누군가와 오해가 있다면 먼저 메시지나 전화를 하세요. 대부분의 갈등은 소통 부족에서 비롯됩니다."
        f"\n\n2. 진정한 칭찬: 상대의 장점을 발견하고 진심으로 말하세요. 구체적인 칭찬(\"오늘 제안이 정말 좋았어\")이 일반적인 칭찬(\"대단해\")보다 마음에 와닿습니다."
        f"\n\n3. 거절하는 법 배우기: 가고 싶지 않은 모임, 부당한 요구는 정중하지만 단호하게 거절하세요. 당신의 시간과 에너지는 한정된 자원입니다."
        f"\n\n4.여행 준비: 장거리 여행 전에 서류 확인, 숙소 예약, 현지 날씨와 문화 조사를 미리 하세요. 상비약도 챙기세요."
        f"\n\n5. 아름다운 기록: 여행이나 모임에서 사진을 찍거나 일기를 쓰세요. 이 기록들은 미래에 아름다운 추억이 됩니다.",
        f"\n\n【လက်တွေ့လုပ်ဆောင်ရန် အကြံပြုချက်များ】"
        f"\n\n၁။ တက်ကြွစွာ ရုတ်သိမ်းပါ — မည်သူ့နှင့်မဆို နားလည်မှုလွဲနေပါက မက်ဆေ့ချ်တစ်စောင် သို့မဟုတ် ဖုန်းခေါ်ပါ။ ပဋိပက္ခအများစုသည် ဆက်သွယ်ရေးမလုံလောက်ခြင်းမှ ဖြစ်ပေါ်လာခြင်းဖြစ်သည်။"
        f"\n၂။ စစ်မှန်သည့်ချီးကျူးခြင်း — အခြားသူများ၏ အားသာချက်များကို တွေ့ရှိပြီး စစ်မှန်စွာ ပြောပါ။ တိကျသည့်ချီးကျူးခြင်း ('သင့်အဆိုပြုချက် အမှန်ကောင်းပါတယ်') သည် ယေဘုယျချီးကျူးခြင်း ('သင် အရမ်းကောင်းတယ်') ထက် ပို၍ နှလုံးကျေနပ်စေပါသည်။"
        f"\n၃။ ငြင်းဆိုခြင်းကို သင်ယူပါ — တက်ချင်ခြင်းမရှိသည့် ပွဲလှည့်ပွဲများ၊ မတရားသည့်တောင်းဆိုမှုများကို ယဉ်ကျေးစွာ သို့သော် ညင်သာစွာ ငြင်းဆိုပါ။ သင့်အချိန်နှင့် စွမ်းအင်သည် ကန့်သတ်ထားသည့် အရင်းအမြစ်များဖြစ်သည်။"
        f"\n၄။ ခရီးသွားခြင်းပြင်ဆင် — ရှည်လျားသည့်ခရီးမတိုင်ခင် စာရွက်စာတမ်းများ စစ်ဆေးခြင်း၊ တည်းခိုခန်း ကြိုတင်မှာယူခြင်း၊ ဒေသခံရာသီဥတုနှင့် ယဉ်ကျေးမှုကို ကြိုတင်လေ့လာခြင်း စသည်တို့ လုပ်ပါ။ ပုံမှန်ဆေးဝါးများ ပါသွားပါ။"
        f"\n၅။ ကောင်းသည့်အမှတ်တရများ မှတ်တမ်းတင်ပါ — ခရီးသွားခြင်း သို့မဟုတ် ပွဲလှည့်ပွဲများတွင် ဓာတ်ပုံရိုက်ခြင်း သို့မဟုတ် မှတ်စုရေးခြင်း လုပ်ပါ။ ဤမှတ်တမ်းများသည် အနာဂတ်တွင် လှပသည့် အမှတ်တရများ ဖြစ်လာပါမည်။"
    )

    analysis["travel"] = block(
        L(travel_title.get("zh", "人际 / 出行"), travel_title.get("ja", "人間関係・お出かけ"),
          travel_title.get("en", "People / Travel"), travel_title.get("vi", "Quan hệ / Đi lại"),
          travel_title.get("ko", "인간관계 / 외출"), travel_title.get("my", "လူမှုဆက်ဆံရေး")),
        L(travel_desc.get("zh", "") + travel_now_extra["zh"], travel_desc.get("ja", "") + travel_now_extra["ja"],
          travel_desc.get("en", "") + travel_now_extra["en"], travel_desc.get("vi", "") + travel_now_extra["vi"],
          travel_desc.get("ko", "") + travel_now_extra["ko"], travel_desc.get("my", "") + travel_now_extra["my"]),
        travel_future_extra,
        travel_adv_extra,
    )

    return analysis


# ========== 路由 ==========

@app.route("/")
def index():
    lang = request.args.get("lang")
    if not lang or lang not in LANGS:
        lang_options = [
            ("zh", "Chinese", "\u4e2d\u6587", "\U0001F1E8\U0001F1F3"),
            ("ja", "Japanese", "\u65e5\u672c\u8a9e", "\U0001F1EF\U0001F1F5"),
            ("en", "English", "English", "\U0001F1FA\U0001F1F8"),
            ("vi", "Vietnamese", "Ti\u1ebfng Vi\u1ec7t", "\U0001F1FB\U0001F1F3"),
            ("ko", "Korean", "\ud55c\uad6d\uc5b4", "\U0001F1F0\U0001F1F7"),
            ("my", "Myanmar", "\u1019\u103c\u1014\u103a\u1019\u102c\u1018\u102c", "\U0001F1F2\U0001F1F2"),
        ]
        return render_template("welcome.html", lang="en", t=TEXTS["en"], wt=TEXTS["welcome_texts"]["en"],
                               welcome_json=json.dumps(TEXTS["welcome_texts"]), lang_options=lang_options,
                               lang_urls={code: url_for("index", lang=code) for code in LANGS})
    t = TEXTS.get(lang, TEXTS["zh"])
    lang_urls = {code: url_for("index", lang=code) for code in LANGS}
    daily = get_daily_fortune(lang)
    return render_template("index.html", lang=lang, t=t, lang_urls=lang_urls, daily=daily)


@app.route("/welcome")
def welcome():
    lang_options = [
        ("zh", "Chinese", "\u4e2d\u6587", "\U0001F1E8\U0001F1F3"),
        ("ja", "Japanese", "\u65e5\u672c\u8a9e", "\U0001F1EF\U0001F1F5"),
        ("en", "English", "English", "\U0001F1FA\U0001F1F8"),
        ("vi", "Vietnamese", "Ti\u1ebfng Vi\u1ec7t", "\U0001F1FB\U0001F1F3"),
        ("ko", "Korean", "\ud55c\uad6d\uc5b4", "\U0001F1F0\U0001F1F7"),
        ("my", "Myanmar", "\u1019\u103c\u1014\u103a\u1019\u102c\u1018\u102c", "\U0001F1F2\U0001F1F2"),
    ]
    t = TEXTS["en"]
    wt = TEXTS["welcome_texts"]["en"]
    lang_urls = {code: url_for("index", lang=code) for code in LANGS}
    return render_template("welcome.html", lang="en", t=t, wt=wt,
                           welcome_json=json.dumps(TEXTS["welcome_texts"]),
                           lang_options=lang_options, lang_urls=lang_urls)


@app.route("/welcome/<lang>")
def welcome_guide(lang):
    if lang not in LANGS:
        lang = "zh"
    lang_options = [
        ("zh", "Chinese", "\u4e2d\u6587", "\U0001F1E8\U0001F1F3"),
        ("ja", "Japanese", "\u65e5\u672c\u8a9e", "\U0001F1EF\U0001F1F5"),
        ("en", "English", "English", "\U0001F1FA\U0001F1F8"),
        ("vi", "Vietnamese", "Ti\u1ebfng Vi\u1ec7t", "\U0001F1FB\U0001F1F3"),
        ("ko", "Korean", "\ud55c\uad6d\uc5b4", "\U0001F1F0\U0001F1F7"),
        ("my", "Myanmar", "\u1019\u103c\u1014\u103a\u1019\u102c\u1018\u102c", "\U0001F1F2\U0001F1F2"),
    ]
    t = TEXTS.get(lang, TEXTS["en"])
    wt = TEXTS["welcome_texts"].get(lang, TEXTS["welcome_texts"]["en"])
    lang_urls = {code: url_for("index", lang=code) for code in LANGS}
    return render_template("welcome.html", lang=lang, t=t, wt=wt,
                           welcome_json=json.dumps(TEXTS["welcome_texts"]),
                           lang_options=lang_options, lang_urls=lang_urls)


@app.route("/result", methods=["POST"])
def result():
    lang = get_lang()
    t = TEXTS[lang]

    method = sanitize_input(request.form.get("method", "coin"), 10)
    if method not in ("coin", "time", "number"):
        method = "coin"
    question = sanitize_input(request.form.get("question", ""), 500)
    number_raw = sanitize_input(request.form.get("number", ""), 10)
    category = sanitize_input(request.form.get("category", "general"), 20)
    if category not in ("general", "love", "career", "wealth", "health", "people", "random"):
        category = "general"

    number_val = None
    if method == "number":
        if validate_number(number_raw):
            number_val = int(number_raw)
        else:
            number_val = 0

    lines, moving = make_lines(method, number_val)
    liuchin = calc_liuchin(lines, lang)
    hex_code = lines_to_code(lines)
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Check for duplicate question within 5 minutes
    dup_warning = ""
    if question:
        with db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, created_at FROM history WHERE question=? AND created_at > datetime('now', '-5 minutes') ORDER BY id DESC LIMIT 1",
                (question,),
            )
            dup = cur.fetchone()
        if dup:
            dup_warning = {"zh": "你刚才已经就同一问题占过一卦（5分钟内），建议静心后再问。", "ja": "5分前に同じ質問で占いました。落ち着いてから再度占いましょう。", "en": "You already asked the same question within 5 minutes. Take a moment before asking again.", "vi": "Bạn vừa hỏi cùng câu hỏi trong vòng 5 phút. Hãy bình tâm trước khi hỏi lại.", "ko": "5분 안에 같은 질문으로 점을 보셨습니다. 차분해진 후 다시 보세요.", "my": "သင်သည် ၅ မိနစ်အတွင်း မေးခွန်းတူညီမှုကို ထပ်မံမေးပြီးဖြစ်ပါသည်။ ငြိမ်သက်စွာ စဉ်းစားပြီးမှ ထပ်မံမေးပါ။"}.get(lang, "")

    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO history (method, question, category, hex_code, lines, moving, liuchin, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                method,
                question,
                category,
                hex_code,
                json.dumps(lines, ensure_ascii=False),
                json.dumps(moving, ensure_ascii=False),
                json.dumps(liuchin, ensure_ascii=False),
                created_at,
            ),
        )
        hid = cur.lastrowid
        conn.commit()
    logger.info("New divination: id=%d method=%s category=%s hex=%d", hid, method, category, hex_code)

    return redirect(url_for("view", hid=hid, lang=lang))


@app.route("/history")
def history():
    lang = get_lang()
    t = TEXTS[lang]
    query = sanitize_input(request.args.get("q", ""), 100)
    time_range = request.args.get("time", "")

    with db_connection() as conn:
        cur = conn.cursor()
        conditions = []
        params = []

        if query:
            safe_query = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            conditions.append("(question LIKE ? ESCAPE '\\' OR hex_code LIKE ? ESCAPE '\\')")
            params.extend([f"%{safe_query}%", f"%{safe_query}%"])

        if time_range == "today":
            conditions.append("DATE(created_at) = DATE('now')")
        elif time_range == "week":
            conditions.append("created_at >= DATE('now', '-7 days')")
        elif time_range == "month":
            conditions.append("created_at >= DATE('now', '-30 days')")

        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        cur.execute(f"SELECT id, method, question, hex_code, created_at FROM history{where} ORDER BY id DESC", params)
        rows = cur.fetchall()

    lang_urls = {code: url_for("history", lang=code) for code in LANGS}
    hex_names = {}
    for code in range(64):
        name = get_hex_name(code)
        hex_names[code] = name.get(lang, name.get("en", str(code+1)))
    return render_template("history.html", lang=lang, t=t, rows=rows, lang_urls=lang_urls, hex_names=hex_names, time_range=time_range)


@app.route("/view/<int:hid>")
def view(hid):
    lang = get_lang()
    t = TEXTS[lang]

    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, method, question, category, hex_code, lines, moving, liuchin, starred, created_at FROM history WHERE id=?",
            (hid,),
        )
        row = cur.fetchone()

    if not row:
        t = TEXTS.get(lang, TEXTS["zh"])
        lang_urls = {code: url_for("view", hid=hid, lang=code) for code in LANGS}
        return render_template("error.html", lang=lang, t=t, lang_urls=lang_urls, code=404, message=t.get("error_record_not_found", "Record Not Found")), 404

    _, method, question, category, hex_code, lines_json, moving_json, liuchin_json, starred, created_at = row

    try:
        lines = json.loads(lines_json)
    except Exception:
        lines = [0, 0, 0, 0, 0, 0]

    try:
        moving = json.loads(moving_json)
    except Exception:
        moving = []

    try:
        liuchin = json.loads(liuchin_json)
    except Exception:
        liuchin = calc_liuchin(lines, lang)

    analysis = build_analysis(lines, moving, liuchin, hex_code)
    hex_no = hex_code + 1

    # Calculate changed hexagram (变卦)
    changed_lines = calc_changed_lines(lines, moving)
    changed_code = lines_to_code(changed_lines)
    changed_no = changed_code + 1

    # Moving line analysis
    moving_analysis = analyze_moving_lines(lines, moving, lang)

    # Trend analysis
    trend_analysis = build_trend_analysis(hex_code, changed_code, len(moving))

    # Fortune comparison between 本卦 and 变卦
    fortune_comparison = build_fortune_comparison(hex_code, changed_code)

    # Concise summary
    summary_text = build_summary(hex_code, lines, moving, category, lang)
    dup_warning = ""

    # Get hexagram names and meanings from hexinterp
    hex_name = get_hex_name(hex_code)
    hex_meaning = get_hex_meaning(hex_code)
    changed_name = get_hex_name(changed_code)
    changed_meaning = get_hex_meaning(changed_code)

    # Get hexagram interpretations
    hex_interp = INTERPRETATIONS.get(hex_code, {})
    changed_interp = INTERPRETATIONS.get(changed_code, {})

    lang_urls = {code: url_for("view", hid=hid, lang=code) for code in LANGS}

    return render_template(
        "result.html",
        lang=lang,
        t=t,
        lang_urls=lang_urls,
        hid=hid,
        method=method,
        question=question,
        created_at=created_at,
        hex_no=hex_no,
        lines=lines,
        moving=moving,
        liuchin=liuchin,
        analysis=analysis,
        # Changed hexagram data
        changed_lines=changed_lines,
        changed_no=changed_no,
        # Hexagram metadata
        hex_name=hex_name,
        hex_meaning=hex_meaning,
        changed_name=changed_name,
        changed_meaning=changed_meaning,
        # Hexagram interpretations
        hex_interp=hex_interp,
        changed_interp=changed_interp,
        # New analysis data
        moving_analysis=moving_analysis,
        trend_analysis=trend_analysis,
        fortune_comparison=fortune_comparison,
        summary_text=summary_text,
        dup_warning=dup_warning,
        starred=starred,
        glossary=GLOSSARY.get(lang, GLOSSARY.get("zh", {})),
    )


@app.route("/star/<int:hid>", methods=["POST"])
def star(hid):
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT starred FROM history WHERE id=?", (hid,))
        row = cur.fetchone()
        if row:
            new_val = 0 if row[0] else 1
            cur.execute("UPDATE history SET starred=? WHERE id=?", (new_val, hid))
            conn.commit()
    lang = request.form.get("lang", "zh")
    return redirect(url_for("view", hid=hid, lang=lang))


@app.route("/random")
def random_hex():
    lang = get_lang()
    t = TEXTS.get(lang, TEXTS["zh"])
    lines, moving = make_lines("coin", None)
    liuchin = calc_liuchin(lines, lang)
    hex_code = lines_to_code(lines)
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO history (method, question, category, hex_code, lines, moving, liuchin, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("coin", t.get("random_question", "Quick Cast"), "random", hex_code,
             json.dumps(lines, ensure_ascii=False),
             json.dumps(moving, ensure_ascii=False),
             json.dumps(liuchin, ensure_ascii=False),
             created_at),
        )
        hid = cur.lastrowid
        conn.commit()
    logger.info("Quick cast: id=%d hex=%d", hid, hex_code)
    return redirect(url_for("view", hid=hid, lang=lang))


@app.route("/cast/<int:hex_code>")
def cast_hex(hex_code):
    lang = get_lang()
    t = TEXTS.get(lang, TEXTS["zh"])

    if hex_code < 0 or hex_code > 63:
        hex_code = random.randint(0, 63)

    interp = INTERPRETATIONS.get(hex_code, {})
    lines = []
    for i in range(6):
        lines.append((hex_code >> i) & 1)

    liuchin = calc_liuchin(lines, lang)
    moving = []
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO history (method, question, category, hex_code, lines, moving, liuchin, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("gallery", t.get("nav_gallery", "Hexagram Atlas"), "general", hex_code,
             json.dumps(lines, ensure_ascii=False),
             json.dumps(moving, ensure_ascii=False),
             json.dumps(liuchin, ensure_ascii=False),
             created_at),
        )
        hid = cur.lastrowid
        conn.commit()
    return redirect(url_for("view", hid=hid, lang=lang))


@app.route("/gallery")
def gallery():
    lang = get_lang()
    t = TEXTS.get(lang, TEXTS["zh"])
    lang_urls = {code: url_for("gallery", lang=code) for code in LANGS}
    hex_list = []
    for code in range(64):
        name = get_hex_name(code)
        meaning = get_hex_meaning(code)
        hex_list.append({"code": code, "no": code + 1, "name": name, "meaning": meaning})
    return render_template("gallery.html", lang=lang, t=t, lang_urls=lang_urls, hex_list=hex_list)


@app.route("/stats")
def stats():
    lang = get_lang()
    t = TEXTS.get(lang, TEXTS["zh"])
    with db_connection() as conn:
        cur = conn.cursor()

        # Total count
        cur.execute("SELECT COUNT(*) FROM history")
        total = cur.fetchone()[0]

        # Hexagram distribution
        cur.execute("SELECT hex_code, COUNT(*) as cnt FROM history GROUP BY hex_code ORDER BY cnt DESC")
        hex_dist = cur.fetchall()

        # Category distribution
        cur.execute("SELECT category, COUNT(*) as cnt FROM history WHERE category != '' GROUP BY category ORDER BY cnt DESC")
        cat_dist = cur.fetchall()

        # Method distribution
        cur.execute("SELECT method, COUNT(*) as cnt FROM history GROUP BY method ORDER BY cnt DESC")
        method_dist = cur.fetchall()

        # Starred count
        cur.execute("SELECT COUNT(*) FROM history WHERE starred=1")
        starred_count = cur.fetchone()[0]

        # Recent activity (last 7 days)
        cur.execute("SELECT DATE(created_at) as day, COUNT(*) FROM history WHERE created_at >= DATE('now', '-7 days') GROUP BY day ORDER BY day")
        recent = cur.fetchall()

    # Map codes to names
    hex_names = {}
    for code in range(64):
        name = get_hex_name(code)
        hex_names[code] = name.get(lang, name.get("en", str(code+1)))

    method_names = {"coin": t.get("method_name_coin", "Coin"), "time": t.get("method_name_time", "Time"), "number": t.get("method_name_number", "Number")}
    cat_names = {
        "general": t.get("cat_general", "General"), "love": t.get("cat_love", "Love"),
        "career": t.get("cat_career", "Career"), "wealth": t.get("cat_wealth", "Wealth"),
        "health": t.get("cat_health", "Health"), "people": t.get("cat_people", "People"),
        "random": t.get("cat_random", "Random"),
    }

    lang_urls = {code: url_for("stats", lang=code) for code in LANGS}
    return render_template("stats.html", lang=lang, t=t, lang_urls=lang_urls,
        total=total, starred_count=starred_count,
        hex_dist=hex_dist, hex_names=hex_names,
        cat_dist=cat_dist, cat_names=cat_names,
        method_dist=method_dist, method_names=method_names,
        recent=recent)


@app.route("/starred")
def starred():
    lang = get_lang()
    t = TEXTS.get(lang, TEXTS["zh"])
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, method, question, hex_code, created_at FROM history WHERE starred=1 ORDER BY id DESC")
        rows = cur.fetchall()
    lang_urls = {code: url_for("starred", lang=code) for code in LANGS}
    hex_names = {}
    for code in range(64):
        name = get_hex_name(code)
        hex_names[code] = name.get(lang, name.get("en", str(code+1)))
    return render_template("history.html", lang=lang, t=t, rows=rows, lang_urls=lang_urls, title_override=t.get("nav_starred", "收藏记录"), hex_names=hex_names, time_range="")


if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    print("Initializing database sixyao2.db ...")
    init_db()
    migrate_db()
    print("Starting: http://127.0.0.1:8888")
    app.run(debug=True, host="127.0.0.1", port=8888)
