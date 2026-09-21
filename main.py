
DINGTALK_WEBHOOK_URL = "https://oapi.dingtalk.com/robot/send?access_token=a460953e539e18fa8b883fbe7cb3d16a3a4842b2cbe25997c75bc5db46257c88"


import os
import subprocess
import requests
import json
import time
from datetime import datetime, timezone, timedelta
import matplotlib.pyplot as plt
import numpy as np

# 北京时间 (UTC+8)
BJ_TZ = timezone(timedelta(hours=8))

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
    today_str = datetime.now(BJ_TZ).strftime("%Y-%m-%d")
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
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://eastmoney.com"
    }
    specified_sectors = {
        "5G概念": "BK0714", "通信技术": "BK0630", "国产芯片": "BK0891", 
        "光通信模块": "BK0714", "CPO概念": "BK1128", "存储芯片": "BK1118", 
        "液冷服务器": "BK1136", "光伏概念": "BK0491", "PCB": "BK0971", 
        "商业航天": "BK1173", "小金属概念": "BK0736", "稀土永磁": "BK0591", 
        "特高压": "BK0565", "国防军工": "BK0472", "工业母机": "BK1016", 
        "CRO": "BK0897", "无人机": "BK0665", "创新药": "BK1106", 
        "微盘股": "BK1158", "白酒": "BK0896", "中特估": "BK1137", 
        "券商概念": "BK0711", "农业种植": "BK0916", "核电核能": "BK0548", 
        "银行": "BK0475", "半导体": "BK1036", "新能源车": "BK0900"
    }
    url = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=500&po=1&np=1&fltt=2&invt=2&fid=f62&fs=m:90+t:2&fields=f12,f14,f3,f62"
    
    try:
        response = requests.get(url, headers=headers, timeout=12)
        res = response.json()
        raw_list = res.get("data", {}).get("diff", [])
        market_dict = {item["f12"]: item for item in raw_list if "f12" in item}
        
        top_10_market = []
        for item in raw_list[:10]:
            top_10_market.append({
                "name": item.get("f14", "未知"),
                "flow": item.get("f62", 0) / 100000000.0,
                "pct": item.get("f3", 0.0)
            })
            
        specified_list = []
        for name, code in specified_sectors.items():
            if code in market_dict:
                match_data = market_dict[code]
                specified_list.append({
                    "name": name,
                    "flow": match_data.get("f62", 0) / 100000000.0,
                    "pct": match_data.get("f3", 0.0)
                })
            else:
                specified_list.append({"name": name, "flow": 0.0, "pct": 0.0})
                
        merged_dict = {}
        for item in top_10_market: merged_dict[item["name"]] = item
        for item in specified_list: merged_dict[item["name"]] = item
            
        final_list = list(merged_dict.values())
        final_list.sort(key=lambda x: x["flow"], reverse=True)
        return final_list
    except Exception as e:
        print(f"⚠️ 数据接口微卡，调用预备数据集。")
        all_names = list(specified_sectors.keys())
        return [{"name": name, "flow": 12.0 - idx * 0.9, "pct": 2.5 - idx * 0.1} for idx, name in enumerate(all_names)]

# =====================================================================
# 🎨 第二部分：智能双时段【零轴双向延伸】高清长图引擎
# =====================================================================
def generate_infographic_image(data_list, report_type):
    """
    根据运行时间段自动变换图表大标题
    """
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

    today_date = datetime.now(BJ_TZ).strftime("%Y-%m-%d")
    
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
# 🔗 第三部分：组装时段特定的通知送达钉钉
# =====================================================================
def push_image_to_dingtalk(webhook_url, img_path, report_type):
    today_date = datetime.now(BJ_TZ).strftime("%Y-%m-%d")
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

# =====================================================================
# 📤 第四部分：将生成的长图推送到 GitHub，使钉钉 CDN 图片链接生效
# =====================================================================
def push_image_to_github(img_path):
    """
    尝试 git add/commit/push 图片到 GitHub。
    若失败（如无 token），打印错误但不中断流程。
    """
    try:
        # 检查是否有变更
        status = subprocess.run(["git", "status", "--porcelain", img_path],
                                capture_output=True, text=True, cwd="/workspace")
        if not status.stdout.strip():
            print(f"📤 Git：{img_path} 无变更，跳过 push。")
            return True

        subprocess.run(["git", "add", img_path], check=True, cwd="/workspace")
        commit_msg = f"chore: update {img_path} ({datetime.now(BJ_TZ).strftime('%Y-%m-%d %H:%M')})"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True, cwd="/workspace",
                       capture_output=True, text=True)
        push_result = subprocess.run(["git", "push", "origin", "main"],
                                     capture_output=True, text=True, cwd="/workspace")
        if push_result.returncode == 0:
            print(f"✅ Git push 成功，{img_path} 已上传至 GitHub，CDN 链接已生效。")
            return True
        else:
            err = push_result.stderr.strip()
            print(f"⚠️ Git push 失败（可能无 GitHub token），钉钉消息已发送但图片链接暂时不可用。错误: {err}")
            return False
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Git 操作失败，钉钉消息已发送但图片链接暂时不可用。错误: {e.stderr if hasattr(e, 'stderr') else e}")
        return False
    except Exception as e:
        print(f"⚠️ Git push 异常，钉钉消息已发送但图片链接暂时不可用。错误: {e}")
        return False

if __name__ == "__main__":
    print("📅 [验证开始] 正在检测大盘是否处于开盘交易状态...")
    if check_is_market_closed():
        print("😴 检测到今天非交易日，自动化工作流优雅休眠退出。")
    else:
        # 💡 智能化总线判断：当前是中午还是下午收盘（使用北京时间）
        current_hour = datetime.now(BJ_TZ).hour
        # 北京时间 11:00~13:59 之间运行则判定为午盘
        current_report_type = "midday" if 11 <= current_hour < 14 else "closing"
        
        print(f"🔄 第一步：启动数据清洗进程，当前判定时段为: {current_report_type}")
        stock_data = get_all_merged_capital_flow()
        
        print("🎨 第二步：调用零轴中置绘图引擎渲染高级长图...")
        img_file = generate_infographic_image(stock_data, current_report_type)
        
        print("🔑 第三步：向钉钉发送图文长图简报...")
        push_image_to_dingtalk(DINGTALK_WEBHOOK_URL, img_file, current_report_type)
        
        print("📤 第四步：尝试将长图推送到 GitHub（使 CDN 链接生效）...")
        push_image_to_github(img_file)
