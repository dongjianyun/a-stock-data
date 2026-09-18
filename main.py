# Gitee 仓库地址：https://gitee.com/thats-awesome/a-stock-data

import os
import requests
import json
import time
from datetime import datetime, timezone, timedelta
import matplotlib.pyplot as plt
import numpy as np

# =====================================================================
# 🚨 【配置区】请在这里准确填写你的个人配置
# =====================================================================
DINGTALK_WEBHOOK_URL = "https://oapi.dingtalk.com/robot/send?access_token=a460953e539e18fa8b883fbe7cb3d16a3a4842b2cbe25997c75bc5db46257c88"
GITEE_OWNER = "thats-awesome"     # Gitee 用户名
GITEE_REPO = "a-stock-data"       # Gitee 仓库名

# 北京时间 UTC+8
BEIJING_TZ = timezone(timedelta(hours=8))


def now_beijing():
    return datetime.now(BEIJING_TZ)


# =====================================================================
# 📅 核心模块：中国法定节假日休市智能拦截引擎（真实数据）
# =====================================================================
def check_is_market_closed():
    today_str = now_beijing().strftime("%Y-%m-%d")
    url = f"https://timor.tech/api/holiday/info/{today_str}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        res = requests.get(url, headers=headers, timeout=10).json()
        if res.get("code") == 0 and res.get("type"):
            # type: 0工作日/补班 1周末 2节日 3调休
            if res.get("type") in (1, 2):
                print("🎉 动态监测：今天为周末/法定节假日，A股休市，不打扰主理人！😴")
                return True
        print("📈 动态监测：今日为正常交易日，开始追踪筹码异动！")
        return False
    except Exception as e:
        print(f"⚠️ 节假日接口暂时不可用，默认跳过拦截继续跑数据。原因: {e}")
        return False


# =====================================================================
# 🛠️ 东财数据拉取：优先实时接口，不可达时回退到延时接口（皆为真实数据）
# =====================================================================
def _fetch_boards():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://quote.eastmoney.com/center/boardlist.html"
    }
    base_params = {
        "fid": "f62", "po": "1", "pz": "500", "pn": "1",
        "np": "1", "fltt": "2", "invt": "2",
        "fs": "m:90+t:3",
        "fields": "f12,f14,f3,f62"
    }
    # (host, 是否需要分页) —— push2delay 每页最多 100 条，需翻页
    hosts = [
        ("https://push2.eastmoney.com/api/qt/clist/get", False),
        ("https://push2delay.eastmoney.com/api/qt/clist/get", True),
    ]
    for url, need_paging in hosts:
        try:
            rows = []
            if need_paging:
                for pn in range(1, 8):
                    p = dict(base_params)
                    p["pn"] = str(pn)
                    page = requests.get(url, params=p, headers=headers, timeout=12).json().get("data", {}).get("diff", [])
                    if not page:
                        break
                    rows.extend(page)
                    if len(page) < 100:
                        break
            else:
                p = dict(base_params)
                p["pn"] = "1"
                rows = requests.get(url, params=p, headers=headers, timeout=12).json().get("data", {}).get("diff", [])
            if rows:
                print(f"✅ 数据源可用: {url}，共 {len(rows)} 个板块")
                return rows
        except Exception as e:
            print(f"⚠️ 数据源不可用: {url}，原因: {e}")
    return None


def get_all_merged_capital_flow():
    specified_sectors = {
        "5G概念": "BK0714", "通信技术": "BK0630", "国产芯片": "BK0891",
        "光通信模块": "BK1136", "CPO概念": "BK1128", "存储芯片": "BK1118",
        "液冷服务器": "BK1136", "光伏概念": "BK0491", "PCB": "BK0971",
        "商业航天": "BK1173", "小金属概念": "BK0736", "稀土永磁": "BK0591",
        "特高压": "BK0565", "国防军工": "BK0472", "工业母机": "BK1016",
        "CRO": "BK0899", "无人机": "BK0665", "创新药": "BK1106",
        "微盘股": "BK1158", "白酒": "BK0896", "中特估": "BK1137",
        "券商概念": "BK0711", "农业种植": "BK0888", "核电核能": "BK0548",
        "银行": "BK0475", "半导体": "BK1036", "新能源车": "BK0900"
    }

    raw_list = _fetch_boards()
    if raw_list is None:
        # ✅ 只用真实数据：两个数据源都失败则直接退出，绝不发送任何臆造数据
        print("❌ 东财接口异常，无法获取真实数据，本次不发送任何内容。")
        raise SystemExit(1)

    market_dict = {item["f12"]: item for item in raw_list if item.get("f12")}

    # 全市场板块按主力净流入降序，取前10名做榜单
    ranked = sorted(market_dict.values(), key=lambda x: x.get("f62", 0), reverse=True)
    top_10_market = [{
        "name": item.get("f14", "未知"),
        "flow": item.get("f62", 0) / 100000000.0,
        "pct": item.get("f3", 0.0)
    } for item in ranked[:10]]

    # 指定重点关注的板块
    specified_list = []
    for name, code in specified_sectors.items():
        match_data = market_dict.get(code)
        if match_data is not None:
            specified_list.append({
                "name": name,
                "flow": match_data.get("f62", 0) / 100000000.0,
                "pct": match_data.get("f3", 0.0)
            })
        else:
            specified_list.append({"name": name, "flow": 0.0, "pct": 0.0})

    merged_dict = {}
    for item in top_10_market:
        merged_dict[item["name"]] = item
    for item in specified_list:
        merged_dict[item["name"]] = item

    final_list = list(merged_dict.values())
    final_list.sort(key=lambda x: x["flow"], reverse=True)
    return final_list


# =====================================================================
# 🎨 高清长图引擎（净流出长条用绝对值，从 X 轴 0 点向右延伸）
# =====================================================================
def _pick_cjk_font():
    from matplotlib import font_manager
    preferred = ['Noto Sans CJK SC', 'Noto Sans CJK JP', 'Source Han Sans SC', 'Source Han Sans CN',
                 'WenQuanYi Micro Hei', 'WenQuanYi Zen Hei', 'PingFang SC', 'Microsoft YaHei',
                 'SimHei', 'Alibaba PuHuiTi', 'sans-serif']
    candidates = {f.name for f in font_manager.fontManager.ttflist}
    for name in preferred:
        if name in candidates:
            return name
    return None


def generate_infographic_image(data_list, report_type):
    cjk_font = _pick_cjk_font()
    if cjk_font:
        plt.rcParams['font.sans-serif'] = [cjk_font, 'DejaVu Sans', 'sans-serif']
    else:
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False

    data_list = data_list[::-1]
    names = [item['name'] for item in data_list]
    flows = [item['flow'] for item in data_list]
    pcts = [item['pct'] for item in data_list]

    # ★ 核心：流入流出长条一律用绝对值，统一从 X 轴 0 点向正方向延伸
    abs_flows = [abs(f) for f in flows]

    fig_height = max(13, len(data_list) * 0.45)
    fig, ax = plt.subplots(figsize=(9, fig_height), dpi=200)

    fig.patch.set_facecolor('#f8fafc')
    ax.set_facecolor('#ffffff')

    # 流入红色、流出绿色
    colors = ['#e53e3e' if x >= 0 else '#38a169' for x in flows]
    bars = ax.barh(names, abs_flows, color=colors, edgecolor='none', height=0.65, alpha=0.95)

    for spine in ['top', 'right', 'bottom', 'left']:
        ax.spines[spine].set_visible(False)

    ax.grid(axis='x', linestyle='--', alpha=0.25, color='#a0aec0')

    for bar, flow, pct in zip(bars, flows, pcts):
        width = bar.get_width()
        sign = "+" if flow >= 0 else "-"
        label_text = f" {sign}{abs(flow):.2f}亿 ({pct:+.2f}%)"
        # 标签统一放在长条右侧（X 正方向）
        ax.text(width, bar.get_y() + bar.get_height() / 2, label_text,
                va='center', ha='left', fontsize=9, color='#2d3748', fontweight='bold')

    today_date = now_beijing().strftime("%Y-%m-%d")
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
# 🔗 组装图文通知送达钉钉
# =====================================================================
def push_image_to_dingtalk(webhook_url, img_path, report_type):
    today_date = now_beijing().strftime("%Y-%m-%d")
    time_label = "【午盘】中场" if report_type == "midday" else "【收盘】全天"

    # 使用 Gitee raw 直链加载图片
    cdn_image_url = f"https://gitee.com/{GITEE_OWNER}/{GITEE_REPO}/raw/main/{img_path}?t={int(time.time())}"

    markdown_text = f"### 📊 今日A股全景核心板块{time_label}【主力】资金大长图已洗净！\n"
    markdown_text += f"**快报日期**：{today_date}\n"
    markdown_text += "━━━━━━━━━━━━━━━━━━━━\n"
    markdown_text += f"![主力资金全景长图]({cdn_image_url})\n\n"
    markdown_text += "📂 **自媒体运营发布动作**：\n"
    markdown_text += f"1. 长按上方群聊里的{time_label}图表，直接保存至手机相册。\n"
    markdown_text += "2. 打开公众号后台，直接插入最新动态文章，一秒群发抢占头条！\n"
    markdown_text += "━━━━━━━━━━━━━━━━━━━━\n"
    markdown_text += f"[📥 若图片未加载，点击查看高清原图]({cdn_image_url})\n\n"
    markdown_text += "> ⚠️ *免责声明：本内容仅供客观数据事实复盘，不构成任何投资买卖建议。*"

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
        print(f"🎉【{time_label}特刊完美收官】简报已安全送达钉钉群聊！")
    else:
        print(f"❌ 钉钉拒绝，原因：{response}")


if __name__ == "__main__":
    print("📅 [验证开始] 正在检测大盘是否处于开盘交易状态...")
    if check_is_market_closed():
        print("😴 检测到今天非交易日，自动化工作流优雅休眠退出。")
        raise SystemExit(0)
    else:
        current_hour = now_beijing().hour
        # 北京时间 11:30~13:30 之间运行则判定为午盘
        current_report_type = "midday" if 11 <= current_hour < 14 else "closing"

        print(f"🔄 第一步：启动数据清洗进程，当前判定时段为: {current_report_type}")
        stock_data = get_all_merged_capital_flow()

        print("🎨 第二步：调用零轴中置绘图引擎渲染高级长图...")
        img_file = generate_infographic_image(stock_data, current_report_type)

        print("🔑 第三步：向钉钉发送图文长图简报...")
        push_image_to_dingtalk(DINGTALK_WEBHOOK_URL, img_file, current_report_type)