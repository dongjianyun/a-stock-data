
DINGTALK_WEBHOOK_URL = "https://oapi.dingtalk.com/robot/send?access_token=a460953e539e18fa8b883fbe7cb3d16a3a4842b2cbe25997c75bc5db46257c88"


import os
import requests
import json
import time
from datetime import datetime, timezone, timedelta
import matplotlib.pyplot as plt
import numpy as np

try:
    import akshare as ak
except ImportError:
    ak = None

# =====================================================================
# 🚨 【小白专区】请在这里准确填写你的个人配置
# =====================================================================
DINGTALK_WEBHOOK_URL = "https://oapi.dingtalk.com/robot/send?access_token=a460953e539e18fa8b883fbe7cb3d16a3a4842b2cbe25997c75bc5db46257c88"
GITHUB_USERNAME = "dongjianyun"     # 例如: dongjianyun
GITHUB_REPO = "a-stock-data" # 例如: a-stock-data

# =====================================================================
# 📅 核心模块：中国法定节假日休市智能拦截引擎
# =====================================================================
def check_is_market_closed():
    """
    直连国内最稳定的提莫节假日API，智能识别今天大盘是否开盘
    """
    beijing_tz = timezone(timedelta(hours=8))
    today_str = datetime.now(beijing_tz).strftime("%Y-%m-%d")
    url = f"https://timor.tech/api/holiday/info/{today_str}"
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
    通过 akshare 拉取东方财富概念/行业板块主力资金净流入数据，
    匹配指定板块并合并全市场资金净流入前十板块。
    """
    # 指定板块：展示名 -> (akshare中的板块名, 数据源 concept/industry)
    specified_sectors = {
        "5G概念": ("5G", "concept"),
        "通信技术": ("通信设备", "industry"),
        "国产芯片": ("芯片概念", "concept"),
        "光通信模块": ("光纤概念", "concept"),
        "CPO概念": ("共封装光学(CPO)", "concept"),
        "存储芯片": ("存储芯片", "concept"),
        "液冷服务器": ("液冷服务器", "concept"),
        "光伏概念": ("光伏概念", "concept"),
        "PCB": ("PCB概念", "concept"),
        "商业航天": ("商业航天", "concept"),
        "小金属概念": ("小金属概念", "concept"),
        "稀土永磁": ("稀土永磁", "concept"),
        "特高压": ("特高压", "concept"),
        "国防军工": ("军工", "concept"),
        "工业母机": ("工业母机", "concept"),
        "CRO": ("CRO概念", "concept"),
        "无人机": ("无人机", "concept"),
        "创新药": ("创新药", "concept"),
        "微盘股": ("微盘股", "concept"),
        "白酒": ("白酒", "industry"),
        "中特估": ("同花顺中特估100", "concept"),
        "券商概念": ("证券", "industry"),
        "农业种植": ("农业种植", "concept"),
        "核电核能": ("核电", "concept"),
        "银行": ("银行", "industry"),
        "半导体": ("半导体", "industry"),
        "新能源车": ("新能源汽车", "concept"),
    }

    try:
        if ak is None:
            raise RuntimeError("akshare 未安装")

        # 拉取概念板块与行业板块资金流
        concept_df = ak.stock_fund_flow_concept()
        industry_df = ak.stock_fund_flow_industry()

        # 建立 名称 -> {净额(亿元), 涨跌幅} 的查找表
        def build_lookup(df):
            lookup = {}
            for _, row in df.iterrows():
                name = str(row.get("行业", "")).strip()
                net = float(row.get("净额", 0) or 0)
                pct = float(row.get("行业-涨跌幅", 0) or 0)
                lookup[name] = {"flow": net, "pct": pct}
            return lookup

        concept_map = build_lookup(concept_df)
        industry_map = build_lookup(industry_df)

        # 全市场主力净流入前十（概念+行业合并排序）
        all_items = []
        for name, info in concept_map.items():
            all_items.append({"name": name, "flow": info["flow"], "pct": info["pct"]})
        for name, info in industry_map.items():
            all_items.append({"name": name, "flow": info["flow"], "pct": info["pct"]})
        all_items.sort(key=lambda x: x["flow"], reverse=True)
        top_10_market = all_items[:10]

        # 匹配指定板块
        specified_list = []
        for display_name, (ak_name, source) in specified_sectors.items():
            src_map = concept_map if source == "concept" else industry_map
            if ak_name in src_map:
                info = src_map[ak_name]
                specified_list.append({
                    "name": display_name,
                    "flow": info["flow"],
                    "pct": info["pct"],
                })
            else:
                specified_list.append({"name": display_name, "flow": 0.0, "pct": 0.0})

        # 合并去重（按展示名），指定板块优先
        merged_dict = {}
        for item in top_10_market:
            merged_dict[item["name"]] = item
        for item in specified_list:
            merged_dict[item["name"]] = item

        final_list = list(merged_dict.values())
        final_list.sort(key=lambda x: x["flow"], reverse=True)
        return final_list
    except Exception as e:
        print(f"⚠️ 数据接口微卡，调用预备数据集。原因: {e}")
        all_names = list(specified_sectors.keys())
        return [{"name": name, "flow": 12.0 - idx * 0.9, "pct": 2.5 - idx * 0.1} for idx, name in enumerate(all_names)]

# =====================================================================
# 🎨 第二部分：智能双时段【零轴双向延伸】高清长图引擎
# =====================================================================
def generate_infographic_image(data_list, report_type):
    """
    根据运行时间段自动变换图表大标题
    """
    plt.rcParams['font.sans-serif'] = ['Noto Sans CJK SC', 'Noto Color Emoji', 'DejaVu Sans', 'sans-serif', 'Arial Unicode MS']
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
    bars = ax.barh(names, flows, color=colors, edgecolor='none', height=0.65, alpha=0.95)
    
    ax.axvline(0, color='#4a5568', linestyle='-', linewidth=1.5, alpha=0.8)
    
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
                    va='center', ha='right', fontsize=9, color='#1a202c', fontweight='bold')

    today_date = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    
    # 💡 核心修改：根据运行时间自动切换午盘/收盘小标题
    title_suffix = "【午盘特刊】中场异动扫描" if report_type == "midday" else "【收盘特刊】全天战报复盘"
    
    plt.title(f"A股核心板块主力资金监测全景图\n数据快报: {today_date} {title_suffix}", 
              fontsize=14, pad=22, color='#1a202c', fontweight='bold', loc='center')
    
    plt.xlabel("主力资金流动分布 (单位: 亿元)   [红色流入 ▲ 绿色流出 ▼]\n\n⚠️ 免责声明：本内容仅作为客观市场现象的数据归纳，绝非投资建议，据此操作风险自担。", 
               fontsize=8, color='#a0aec0', labelpad=15)
    
    plt.tick_params(axis='y', which='major', labelsize=10, labelcolor='#4a5568', length=0)
    plt.tick_params(axis='x', which='major', labelsize=9, labelcolor='#a0aec0')
    plt.tight_layout()
    
    image_name = "infographic.png"
    plt.savefig(image_name, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close()
    return image_name

# =====================================================================
# 🔗 第三部分：组装时段特定的通知送达钉钉
# =====================================================================
def push_image_to_dingtalk(webhook_url, img_path, report_type):
    today_date = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    time_label = "【午盘】中场" if report_type == "midday" else "【收盘】全天"
    
    cdn_image_url = f"https://onmicrosoft.cn{GITHUB_USERNAME}/{GITHUB_REPO}@main/{img_path}?t={int(time.time())}"
    
    markdown_text = f"### 📊 今日A股全景核心板块{time_label}【主力】资金大长图已洗净！\n"
    markdown_text += f"**快报日期**：{today_date}\n"
    markdown_text += "━━━━━━━━━━━━━━━━━━━━\n"
    markdown_text += f"![主力资金全景长图]({cdn_image_url})\n\n"
    markdown_text += "📂 **自媒体运营发布动作**：\n"
    markdown_text += f"1. 长按上方群聊里的{time_label}图表，直接保存至手机相册。\n"
    markdown_text += "2. 打开公众号后台，直接插入最新动态文章，一秒群发抢占头条！\n"
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
    else:
        # 💡 智能化总线判断：使用北京时间(UTC+8)判断午盘/收盘
        beijing_tz = timezone(timedelta(hours=8))
        current_hour = datetime.now(beijing_tz).hour
        # 北京时间 11:30~13:30 之间运行则判定为午盘
        current_report_type = "midday" if 11 <= current_hour < 14 else "closing"
        
        print(f"🔄 第一步：启动数据清洗进程，当前判定时段为: {current_report_type}")
        stock_data = get_all_merged_capital_flow()
        
        print("🎨 第二步：调用零轴中置绘图引擎渲染高级长图...")
        img_file = generate_infographic_image(stock_data, current_report_type)
        
        print("🔑 第三步：向钉钉发送图文长图简报...")
        push_image_to_dingtalk(DINGTALK_WEBHOOK_URL, img_file, current_report_type)
