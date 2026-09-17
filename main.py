import os
import requests
import json
import time
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np

# =====================================================================
# 🚨 【小白专区】请在这里准确填写你的个人配置
# =====================================================================
# 微信公众号凭据(已替换原钉钉 Webhook)
WECHAT_APPID = "wx51e6c36abfcc6e72"
WECHAT_APPSECRET = "c7d90937fcd0e51e933f938d6d80212d"
# 图文素材永久素材 CDN 前缀(用于草稿正文 <img src> 渲染)
WECHAT_CDN_PREFIX = "https://api.weixin.qq.com/cgi-bin/material/get?access_token={token}&media_id={media_id}"

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
    url = "https://eastmoney.com"
    
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
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'sans-serif', 'Arial Unicode MS']
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
# 🔗 第三部分：推送图文草稿到微信公众号草稿箱
# =====================================================================
def _get_wechat_access_token(appid, appsecret):
    """通过 client_credential 拿到 access_token"""
    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {
        "grant_type": "client_credential",
        "appid": appid,
        "secret": appsecret,
    }
    res = requests.get(url, params=params, timeout=15).json()
    if "access_token" not in res:
        raise RuntimeError(f"获取 access_token 失败: {res}")
    return res["access_token"], res.get("expires_in", 7200)


def _upload_wechat_material(access_token, img_path, media_type="image"):
    """上传永久素材,返回 media_id 和 url(图文消息里 <img src> 用)"""
    url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={access_token}&type={media_type}"
    with open(img_path, "rb") as f:
        files = {"media": (os.path.basename(img_path), f, "image/png")}
        res = requests.post(url, files=files, timeout=60).json()
    if "media_id" not in res:
        raise RuntimeError(f"上传素材失败: {res}")
    return res["media_id"], res.get("url", "")


def _add_wechat_draft(access_token, title, content, thumb_media_id):
    """写入草稿箱,返回草稿 media_id"""
    url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={access_token}"
    payload = {
        "articles": [
            {
                "title": title,
                "author": "A 股主力资金监测",
                "content": content,
                "thumb_media_id": thumb_media_id,
                "need_open_comment": 0,
                "only_fans_can_comment": 0,
            }
        ]
    }
    res = requests.post(url, json=payload, timeout=30).json()
    if "media_id" not in res:
        raise RuntimeError(f"草稿创建失败: {res}")
    return res["media_id"]


def push_image_to_wechat_draft(appid, appsecret, img_path, report_type):
    """主入口:获取 token → 上传图片 → 写入草稿箱"""
    today_date = datetime.now().strftime("%Y-%m-%d")
    time_label = "【午盘】中场" if report_type == "midday" else "【收盘】全天"

    print("🔐 第 3.1 步：获取 access_token...")
    access_token, _ = _get_wechat_access_token(appid, appsecret)

    print("📤 第 3.2 步：上传长图为永久素材(image)...")
    media_id, material_url = _upload_wechat_material(access_token, img_path, "image")
    # 正文 <img src> 优先用上传返回的 url;缺失则回退到 material/get 接口
    img_src = material_url or WECHAT_CDN_PREFIX.format(token=access_token, media_id=media_id)

    print("📝 第 3.3 步：写入微信公众号草稿箱...")
    title = f"今日{time_label}主力资金长图已就绪 {today_date}"
    content = (
        f"<h2 style='text-align:center;'>📊 今日A股全景核心板块{time_label}【主力】资金大长图已洗净！</h2>"
        f"<p style='text-align:center;'><strong>快报日期</strong>：{today_date}</p>"
        f"<hr/>"
        f"<p style='text-align:center;'><img src='{img_src}' alt='主力资金全景长图'/></p>"
        f"<hr/>"
        f"<p>⚠️ <em>免责声明：本内容仅供客观数据事实复盘，不构成任何投资买卖建议。</em></p>"
    )
    draft_id = _add_wechat_draft(access_token, title, content, thumb_media_id=media_id)
    print(f"🎉【{time_label}特刊完美收官】草稿已写入公众号草稿箱! draft_id={draft_id}")


if __name__ == "__main__":
    print("📅 [验证开始] 正在检测大盘是否处于开盘交易状态...")
    if check_is_market_closed():
        print("😴 检测到今天非交易日，自动化工作流优雅休眠退出。")
    else:
        # 💡 智能化总线判断：当前是中午还是下午收盘
        current_hour = datetime.now().hour
        # 北京时间 11:30~13:30 之间运行则判定为午盘
        current_report_type = "midday" if 11 <= current_hour < 14 else "closing"

        print(f"🔄 第一步：启动数据清洗进程，当前判定时段为: {current_report_type}")
        stock_data = get_all_merged_capital_flow()

        print("🎨 第二步：调用零轴中置绘图引擎渲染高级长图...")
        img_file = generate_infographic_image(stock_data, current_report_type)

        print("🔑 第三步：推送图文草稿到微信公众号草稿箱...")
        push_image_to_wechat_draft(WECHAT_APPID, WECHAT_APPSECRET, img_file, current_report_type)
