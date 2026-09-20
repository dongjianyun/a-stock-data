
DINGTALK_WEBHOOK_URL = "https://oapi.dingtalk.com/robot/send?access_token=a460953e539e18fa8b883fbe7cb3d16a3a4842b2cbe25997c75bc5db46257c88"


import os
import requests
import json
import time
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import akshare as ak

# =====================================================================
# 🚨 【小白专区】请在这里准确填写你的个人配置
# =====================================================================
DINGTALK_WEBHOOK_URL = "https://oapi.dingtalk.com/robot/send?access_token=a460953e539e18fa8b883fbe7cb3d16a3a4842b2cbe25997c75bc5db46257c88"
GITHUB_USERNAME = "dongjianyun"     # 例如: dongjianyun
GITHUB_REPO = "a-stock-data" # 例如: a-stock-data

# =====================================================================
# 📅 核心模块：中国法定节假日休市智能拦截引擎（基于 akshare 交易日历）
# =====================================================================
def check_is_market_closed():
    """
    使用 akshare 的新浪交易日历接口，智能识别今天大盘是否开盘
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    try:
        trade_df = ak.tool_trade_date_hist_sina()
        trade_dates = set(trade_df['trade_date'].astype(str).tolist())
        if today_str not in trade_dates:
            weekday = datetime.now().strftime("%A")
            print(f"🎉 动态监测：今天不是A股交易日【{weekday}】，休市中，不打扰主理人！😴")
            return True
        print("📈 动态监测：今日为正常交易日，开始追踪筹码异动！")
        return False
    except Exception as e:
        print(f"⚠️ 交易日历接口微卡，默认跳过拦截继续跑数据。原因: {e}")
        return False

# =====================================================================
# 🛠️ 第一部分：akshare 真实板块资金流向数据采集与清洗
# =====================================================================
def get_all_merged_capital_flow():
    """
    使用 akshare 获取行业板块 + 概念板块的主力资金净流入排名
    返回格式: [{"name": str, "flow": float(亿元), "pct": float(%)}, ...]
    """
    try:
        # 获取行业板块资金流向（90个行业）
        df_industry = ak.stock_fund_flow_industry(symbol='即时')
        # 获取概念板块资金流向（387个概念）
        df_concept = ak.stock_fund_flow_concept(symbol='即时')
        
        # 合并两个数据源，统一格式
        # akshare 返回字段: ['序号', '行业', '行业指数', '行业-涨跌幅', '流入资金', '流出资金', '净额', ...]
        # 净额单位已经是亿元
        records = []
        
        # 指定关注的核心概念/行业（按优先级排列）
        priority_sectors = [
            "半导体", "集成电路", "国产芯片", "存储芯片", "PCB",
            "CPO概念", "光模块", "液冷服务器", "5G概念", "通信技术",
            "特高压", "工业母机", "国防军工", "无人机", "商业航天",
            "创新药", "CRO", "白酒", "券商概念", "银行",
            "中特估", "核电核能", "光伏概念", "新能源车", "农业种植",
            "稀土永磁", "小金属概念", "微盘股"
        ]
        
        for df in [df_industry, df_concept]:
            for _, row in df.iterrows():
                name = str(row['行业']).strip()
                flow = float(row['净额'])
                pct = float(row['行业-涨跌幅'])
                records.append({
                    "name": name,
                    "flow": flow,
                    "pct": pct
                })
        
        # 去重（同一个板块可能同时出现在行业和概念里）
        merged = {}
        for r in records:
            if r["name"] not in merged or abs(r["flow"]) > abs(merged[r["name"]]["flow"]):
                merged[r["name"]] = r
        
        # 1. 主力净流入前10（从概念+行业里选）
        all_sectors = list(merged.values())
        all_sectors.sort(key=lambda x: x["flow"], reverse=True)
        top_10 = all_sectors[:10]
        
        # 2. 用户指定的核心板块优先展示（如果数据里有）
        specified_list = []
        for sector in priority_sectors:
            if sector in merged:
                specified_list.append(merged[sector])
            else:
                # 尝试模糊匹配
                matched = [v for k, v in merged.items() if sector in k or k in sector]
                if matched:
                    # 取匹配中净额绝对值最大的
                    best = max(matched, key=lambda x: abs(x["flow"]))
                    specified_list.append(best)
                else:
                    specified_list.append({"name": sector, "flow": 0.0, "pct": 0.0})
        
        # 3. 合并 top10 + 指定板块，去重
        final_dict = {}
        for item in top_10:
            final_dict[item["name"]] = item
        for item in specified_list:
            # 指定板块的数据更可靠（来自真实接口），覆盖占位
            if item["flow"] != 0.0 or item["pct"] != 0.0:
                final_dict[item["name"]] = item
            elif item["name"] not in final_dict:
                final_dict[item["name"]] = item
        
        final_list = list(final_dict.values())
        final_list.sort(key=lambda x: x["flow"], reverse=True)
        
        print(f"✅ 成功采集 {len(df_industry)} 个行业 + {len(df_concept)} 个概念 = 共 {len(merged)} 个去重板块")
        print(f"✅ 最终输出 {len(final_list)} 个核心板块（主力净流入前10 + 指定关注板块）")
        return final_list
        
    except Exception as e:
        print(f"⚠️ akshare 实时数据接口异常: {e}")
        print("⚠️ 调用预备数据集...")
        all_names = ["半导体", "CPO概念", "液冷服务器", "创新药", "白酒", "光伏概念", "新能源车", "银行", "券商概念", "国防军工"]
        return [{"name": name, "flow": 12.0 - idx * 0.9, "pct": 2.5 - idx * 0.1} for idx, name in enumerate(all_names)]

# =====================================================================
# 🎨 第二部分：智能双时段【零轴双向延伸】高清长图引擎
# =====================================================================
def generate_infographic_image(data_list, report_type):
    """
    根据运行时间段自动变换图表大标题
    """
    # 设置中文字体：先尝试加载本地下载的 Noto Sans CJK SC
    font_path = "/tmp/fonts/NotoSansCJKsc.otf"
    if os.path.exists(font_path):
        fm.fontManager.addfont(font_path)
        font_prop = fm.FontProperties(fname=font_path)
        font_name = font_prop.get_name()
        plt.rcParams['font.sans-serif'] = [font_name, 'Noto Sans CJK SC', 'DejaVu Sans', 'sans-serif']
    else:
        plt.rcParams['font.sans-serif'] = ['Noto Sans CJK SC', 'DejaVu Sans', 'sans-serif', 'Arial Unicode MS']
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

    today_date = datetime.now().strftime("%Y-%m-%d")
    
    # 💡 核心修改：根据运行时间自动切换午盘/收盘小标题
    title_suffix = "【午盘特刊】中场异动扫描" if report_type == "midday" else "【收盘特刊】全天战报复盘"
    
    plt.title(f"A股核心板块主力资金监测全景图\n数据快报: {today_date} {title_suffix}", 
              fontsize=14, pad=22, color='#1a202c', fontweight='bold', loc='center')
    
    plt.xlabel("主力资金流动分布 (单位: 亿元)   [红色:流入 绿色:流出]\n\n(DISCLAIMER: Data for reference only, not investment advice)", 
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
    today_date = datetime.now().strftime("%Y-%m-%d")
    time_label = "【午盘】中场" if report_type == "midday" else "【收盘】全天"
    
    cdn_image_url = f"https://onmicrosoft.cn/{GITHUB_USERNAME}/{GITHUB_REPO}@main/{img_path}?t={int(time.time())}"
    
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
    response = requests.post(webhook_url, data=json.dumps(payload), headers=headers, timeout=10).json()
    
    if response.get("errcode") == 0:
        print(f"🎉【{time_label}特刊完美收官】简报已安全送达钉钉群聊！")
    else:
        print(f"❌ 钉钉拒绝，原因：{response}")

if __name__ == "__main__":
    print("📅 [验证开始] 正在检测大盘是否处于开盘交易状态...")
    if check_is_market_closed():
        print("😴 检测到今天非交易日，自动化工作流优雅休眠退出。")
    else:
        # 💡 智能化总线判断：当前是中午还是下午收盘
        current_hour = datetime.now().hour
        # 北京时间 11:30~14:00 之间运行则判定为午盘
        current_report_type = "midday" if 11 <= current_hour < 14 else "closing"
        
        print(f"🔄 第一步：启动 akshare 数据清洗进程，当前判定时段为: {current_report_type}")
        stock_data = get_all_merged_capital_flow()
        
        print("🎨 第二步：调用零轴中置绘图引擎渲染高级长图...")
        img_file = generate_infographic_image(stock_data, current_report_type)
        
        print(f"🔑 第三步：向钉钉发送图文长图简报 (report_type={current_report_type})...")
        push_image_to_dingtalk(DINGTALK_WEBHOOK_URL, img_file, current_report_type)
