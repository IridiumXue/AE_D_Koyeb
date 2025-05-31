import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
from datetime import datetime
import base64
import io
from typing import Optional, Dict, List
import requests

# ==================== 页面配置（必须在最前面）====================
st.set_page_config(
    page_title="Hong Kong A&E Waiting Time",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==================== 配置 ====================
def get_config():
    """获取应用配置"""
    return {
        'page': {
            'title': "Hong Kong A&E Waiting Time",
            'icon': "🏥"
        },
        'style': {
            'background_image': "aedemobg.png",
            'primary_color': "#4a4238",
            'title_size': "3rem",
            'update_info_size': "2em"
        },
        'data': {
            'base_url': "https://huggingface.co/datasets/StannumX/aedemo/raw/main/data/",
            'timezone_offset': 8
        },
        'visualization': {
            'figure_height': 8,
            'figure_width': 14,
            'high_wait_threshold': 3,
            'font_size': 12
        }
    }

def get_hospital_names():
    """获取医院名称映射"""
    return {
        'AHN': '雅麗氏何妙齡那打素醫院', 'CMC': '明愛醫院', 'KWH': '廣華醫院',
        'NDH': '北區醫院', 'NLT': '北大嶼山醫院', 'PYN': '東區尤德夫人那打素醫院',
        'POH': '博愛醫院', 'PWH': '威爾斯親王醫院', 'PMH': '瑪嘉烈醫院',
        'QEH': '伊利沙伯醫院', 'QMH': '瑪麗醫院', 'RH': '律敦治醫院',
        'SJH': '長洲醫院', 'TSH': '天水圍醫院', 'TKO': '將軍澳醫院',
        'TMH': '屯門醫院', 'UCH': '基督教聯合醫院', 'YCH': '仁濟醫院'
    }

# ==================== 数据处理 ====================
class DataProcessor:
    """数据处理器"""
    
    @staticmethod
    def parse_wait_time(text: str) -> float:
        """解析等待时间"""
        if not text:
            return 0
        if '< 1' in text:
            return 0.5
        try:
            return int(text.replace('>', '').strip())
        except (ValueError, AttributeError):
            return 0
    
    @staticmethod
    def get_data_filename() -> str:
        """生成数据文件名"""
        config = get_config()
        now_ts = datetime.utcnow().timestamp() + config['data']['timezone_offset'] * 3600
        utc8 = datetime.utcfromtimestamp(now_ts)
        
        minute_mappings = [
            (4, '47', -1), (21, '02', 0), (36, '17', 0),
            (51, '32', 0), (60, '47', 0)
        ]
        
        for threshold, minute_str, hour_offset in minute_mappings:
            if utc8.minute < threshold:
                hour = (utc8.hour + hour_offset) % 24
                return f"{utc8.strftime('%Y%m%d')}_{hour:02d}{minute_str}.csv"
        
        return f"{utc8.strftime('%Y%m%d')}_{utc8.hour:02d}47.csv"
    
    @classmethod
    def load_data(cls) -> Optional[pd.DataFrame]:
        """加载数据"""
        try:
            config = get_config()
            filename = cls.get_data_filename()
            url = f"{config['data']['base_url']}{filename}"
            
            df = pd.read_csv(url)
            df['waitTimeNumeric'] = df['topWait'].apply(cls.parse_wait_time)
            df['hospital_name'] = df['hospCode'].map(get_hospital_names())
            
            return df
        except Exception as e:
            st.error(f"数据加载失败: {e}")
            return None

# ==================== 样式处理 ====================
class StyleManager:
    """样式管理器"""
    
    @staticmethod
    def load_background_style() -> str:
        """加载背景样式"""
        config = get_config()
        try:
            with open(config['style']['background_image'], "rb") as f:
                bg_bytes = f.read()
            
            bg_base64 = base64.b64encode(bg_bytes).decode()
            return f"""
            .stApp {{
                background-image: url("data:image/png;base64,{bg_base64}");
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
                background-attachment: fixed;
            }}
            """
        except Exception as e:
            st.warning(f"背景图片加载失败: {e}")
            return ""
    
    @classmethod
    def apply_styles(cls):
        """应用页面样式"""
        config = get_config()
        bg_style = cls.load_background_style()
        
        styles = f"""
        <style>
        {bg_style}
        
        h1, h2, h3, p, span, div {{
            color: {config['style']['primary_color']};
        }}
        
        [style*="background-color: white"],
        [style*="background: white"] {{
            background-color: transparent !important;
            background: transparent !important;
        }}
        
        .black-text {{
            color: #000000 !important;
            font-weight: 600 !important;
            text-align: center;
        }}
        
        .title-text {{
            font-size: {config['style']['title_size']} !important;
            margin-bottom: 1rem;
        }}
        
        .update-info {{
            font-size: {config['style']['update_info_size']} !important;
            margin-top: 30px;
        }}
        </style>
        """
        
        st.markdown(styles, unsafe_allow_html=True)

# ==================== 可视化 ====================
class TreemapVisualizer:
    """树状图可视化器"""
    
    @staticmethod
    def create_colormap():
        """创建颜色映射"""
        colors = ['#ffe5e5', '#ffcccc', '#ffb2b2', '#ff9999', 
                 '#ff7f7f', '#ff6666', '#ff4c4c', '#ff3232', '#ff1919']
        return LinearSegmentedColormap.from_list("custom", colors, N=256)
    
    @classmethod
    def calculate_layout(cls, values: List[float], width: float = 1.0, height: float = 1.0) -> List[Dict]:
        """计算树状图布局（简化版二元分割算法）"""
        if not values:
            return []
        
        total = sum(values)
        if total == 0:
            return []
        
        # 按值排序
        indexed_values = [(i, v) for i, v in enumerate(values)]
        indexed_values.sort(key=lambda x: x[1], reverse=True)
        
        rectangles = []
        
        def split_rectangle(items, x, y, w, h, horizontal=True):
            if len(items) == 1:
                rectangles.append({
                    'index': items[0][0],
                    'x': x, 'y': y, 'width': w, 'height': h,
                    'value': items[0][1]
                })
                return
            
            if len(items) == 0:
                return
            
            # 找到最佳分割点
            total_val = sum(item[1] for item in items)
            if total_val == 0:
                return
                
            best_ratio = 0.5
            split_idx = len(items) // 2
            
            if len(items) > 1:
                # 尝试平衡分割
                cumsum = 0
                for i in range(len(items) - 1):
                    cumsum += items[i][1]
                    ratio = cumsum / total_val
                    if 0.3 <= ratio <= 0.7:
                        best_ratio = ratio
                        split_idx = i + 1
                        break
                
                if split_idx == 0:
                    split_idx = 1
                elif split_idx >= len(items):
                    split_idx = len(items) - 1
                
                best_ratio = sum(item[1] for item in items[:split_idx]) / total_val
            
            if horizontal:
                split_pos = x + w * best_ratio
                split_rectangle(items[:split_idx], x, y, w * best_ratio, h, not horizontal)
                split_rectangle(items[split_idx:], split_pos, y, w * (1 - best_ratio), h, not horizontal)
            else:
                split_pos = y + h * best_ratio
                split_rectangle(items[:split_idx], x, y, w, h * best_ratio, not horizontal)
                split_rectangle(items[split_idx:], x, split_pos, w, h * (1 - best_ratio), not horizontal)
        
        split_rectangle(indexed_values, 0, 0, width, height, True)
        
        # 按原始索引排序返回
        rectangles.sort(key=lambda x: x['index'])
        return rectangles
    
    @classmethod
    def create_treemap(cls, df: pd.DataFrame) -> plt.Figure:
        """创建树状图"""
        config = get_config()
        
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
        fig, ax = plt.subplots(figsize=(config['visualization']['figure_width'], 
                                      config['visualization']['figure_height']))
        
        # 准备数据
        values = df['waitTimeNumeric'].tolist()
        labels = df.apply(lambda row: f"{row['hospital_name']}\n{row['hospCode']} {row['topWait']}", axis=1).tolist()
        
        # 计算布局
        layout = cls.calculate_layout(values)
        
        # 创建颜色映射
        cmap = cls.create_colormap()
        norm = plt.Normalize(vmin=0, vmax=9)
        
        # 绘制矩形
        for i, rect in enumerate(layout):
            if i >= len(df):
                continue
                
            value = df.iloc[i]['waitTimeNumeric']
            color = cmap(norm(value))
            
            # 创建矩形
            rectangle = patches.Rectangle(
                (rect['x'], rect['y']), rect['width'], rect['height'],
                linewidth=1, edgecolor='rgba(0,0,0,0.2)', facecolor=color
            )
            ax.add_patch(rectangle)
            
            # 添加文字
            text_color = 'white' if value >= config['visualization']['high_wait_threshold'] else 'black'
            
            # 计算文字大小
            area = rect['width'] * rect['height']
            font_size = min(config['visualization']['font_size'], 
                          max(8, int(area * 100)))
            
            ax.text(
                rect['x'] + rect['width']/2, 
                rect['y'] + rect['height']/2,
                labels[i], 
                ha='center', va='center',
                fontsize=font_size,
                color=text_color,
                weight='bold',
                wrap=True
            )
        
        # 设置轴
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_aspect('equal')
        ax.axis('off')
        
        # 设置透明背景
        fig.patch.set_alpha(0)
        ax.patch.set_alpha(0)
        
        plt.tight_layout()
        return fig

# ==================== 缓存函数 ====================
@st.cache_data(ttl=300)  # 缓存5分钟
def cached_load_data():
    """缓存的数据加载函数"""
    return DataProcessor.load_data()

@st.cache_data
def cached_background_style():
    """缓存的背景样式加载"""
    return StyleManager.load_background_style()

# ==================== 主应用 ====================
def main():
    """主函数"""
    # 应用样式
    StyleManager.apply_styles()
    
    # 显示标题
    config = get_config()
    st.markdown(
        f'<h1 class="black-text title-text">{config["page"]["icon"]} {config["page"]["title"]}</h1>',
        unsafe_allow_html=True
    )
    
    # 加载数据
    df = cached_load_data()
    
    if df is None:
        st.warning("无法加载数据，请检查网络连接或稍后再试。")
        return
    
    # 显示可视化
    with st.spinner("正在生成可视化..."):
        fig = TreemapVisualizer.create_treemap(df)
        
        # 将图表转换为图片并显示
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight', 
                   facecolor='none', edgecolor='none')
        buf.seek(0)
        
        st.image(buf, use_column_width=True)
        plt.close(fig)  # 释放内存
    
    # 显示更新信息
    if not df.empty:
        last_update = df['hospTimeEn'].iloc[0]
        st.markdown(
            f'<div class="black-text update-info">'
            f'数据最后更新时间：{last_update}<br>'
            f'Data last updated: {last_update}'
            '</div>',
            unsafe_allow_html=True
        )

if __name__ == "__main__":
    main()
