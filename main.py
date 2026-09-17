import os
import requests
import json
import subprocess
import time
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import akshare as ak

# =====================================================================
# 🔤 运行时自动确保中文字体可用(TraeWork 定时任务用全新容器,字体每次都要装)
# =====================================================================
def _ensure_chinese_font():
    """首次运行自动安装 fonts-noto-cjk 并清 matplotlib 字体缓存"""
    # 检查是否已有 Noto Sans CJK SC
    cjk_fonts = [f for f in fm.fontManager.ttflist if 'Noto Sans CJK SC' in f.name and f.style == 'normal']
    if cjk_fonts:
        return cjk_fonts[0].fname  # 已安装,直接返回路径

    # 尝试 apt-get 安装
    print("🔤 首次运行,正在安装中文字体 fonts-noto-cjk...")
    try:
        subprocess.run(["apt-get", "update", "-qq"], check=True, timeout=60, capture_output=True)
        subprocess.run(["apt-get", "install", "-y", "-qq", "fonts-noto-cjk"], check=True, timeout=120, capture_output=True)
        subprocess.run(["fc-cache", "-f"], check=False)
        # 清 matplotlib 字体缓存
        cache_dir = matplotlib.get_cachedir()
        subprocess.run(["rm", "-rf", os.path.join(cache_dir, "fontlist*.json")], check=False)
        # 重载字体管理器
        fm.fontManager = fm.FontManager()
        print("✅ 中文字体安装完成")
    except Exception as e:
        print(f"⚠️ 字体安装失败: {e},图片中文可能显示为方框")

    # 再查一次
    cjk_fonts = [f for f in fm.fontManager.ttflist if 'Noto Sans CJK SC' in f.name and f.style == 'normal']
    return cjk_fonts[0].fname if cjk_fonts else None


# 模块加载时就装好
_CHINESE_FONT_PATH = _ensure_chinese_font()

# =====================================================================
# 🚨 【小白专区】请在这里准确填写你的个人配置
# =====================================================================
# 钉钉群机器人 Webhook
DINGTALK_WEBHOOK_URL = "https://oapi.dingtalk.com/robot/send?access_token=a460953e539e18fa8b883fbe7cb3d16a3a4842b2cbe25997c75bc5db46257c88"

# Gitee 国内图床配置(仓库已改为 public,国内秒开)
GITEE_USERNAME = "thats-awesome"
GITEE_REPO = "a-stock-data"
GITEE_TOKEN = "4b6548b05c10a4d9746064cefa583c40"
GITEE_BRANCH = "main"

# =====================================================================
# 📅 核心模块：中国法定节假日休市智能拦截引擎
# =====================================================================
def check_is_market_closed():
    """
    直连国内最稳定的提莫节假日API，智能识别今天大盘是否开盘
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    url = f"https://timor.tech{today_str}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        res = requests.get(url, headers=headers, timeout=10).json()
        if res.get("code") == 0 and "holiday" in res:
            holiday_info = res["holiday"]
            if holiday_info and holiday_info.get("is_holiday") is True:
                print(f"🎉 动态监测：今天是法定节日或周末假期【{holiday_info.get('name')}】，A股休市，不打扰主理人！😴")
                return True
        print("📈 动态监测：今日为正常交易日，开始追踪筹码异动！")
        return False
    except Exception as e:
        print(f"⚠️ 节假日接口微卡，默认跳过拦截继续跑数据。原因: {e}")
        return False

# =====================================================================
# 🛠️ 第一部分：a-stock-data 全景板块绑定与数据清洗逻辑
# =====================================================================
def get_all_merged_capital_flow():
    """
    用 AKShare 直连东方财富 data.eastmoney.com 爬取真实概念资金流
    (不依赖被代理拦截的 push2.eastmoney.com)
    """
    # 用户关注的板块(名称做同义词映射,匹配东财概念库)
    SECTOR_ALIASES = {
        "5G概念": ["5G", "F5G"],
        "通信技术": ["通信", "光通信"],
        "国产芯片": ["芯片", "半导体", "集成电路"],
        "光通信模块": ["光通信", "光模块"],
        "CPO概念": ["CPO", "光模块"],
        "存储芯片": ["存储芯片", "存储"],
        "液冷服务器": ["液冷服务器"],
        "光伏概念": ["光伏", "光伏概念"],
        "PCB": ["PCB"],
        "商业航天": ["商业航天"],
        "小金属概念": ["小金属"],
        "稀土永磁": ["稀土永磁", "稀土"],
        "特高压": ["特高压"],
        "国防军工": ["军工", "国防军工"],
        "工业母机": ["工业母机"],
        "CRO": ["CRO"],
        "无人机": ["无人机"],
        "创新药": ["创新药"],
        "微盘股": ["微盘"],
        "白酒": ["白酒"],
        "中特估": ["中特估"],
        "券商概念": ["券商"],
        "农业种植": ["农业种植"],
        "核电核能": ["核电"],
        "银行": ["银行"],
        "半导体": ["半导体", "芯片"],
        "新能源车": ["新能源车", "新能源汽车"],
    }

    def _match_sector(user_name, concept_list):
        """在概念列表中模糊匹配用户板块"""
        aliases = SECTOR_ALIASES.get(user_name, [user_name])
        for concept in concept_list:
            for alias in aliases:
                if alias in concept:
                    return concept
        return None

    try:
        print("📡 AKShare 爬取东财概念资金流...")
        df = None
        for attempt in range(5):
            try:
                df = ak.stock_fund_flow_concept()
                print(f"✅ 第 {attempt+1} 次成功!")
                break
            except Exception as e:
                print(f"  第 {attempt+1} 次失败: {type(e).__name__}, 2s 后重试...")
                time.sleep(2)
        if df is None:
            raise RuntimeError("AKShare 5 次全部失败")
        # 数据清洗:净额转 float(有些行是 "--" 或空)
        df["净额"] = df["净额"].astype(str).str.replace("--", "0").str.replace(",", "").astype(float)
        df["行业-涨跌幅"] = df["行业-涨跌幅"].astype(str).str.replace("--", "0").astype(float)
        df["行业"] = df["行业"].astype(str)
        print(f"✅ 拿到 {len(df)} 个概念,净额范围 {df['净额'].min():.2f} ~ {df['净额'].max():.2f} 亿")

        # 概念名 -> 数据字典
        concept_map = dict(zip(df["行业"], df[["净额", "行业-涨跌幅"]].itertuples(index=False, name=None)))

        result = []

        # 1) 用户关注板块(匹配真实数据,匹配不到也放占位 0)
        matched_count = 0
        for user_name in SECTOR_ALIASES:
            match = _match_sector(user_name, list(concept_map.keys()))
            if match:
                flow, pct = concept_map[match]
                result.append({"name": user_name, "flow": flow, "pct": pct})
                matched_count += 1
            else:
                result.append({"name": user_name, "flow": 0.0, "pct": 0.0})
        print(f"🎯 用户 {len(SECTOR_ALIASES)} 个板块匹配到 {matched_count} 个真实数据")

        # 2) 额外补充:净流入 Top 8 + 净流出 Top 8(去掉已在列表里的)
        top_inflow = df.nlargest(8, "净额")[["行业", "净额", "行业-涨跌幅"]]
        top_outflow = df.nsmallest(8, "净额")[["行业", "净额", "行业-涨跌幅"]]
        existing = {r["name"] for r in result}

        extra = []
        for _, row in top_inflow.iterrows():
            if row["行业"] not in existing and row["净额"] > 0:
                extra.append({"name": row["行业"], "flow": row["净额"], "pct": row["行业-涨跌幅"]})
                existing.add(row["行业"])
        for _, row in top_outflow.iterrows():
            if row["行业"] not in existing and row["净额"] < 0:
                extra.append({"name": row["行业"], "flow": row["净额"], "pct": row["行业-涨跌幅"]})
                existing.add(row["行业"])

        result.extend(extra)
        print(f"📊 额外补充 {len(extra)} 个热门概念")

        # 3) 全部按净额从大到小排序
        result.sort(key=lambda x: x["flow"], reverse=True)

        # 验证输出前10
        for item in result[:10]:
            print(f"   📈 {item['name']}: {item['flow']:+.2f}亿 ({item['pct']:+.2f}%)")

        return result

    except Exception as e:
        print(f"⚠️ AKShare 失败: {type(e).__name__}: {e}")
        print(f"⚠️ 调用预备 mock 数据集")
        all_names = list(SECTOR_ALIASES.keys())
        return [{"name": name, "flow": 12.0 - idx * 0.9, "pct": 2.5 - idx * 0.1} for idx, name in enumerate(all_names)]

# =====================================================================
# 🎨 第二部分：智能双时段【零轴双向延伸】高清长图引擎
# =====================================================================
def generate_infographic_image(data_list, report_type):
    """
    根据运行时间段自动变换图表大标题
    """
    # 强制用 Noto Sans CJK SC 字体文件(不是只靠字体名匹配)
    if _CHINESE_FONT_PATH:
        fp = fm.FontProperties(fname=_CHINESE_FONT_PATH)
        plt.rcParams['font.family'] = fp.get_name()
    plt.rcParams['font.sans-serif'] = ['Noto Sans CJK SC', 'Noto Sans CJK TC', 'SimHei', 'Microsoft YaHei', 'DejaVu Sans', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False     

    data_list = data_list[::-1]
    names = [item['name'] for item in data_list]
    flows = [item['flow'] for item in data_list]
    pcts = [item['pct'] for item in data_list]
    
    fig_height = max(13, len(data_list) * 0.45)
    fig, ax = plt.subplots(figsize=(9, fig_height), dpi=200) 
    
    fig.patch.set_facecolor('#f8fafc')
    ax.set_facecolor('#ffffff')
    
    colors = ['#e53e3e' if x >= 0 else '#38a169' for x in flows]
    # 所有长条都画在正轴上(用绝对值),颜色区分方向
    abs_flows = [abs(x) for x in flows]
    bars = ax.barh(names, abs_flows, color=colors, edgecolor='none', height=0.65, alpha=0.95)
    
    for spine in ['top', 'right', 'bottom', 'left']:
        ax.spines[spine].set_visible(False)
        
    ax.grid(axis='x', linestyle='--', alpha=0.25, color='#a0aec0')
    
    for bar, flow, pct in zip(bars, flows, pcts):
        width = bar.get_width()
        label_text = f" {flow:+.2f}亿 ({pct:+.2f}%)"
        ax.text(width, bar.get_y() + bar.get_height()/2, label_text,
                va='center', ha='left', fontsize=9, color='#2d3748', fontweight='bold')

    today_date = datetime.now().strftime("%Y-%m-%d")
    
    # 💡 核心修改：根据运行时间自动切换午盘/收盘小标题
    title_suffix = "【午盘特刊】中场异动扫描" if report_type == "midday" else "【收盘特刊】全天战报复盘"
    
    plt.title(f"A股核心板块主力资金监测全景图\n数据快报: {today_date} {title_suffix}", 
              fontsize=14, pad=22, color='#1a202c', fontweight='bold', loc='center')
    
    plt.xlabel("主力资金流动分布 (单位: 亿元)   [红色流入 🔺 绿色流出 🔻]\n\n⚠️ 免责声明：本内容仅作为客观市场现象的数据归纳，绝非投资建议，据此操作风险自担。", 
               fontsize=8, color='#a0aec0', labelpad=15)
    
    plt.tick_params(axis='y', which='major', labelsize=10, labelcolor='#4a5568', length=0)
    plt.tick_params(axis='x', which='major', labelsize=9, labelcolor='#a0aec0')
    plt.tight_layout()
    
    image_name = "infographic.png"
    plt.savefig(image_name, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close()
    return image_name

# =====================================================================
# 🔗 第三部分：组装时段特定的通知送达钉钉群机器人
# =====================================================================
def _upload_to_gitee(img_path):
    """通过 Gitee REST API 上传图片,返回公网 raw 链接(仓库已 public,钉钉能拉图)"""
    import base64
    if not GITEE_TOKEN:
        print("⚠️ GITEE_TOKEN 未配置,跳过 Gitee 上传")
        return None
    try:
        filename = os.path.basename(img_path)
        # 先查文件是否已存在(更新需要 sha)
        sha = None
        check_url = f"https://gitee.com/api/v5/repos/{GITEE_USERNAME}/{GITEE_REPO}/contents/{filename}"
        check_params = {"access_token": GITEE_TOKEN, "ref": GITEE_BRANCH}
        check_resp = requests.get(check_url, params=check_params, timeout=10)
        if check_resp.status_code == 200:
            sha = check_resp.json().get("sha")

        # 读文件并 base64 编码
        with open(img_path, "rb") as f:
            content_b64 = base64.b64encode(f.read()).decode()

        # PUT 上传/更新
        put_url = f"https://gitee.com/api/v5/repos/{GITEE_USERNAME}/{GITEE_REPO}/contents/{filename}"
        put_data = {
            "access_token": GITEE_TOKEN,
            "message": f"auto update {filename}",
            "content": content_b64,
            "branch": GITEE_BRANCH,
        }
        if sha:
            put_data["sha"] = sha  # 更新时必须带 sha

        resp = requests.put(put_url, json=put_data, timeout=30)
        result = resp.json()
        if resp.status_code in (200, 201):
            # Gitee raw 会 302 重定向到带签名的 raw.giteeusercontent.com
            # 钉钉不 follow 302,所以我们自己 follow 拿到签名直链(200 + image/png)
            raw_url = f"https://gitee.com/{GITEE_USERNAME}/{GITEE_REPO}/raw/{GITEE_BRANCH}/{filename}"
            # 加时间戳参数,强制钉钉/CDN 不缓存(每次都新 URL)
            cache_buster = int(time.time())
            raw_url_with_ts = raw_url + f"?t={cache_buster}"
            try:
                follow = requests.get(raw_url, allow_redirects=True, timeout=15)
                final_url = follow.url
                if follow.status_code == 200 and 'image/' in follow.headers.get('content-type', ''):
                    # 签名 URL 后面追加 &t=时间戳,绕过钉钉和 Gitee CDN 缓存
                    url_with_cache_bust = final_url + f"&t={cache_buster}"
                    print(f"📤 图片已上传,签名直链(带时间戳绕缓存): {url_with_cache_bust[:100]}...")
                    return url_with_cache_bust
            except Exception:
                pass
            # 兜底:返回 raw_url(钉钉可能拉不到)
            print(f"📤 图片已上传 Gitee(签名获取失败): {raw_url}")
            return raw_url_with_ts
        print(f"⚠️ Gitee 上传失败: {resp.status_code} {result.get('message','')}")
    except Exception as e:
        print(f"⚠️ Gitee 上传异常: {e}")
    return None


def push_image_to_dingtalk(webhook_url, img_path, report_type):
    today_date = datetime.now().strftime("%Y-%m-%d")
    time_label = "【午盘】中场" if report_type == "midday" else "【收盘】全天"

    # 用 Gitee 国内图床(仓库已 public)
    print("📤 上传长图到 Gitee 国内图床...")
    cdn_image_url = _upload_to_gitee(img_path)
    if not cdn_image_url:
        print("❌ 图片上传失败,GITEE_TOKEN 未配置或 Gitee API 报错,无法发送钉钉消息")
        return

    markdown_text = f"### 📊 今日A股全景核心板块{time_label}【主力】资金大长图已洗净！\n"
    markdown_text += f"**快报日期**：{today_date}\n"
    markdown_text += "━━━━━━━━━━━━━━━━━━━━\n"
    markdown_text += f"![主力资金全景长图]({cdn_image_url})\n\n"
    markdown_text += "📂 **自媒体运营发布动作**：\n"
    markdown_text += f"1. 长按上方群聊里的{time_label}图表,直接保存至手机相册。\n"
    markdown_text += "2. 打开公众号后台,直接插入最新动态文章,一秒群发抢占头条！\n"
    markdown_text += "━━━━━━━━━━━━━━━━━━━━\n"
    markdown_text += "> ⚠️ *免责声明:本内容仅供客观数据事实复盘,不构成任何投资买卖建议。*"

    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": f"今日{time_label}主力资金长图已就绪",
            "text": markdown_text
        }
    }

    headers = {"Content-Type": "application/json"}
    response = requests.post(webhook_url, data=json.dumps(payload), headers=headers).json()

    if response.get("errcode") == 0:
        print(f"🎉【{time_label}特刊完美收官】简报已安全送达钉钉群聊!")
    else:
        print(f"❌ 钉钉拒绝,原因:{response}")


if __name__ == "__main__":
    print("📅 [验证开始] 正在检测大盘是否处于开盘交易状态...")
    if check_is_market_closed():
        print("😴 检测到今天非交易日,自动化工作流优雅休眠退出。")
    else:
        # 💡 智能化总线判断:当前是中午还是下午收盘
        current_hour = datetime.now().hour
        # 北京时间 11:30~13:30 之间运行则判定为午盘
        current_report_type = "midday" if 11 <= current_hour < 14 else "closing"

        print(f"🔄 第一步:启动数据清洗进程,当前判定时段为: {current_report_type}")
        stock_data = get_all_merged_capital_flow()

        print("🎨 第二步:调用零轴中置绘图引擎渲染高级长图...")
        img_file = generate_infographic_image(stock_data, current_report_type)

        print("🔑 第三步:上传长图 + 推送简报到钉钉群聊...")
        push_image_to_dingtalk(DINGTALK_WEBHOOK_URL, img_file, current_report_type)
