import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import base64
from typing import Optional, Dict, Any

# ==================== 配置和常量 ====================
class Config:
    """应用配置类"""
    PAGE_TITLE = "Hong Kong A&E Waiting Time"
    PAGE_ICON = "🏥"
    LAYOUT = "wide"
    
    # 样式配置
    BACKGROUND_IMAGE = "aedemobg.png"
    PRIMARY_COLOR = "#4a4238"
    TITLE_SIZE = "3rem"
    UPDATE_INFO_SIZE = "2em"
    
    # 数据配置
    DATA_BASE_URL = "https://huggingface.co/datasets/StannumX/aedemo/raw/main/data/"
    TIMEZONE_OFFSET = 8  # UTC+8
    
    # 可视化配置
    TREEMAP_HEIGHT = 600
    TEXT_SIZE = 20
    HIGH_WAIT_THRESHOLD = 3  # 大于等于此值使用白色文字

# 医院代码映射
HOSPITAL_NAMES = {
    'AHN': '雅麗氏何妙齡那打素醫院',
    'CMC': '明愛醫院',
    'KWH': '廣華醫院',
    'NDH': '北區醫院',
    'NLT': '北大嶼山醫院',
    'PYN': '東區尤德夫人那打素醫院',
    'POH': '博愛醫院',
    'PWH': '威爾斯親王醫院',
    'PMH': '瑪嘉烈醫院',
    'QEH': '伊利沙伯醫院',
    'QMH': '瑪麗醫院',
    'RH': '律敦治醫院',
    'SJH': '長洲醫院',
    'TSH': '天水圍醫院',
    'TKO': '將軍澳醫院',
    'TMH': '屯門醫院',
    'UCH': '基督教聯合醫院',
    'YCH': '仁濟醫院'
}

# 顏色漸變配置
COLOR_SCALE = [
    [0, '#ffe5e5'], [0.125, '#ffcccc'], [0.25, '#ffb2b2'], [0.375, '#ff9999'],
    [0.5, '#ff7f7f'], [0.625, '#ff6666'], [0.75, '#ff4c4c'], [0.875, '#ff3232'],
    [1.0, '#ff1919']
]

# ==================== 工具函数 ====================
def parse_wait_time(text: str) -> float:
    """
    将等待时间文本转换为数值
    
    Args:
        text: 等待时间文本，如 "< 1", "> 2" 等
        
    Returns:
        数值化的等待时间
    """
    if not text:
        return 0
    if '< 1' in text:
        return 0.5
    try:
        return int(text.replace('>', '').strip())
    except (ValueError, AttributeError):
        return 0

def get_current_data_filename() -> str:
    """
    根据当前时间生成数据文件名
    
    Returns:
        数据文件名
    """
    now_ts = datetime.utcnow().timestamp() + Config.TIMEZONE_OFFSET * 3600
    utc8 = datetime.utcfromtimestamp(now_ts)
    
    # 根据分钟数确定数据更新时间点
    minute_mappings = [
        (4, '47', -1),    # 0-3分钟：使用上一小时的47分数据
        (21, '02', 0),    # 4-20分钟：使用当前小时的02分数据
        (36, '17', 0),    # 21-35分钟：使用当前小时的17分数据
        (51, '32', 0),    # 36-50分钟：使用当前小时的32分数据
        (60, '47', 0)     # 51-59分钟：使用当前小时的47分数据
    ]
    
    for threshold, minute_str, hour_offset in minute_mappings:
        if utc8.minute < threshold:
            hour = (utc8.hour + hour_offset) % 24
            return f"{utc8.strftime('%Y%m%d')}_{hour:02d}{minute_str}.csv"
    
    # 默认情况（不应该到达这里）
    return f"{utc8.strftime('%Y%m%d')}_{utc8.hour:02d}47.csv"

def load_background_image() -> str:
    """
    加载背景图片并返回CSS样式
    
    Returns:
        CSS样式字符串
    """
    try:
        with open(Config.BACKGROUND_IMAGE, "rb") as f:
            bg_image_bytes = f.read()
        
        bg_image_base64 = base64.b64encode(bg_image_bytes).decode()
        return f"""
        .stApp {{
            background-image: url("data:image/png;base64,{bg_image_base64}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        """
    except FileNotFoundError:
        st.warning(f"背景图片文件 {Config.BACKGROUND_IMAGE} 未找到")
        return ""
    except Exception as e:
        st.warning(f"加载背景图片失败: {e}")
        return ""

def get_page_styles(background_style: str) -> str:
    """
    生成页面样式
    
    Args:
        background_style: 背景样式
        
    Returns:
        完整的CSS样式字符串
    """
    return f"""
    <style>
    {background_style}
    
    /* 全局文字颜色 */
    h1, h2, h3, p, span, div {{
        color: {Config.PRIMARY_COLOR};
    }}
    
    /* 移除白色背景 */
    [style*="background-color: white"],
    [style*="background: white"] {{
        background-color: transparent !important;
        background: transparent !important;
    }}
    
    /* 图表容器透明化 */
    .js-plotly-plot, .plotly, .plot-container {{
        background-color: transparent !important;
    }}
    
    /* 黑色文字样式 */
    .black-text {{
        color: #000000 !important;
        font-weight: 600 !important;
        text-align: center;
    }}
    
    /* 标题样式 */
    .title-text {{
        font-size: {Config.TITLE_SIZE} !important;
        margin-bottom: 1rem;
    }}
    
    /* 更新信息样式 */
    .update-info {{
        font-size: {Config.UPDATE_INFO_SIZE} !important;
        margin-top: 30px;
    }}
    </style>
    """

# ==================== 数据处理 ====================
def load_data() -> Optional[pd.DataFrame]:
    """
    加载急诊科等候时间数据
    
    Returns:
        包含等候时间数据的DataFrame，失败时返回None
    """
    try:
        filename = get_current_data_filename()
        url = f"{Config.DATA_BASE_URL}{filename}"
        
        df = pd.read_csv(url)
        df['waitTimeNumeric'] = df['topWait'].apply(parse_wait_time)
        
        return df
    except Exception as e:
        st.error(f"数据加载失败: {e}")
        return None

def prepare_treemap_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    准备树形图数据
    
    Args:
        df: 原始数据DataFrame
        
    Returns:
        处理后的数据DataFrame
    """
    treemap_df = df.copy()
    
    # 添加医院中文名称
    treemap_df['hospital_name'] = treemap_df['hospCode'].map(HOSPITAL_NAMES)
    
    # 确定文字颜色（深色背景用白色文字）
    treemap_df['text_color'] = treemap_df['waitTimeNumeric'].apply(
        lambda x: 'white' if x >= Config.HIGH_WAIT_THRESHOLD else 'black'
    )
    
    # 创建显示标签
    treemap_df['display_name'] = treemap_df.apply(
        lambda row: f"{row['hospital_name']}<br>{row['hospCode']} {row['topWait']}",
        axis=1
    )
    
    return treemap_df

# ==================== 可视化 ====================
def create_treemap(df: pd.DataFrame) -> go.Figure:
    """
    创建树形图可视化
    
    Args:
        df: 处理后的数据DataFrame
        
    Returns:
        Plotly图表对象
    """
    fig = go.Figure(go.Treemap(
        labels=df['display_name'],
        parents=[""] * len(df),
        values=df['waitTimeNumeric'],
        branchvalues="total",
        marker=dict(
            colors=df['waitTimeNumeric'],
            colorscale=COLOR_SCALE,
            cmin=0,
            cmax=9,
            line=dict(width=1, color='rgba(0,0,0,0.2)')
        ),
        textfont=dict(
            color=df['text_color'],
            family="Arial, sans-serif",
            size=Config.TEXT_SIZE
        ),
        hovertemplate='<b>%{label}</b><br>',
        textposition="middle center"
    ))
    
    fig.update_layout(
        margin=dict(t=0, l=0, r=0, b=0),
        height=Config.TREEMAP_HEIGHT,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        coloraxis_showscale=False
    )
    
    return fig

def add_text_color_fix_script():
    """添加文字颜色修复的JavaScript脚本"""
    js_code = """
    <script>
    function fixTextColors() {
        try {
            const textElements = document.querySelectorAll('svg text');
            textElements.forEach(text => {
                const content = text.textContent || '';
                // 检查是否为高等待时间（需要白色文字）
                const highWaitPattern = /> [3-8]/;
                if (highWaitPattern.test(content)) {
                    text.setAttribute('fill', '#FFFFFF');
                    text.style.setProperty('fill', '#FFFFFF', 'important');
                    text.setAttribute('stroke', 'none');
                }
            });
        } catch (e) {
            console.error('Text color fix error:', e);
        }
    }

    // 多次尝试修复和持续监听
    [500, 1000, 2000, 3000].forEach(delay => setTimeout(fixTextColors, delay));
    
    const observer = new MutationObserver(fixTextColors);
    observer.observe(document.body, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ['fill', 'style']
    });
    </script>
    """
    st.markdown(js_code, unsafe_allow_html=True)

def display_treemap(df: pd.DataFrame):
    """
    显示树形图可视化
    
    Args:
        df: 原始数据DataFrame
    """
    treemap_df = prepare_treemap_data(df)
    fig = create_treemap(treemap_df)
    
    st.plotly_chart(fig, use_container_width=True)
    add_text_color_fix_script()

def display_update_info(df: pd.DataFrame):
    """
    显示数据更新信息
    
    Args:
        df: 数据DataFrame
    """
    if df is not None and not df.empty:
        last_update_time = df['hospTimeEn'].iloc[0]
        st.markdown(
            f'<div class="black-text update-info">'
            f'数据最后更新时间：{last_update_time}<br>'
            f'Data last updated: {last_update_time}'
            '</div>',
            unsafe_allow_html=True
        )

# ==================== 主应用 ====================
def setup_page():
    """设置页面配置和样式"""
    st.set_page_config(
        page_title=Config.PAGE_TITLE,
        page_icon=Config.PAGE_ICON,
        layout=Config.LAYOUT,
        initial_sidebar_state="collapsed"
    )
    
    # 应用样式
    background_style = load_background_image()
    page_styles = get_page_styles(background_style)
    st.markdown(page_styles, unsafe_allow_html=True)
    
    # 显示标题
    st.markdown(
        f'<h1 class="black-text title-text">{Config.PAGE_ICON} {Config.PAGE_TITLE}</h1>',
        unsafe_allow_html=True
    )

def main():
    """主函数"""
    setup_page()
    
    # 加载和显示数据
    df = load_data()
    
    if df is None:
        st.warning("无法加载数据，请检查网络连接或稍后再试。")
        return
    
    # 显示可视化和更新信息
    display_treemap(df)
    display_update_info(df)

if __name__ == "__main__":
    main()
