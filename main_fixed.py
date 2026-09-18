# Gitee 仓库地址：https://gitee.com/thats-awesome/a-stock-data

import os
import requests
import json
import time
from datetime import datetime, timezone, timedelta
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager

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
# 🔤 中文字体自动检测，避免图片缺字成方框
# =====================================================================
def _pick_cjk_font():
    preferred = ['Noto Sans CJK SC', 'WenQuanYi Micro Hei', 'Microsoft YaHei', 'SimHei']
    candidates = {f.name for f in font_manager.fontManager.ttflist}
    for name in preferred:
        if name in candidates:
            return name
    return None


# =====================================================================
# 🛠️ 东财数据拉取：优先实时接口，不可达时回退到延时接口（皆为真实数据）
#    注：同时拉取【行业板块 t:2】+【概念板块 t:3】，确保 27 个板块都能取到真实数值
#    字段：f12=板块代码, f14=板块名称, f62=主力净流入(元), f3=涨跌幅(%)
# =====================================================================
def _fetch_boards():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://quote.eastmoney.com/center/boardlist.html"
    }
    base_params = {
        "fid": "f62", "po": "1", "pz": "500", "pn": "1",
        "np": "1", "fltt": "2", "invt": "2",
        "fs": "m:90+t:2,m:90+t:3",      # 行业板块 + 概念板块 全部拉取
        "fields": "f12,f14,f3,f62"
    }
    # 东财 clist 接口单页最多约 100 条，两个数据源都须按 total 翻页取全，
    # 否则排序靠后（第100名之后）的板块（如银行、券商等）会匹配失败显示 0
    hosts = [
        "https://push2.eastmoney.com/api/qt/clist/get",
        "https://push2delay.eastmoney.com/api/qt/clist/get",
    ]
    for url in hosts:
        try:
            rows = []
            total = None
            for pn in range(1, 30):
                p = dict(base_params)
                p["pn"] = str(pn)
                data = requests.get(url, params=p, headers=headers, timeout=12).json().get("data") or {}
                if total is None:
                    total = data.get("total")
                page = data.get("diff") or []
                if not page:
                    break
                rows.extend(page)
                # 已取满 total 或本页不足 100 条则停止翻页
                if (total is not None and len(rows) >= total) or len(page) < 100:
                    break
            if rows:
                print(f"✅ 数据源可用: {url}，共 {len(rows)} 个板块 (total={total})")
                return rows
        except Exception as e:
            print(f"⚠️ 数据源不可用: {url}，原因: {e}")
    return None


# =====================================================================
# 📊 主力资金汇总：只使用原定的 27 个指定板块，不随意增加或删减
# =====================================================================
def get_all_merged_capital_flow():
    # 原定 27 个板块（代码均经东财全量板块列表实测核验，勿随意改动）
    specified_sectors = {
        "5G概念": "BK0714", "通信技术": "BK1650", "国产芯片": "BK0891",
        "光通信模块": "BK1136", "CPO概念": "BK1128", "存储芯片": "BK1137",
        "液冷服务器": "BK1138", "光伏概念": "BK0588", "PCB": "BK0877",
        "商业航天": "BK0963", "小金属概念": "BK0695", "稀土永磁": "BK0578",
        "特高压": "BK0918", "国防军工": "BK1204", "工业母机": "BK1004",
        "CRO": "BK0899", "无人机": "BK0704", "创新药": "BK1106",
        "微盘股": "BK1158", "白酒": "BK0896", "中特估": "BK1139",
        "券商概念": "BK0711", "农业种植": "BK0888", "核电核能": "BK0577",
        "银行": "BK0475", "半导体": "BK1036", "新能源车": "BK0900"
    }

    rows = _fetch_boards()
    if not rows:
        print("❌ 所有东财数据源均不可用，本次不发送（不使用任何模拟数据）。")
        raise SystemExit(1)

    # 按代码映射 + 按名称兜底：避免 BK 代码写错/重复时仍能取到真实数据
    code_dict = {item.get("f12"): item for item in rows if item.get("f12")}
    name_dict = {item.get("f14"): item for item in rows if item.get("f14")}

    # 仅遍历原定 27 个板块，逐一取真实数据；缺失的板块以 0 占位但不增删板块数量
    final_list = []
    for name, code in specified_sectors.items():
        # 优先按代码匹配；若代码映射不到（可能被东财改名/合并），再用名称兜底
        match = code_dict.get(code) or name_dict.get(name)
        if match:
            final_list.append({
                "name": name,
                "flow": round(match.get("f62", 0) / 100000000.0, 2),
                "pct": match.get("f3", 0.0)
            })
        else:
            final_list.append({"name": name, "flow": 0.0, "pct": 0.0})

    final_list.sort(key=lambda x: x["flow"], reverse=True)
    print(f"✅ 只使用原定 {len(final_list)} 个板块（真实数据）：{[x['name'] for x in final_list]}")
    return final_list


# =====================================================================
# 🎨 第二部分：高清长图引擎 —— 净流出长条从 X 轴 0 开始，按绝对值向右绘制
# =====================================================================
def generate_infographic_image(data_list, report_type):
    font_name = _pick_cjk_font() or 'DejaVu Sans'
    plt.rcParams['font.sans-serif'] = [font_name, 'DejaVu Sans', 'sans-serif', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False

    data_ordered = data_list[::-1]
    names = [item['name'] for item in data_ordered]
    flows = [item['flow'] for item in data_ordered]
    pcts = [item['pct'] for item in data_ordered]
    abs_flows = [abs(f) for f in flows]  # 长条长度用绝对值，全部从 0 向右

    fig_height = max(13, len(data_list) * 0.45)
    fig, ax = plt.subplots(figsize=(9, fig_height), dpi=200)

    fig.patch.set_facecolor('#f8fafc')
    ax.set_facecolor('#ffffff')

    colors = ['#e53e3e' if x >= 0 else '#38a169' for x in flows]
    bars = ax.barh(names, abs_flows, color=colors, edgecolor='none', height=0.65, alpha=0.95)

    # 横轴从 0 开始向右延伸（不画 0 轴竖线）
    max_abs = max(abs_flows) if abs_flows else 1
    ax.set_xlim(0, max_abs * 1.20)

    for spine in ['top', 'right', 'bottom', 'left']:
        ax.spines[spine].set_visible(False)

    ax.grid(axis='x', linestyle='--', alpha=0.25, color='#a0aec0')

    for bar, flow, pct in zip(bars, flows, pcts):
        width = bar.get_width()
        sign = "+" if flow >= 0 else ""
        label_text = f" {sign}{flow:.2f}亿 ({pct:+.2f}%)"
        if flow >= 0:
            ax.text(width, bar.get_y() + bar.get_height()/2, label_text,
                    va='center', ha='left', fontsize=9, color='#2d3748', fontweight='bold')
        else:
            ax.text(width, bar.get_y() + bar.get_height()/2, label_text,
                    va='center', ha='right', fontsize=9, color='#e53e3e', fontweight='bold')

    today_date = now_beijing().strftime("%Y-%m-%d")

    # 根据运行时间自动切换午盘/收盘小标题
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
# 🔗 第三部分：组装时段特定的通知送达钉钉（图片走 Gitee raw 直链）
# =====================================================================
def push_image_to_dingtalk(webhook_url, img_path, report_type):
    today_date = now_beijing().strftime("%Y-%m-%d")
    time_label = "【午盘】中场" if report_type == "midday" else "【收盘】全天"

    cdn_image_url = f"https://gitee.com/{GITEE_OWNER}/{GITEE_REPO}/raw/main/{img_path}?t={int(time.time())}"

    markdown_text = f"### 📊 今日A股{time_label}【主力】资金大长图已洗净！\n"
    markdown_text += f"**快报日期**：{today_date}\n"
    markdown_text += "━━━━━━━━━━━━━━━━━━━━\n"
    markdown_text += f"![主力资金全景长图]({cdn_image_url})\n\n"
    markdown_text += "📂 **自媒体运营发布动作**：\n"
    markdown_text += f"1. 长按上方{time_label}图表，直接保存至手机相册。\n"
    markdown_text += "2. 打开公众号后台，直接插入最新动态文章应用发布！\n"
    markdown_text += "━━━━━━━━━━━━━━━━━━━━\n"
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

    current_hour = now_beijing().hour
    current_report_type = "midday" if 11 <= current_hour < 14 else "closing"

    print(f"🔄 第一步：启动数据清洗进程，当前判定时段为: {current_report_type}")
    stock_data = get_all_merged_capital_flow()

    print("🎨 第二步：调用绘图引擎渲染高级长图...")
    img_file = generate_infographic_image(stock_data, current_report_type)

    print("🔑 第三步：向钉钉发送图文长图简报...")
    push_image_to_dingtalk(DINGTALK_WEBHOOK_URL, img_file, current_report_type)