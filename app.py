import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import base64

def main():
    # 页面配置
    st.set_page_config(
        page_title="Hong Kong A&E Waiting Time",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # 使用本地图片文件作为背景
    try:
        with open("aedemobg.png", "rb") as f:
            bg_image_bytes = f.read()
        
        # 将图片编码为base64
        bg_image_base64 = base64.b64encode(bg_image_bytes).decode()
        
        # 设置带背景图的样式
        background_style = f"""
        .stApp {{
            background-image: url("data:image/png;base64,{bg_image_base64}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        """
    except Exception as e:
        st.warning(f"无法加载背景图片: {e}")
        background_style = ""
    
    # 设置全局样式
    st.markdown(
        f"""
        <style>
        {background_style}
        
        /* 全局文字色 */
        h1, h2, h3, p, span, div {{
            color: #4a4238;
        }}
        
        /* 覆盖白底 */
        [style*="background-color: white"],
        [style*="background: white"] {{
            background-color: transparent !important;
            background: transparent !important;
        }}
        
        /* 调整图表容器 */
        .js-plotly-plot, .plotly, .plot-container {{
            background-color: transparent !important;
        }}
        
        /* 标题和更新信息共用样式 */
        .black-text {{
            color: #000000 !important;
            font-weight: 600 !important;
            text-align: center;
        }}
        
        /* 标题特有样式 */
        .title-text {{
            font-size: 3rem !important;
            margin-bottom: 1rem;
        }}
        
        /* 更新信息特有样式 */
        .update-info {{
            font-size: 2em !important;
            margin-top: 30px;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # 页面标题
    st.markdown('<h1 class="black-text title-text">🏥 Hong Kong A&E Waiting Time</h1>', unsafe_allow_html=True)
    
    # 加载数据
    df = load_data()
    
    if df is None:
        st.warning("无法加载数据，请检查网络连接或稍后再试。")
    else:
        # 树图
        display_treemap(df)
        
        # 更新说明
        st.markdown(
            '<div class="black-text update-info">'
            '数据在每小时的第4、21、36、51分钟自动更新<br>'
            'Data is automatically updated at the 4, 21, 36 and 51 minutes of each hour.'
            '</div>',
            unsafe_allow_html=True
        )

def parse_wait_time(text):
    """将等待文本转为数值，但保留格式用于显示"""
    if not text:
        return 0
    if '< 1' in text:
        return 0.5
    try:
        return int(text.replace('>', '').strip())
    except:
        return 0

def get_color_scale():
    """返回红色单色渐变：<1, >1, >2, …, >8（共9档）"""
    return [
        [0, '#ffe5e5'], [0.125, '#ffcccc'], [0.25, '#ffb2b2'], [0.375, '#ff9999'],
        [0.5, '#ff7f7f'], [0.625, '#ff6666'], [0.75, '#ff4c4c'], [0.875, '#ff3232'],
        [1.0, '#ff1919']
    ]

def load_data():
    """拉取最新数据"""
    try:
        # 当前 UTC+8 时间
        now_ts = datetime.utcnow().timestamp() + 8 * 3600
        utc8 = datetime.utcfromtimestamp(now_ts)
        m = utc8.minute
        if m < 4:
            minute_str, hour = '47', (utc8.hour - 1) % 24
        elif m < 21:
            minute_str, hour = '02', utc8.hour
        elif m < 36:
            minute_str, hour = '17', utc8.hour
        elif m < 51:
            minute_str, hour = '32', utc8.hour
        else:
            minute_str, hour = '47', utc8.hour

        fn = f"{utc8.strftime('%Y%m%d')}_{hour:02d}{minute_str}.csv"
        url = f"https://huggingface.co/datasets/StannumX/aedemo/raw/main/data/{fn}"
        df = pd.read_csv(url)

        df['waitTimeNumeric'] = df['topWait'].apply(parse_wait_time)
        return df
    except Exception as e:
        st.error(f"加载数据时出错: {e}")
        return None

# 医院代码→中文名
hospital_names = {
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
    'RH' : '律敦治醫院',
    'SJH': '長洲醫院',
    'TSH': '天水圍醫院',
    'TKO': '將軍澳醫院',
    'TMH': '屯門醫院',
    'UCH': '基督教聯合醫院',
    'YCH': '仁濟醫院'
}

def display_treemap(df):
    """显示树图可视化 - 使用直接指定文本颜色的方法"""
    # 准备树图数据
    treemap_df = df.copy()
    treemap_df['hospital_name'] = treemap_df['hospCode'].map(hospital_names)
    
    # 确定文本颜色 - 关键改变：直接在数据中指定每个方块的文本颜色
    treemap_df['text_color'] = treemap_df['waitTimeNumeric'].apply(
        lambda x: 'white' if x >= 3 else 'black'
    )
    
    # 创建自定义标签，带有HTML格式的颜色
    treemap_df['display_name'] = treemap_df.apply(
        lambda row: f"{row['hospital_name']}<br>{row['hospCode']} {row['topWait']}",
        axis=1
    )
    
    # 创建图表，但不使用px.treemap，而是使用更直接的go.Treemap
    fig = go.Figure(go.Treemap(
        labels=treemap_df['display_name'],
        parents=[""] * len(treemap_df),  # 所有项目都是顶级项目
        values=treemap_df['waitTimeNumeric'],
        branchvalues="total",
        marker=dict(
            colors=treemap_df['waitTimeNumeric'],
            colorscale=get_color_scale(),
            cmin=0,
            cmax=9,
            line=dict(width=1, color='rgba(0,0,0,0.2)')
        ),
        textfont=dict(
            # 直接在这里设置文本颜色
            color=treemap_df['text_color'],
            family="Arial, sans-serif",
            size=20
        ),
        hovertemplate='<b>%{label}</b><br>',
        textposition="middle center"
    ))
    
    # 设置布局
    fig.update_layout(
        margin=dict(t=0, l=0, r=0, b=0),
        height=600,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        coloraxis_showscale=False
    )
    
    # 显示树图
    st.plotly_chart(fig, use_container_width=True)
    
    # 备份方案：如果直接设置颜色失败，尝试用JavaScript修复
    # 这个JavaScript更有针对性，直接修改SVG文本元素
    js_code = """
    <script>
    function fixTextColors() {
        try {
            // 直接定位所有SVG文本元素
            const allTextElements = document.querySelectorAll('svg text');
            allTextElements.forEach(text => {
                const content = text.textContent || '';
                // 检查内容是否包含指定的等待时间
                if (content.includes('> 3') || content.includes('> 4') || 
                    content.includes('> 5') || content.includes('> 6') || 
                    content.includes('> 7') || content.includes('> 8')) {
                    // 强制设置文本颜色
                    text.setAttribute('fill', '#FFFFFF');
                    text.style.setProperty('fill', '#FFFFFF', 'important');
                    // 还可以尝试设置stroke属性，以增强可见性
                    text.setAttribute('stroke', 'none');
                }
            });
        } catch (e) {
            console.error('Error fixing text colors:', e);
        }
    }

    // 多次尝试应用文本颜色修复
    setTimeout(fixTextColors, 500);
    setTimeout(fixTextColors, 1000);
    setTimeout(fixTextColors, 2000);
    setTimeout(fixTextColors, 3000);
    
    // 监听DOM变化，持续应用修复
    const observer = new MutationObserver((mutations) => {
        fixTextColors();
    });
    
    // 开始观察文档变化
    observer.observe(document.body, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ['fill', 'style']
    });
    </script>
    """
    
    # 添加JavaScript
    st.markdown(js_code, unsafe_allow_html=True)

# 确保脚本在直接运行时执行主函数
if __name__ == "__main__":
    main()
