import streamlit as st
import pandas as pd
import plotly.express as px
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
    with open("aedemobg.png", "rb") as f:
        bg_image_bytes = f.read()
    
    # 将图片编码为base64
    bg_image_base64 = base64.b64encode(bg_image_bytes).decode()
    
    # 设置背景样式和全局样式
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:image/png;base64,{bg_image_base64}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        
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
        
        /* 强制去除树图边框 - 更全面的选择器 */
        .js-plotly-plot .treemap path,
        .js-plotly-plot .treemap-entry path,
        .js-plotly-plot g.treemap path,
        .js-plotly-plot svg g path,
        .js-plotly-plot .trace path,
        .plotly .treemap path {{
            stroke: none !important;
            stroke-width: 0 !important;
            stroke-opacity: 0 !important;
            border: none !important;
        }}
        
        /* 直接针对所有SVG路径元素 */
        .js-plotly-plot svg path {{
            stroke: transparent !important;
            stroke-width: 0 !important;
        }}
        
        /* 修正树图内文字颜色 - 通过CSS覆盖 */
        .js-plotly-plot .treemap-child text {{
            fill: #1A1A1A !important;
        }}
        
        /* 对于等待时间>3h的区块，覆盖为白色文字 */
        .js-plotly-plot .treemap-child text[data-long-wait="true"] {{
            fill: #FFFFFF !important;
        }}
        
        /* 标题和更新信息共用样式 - 确保一致的外观 */
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
    
    # 页面标题 - 使用与更新信息相同的样式类
    st.markdown('<h1 class="black-text title-text">🏥 Hong Kong A&E Waiting Time</h1>', unsafe_allow_html=True)
    
    # 加载数据
    df = load_data()
    
    if df is None:
        st.warning("无法加载数据，请检查网络连接或稍后再试。")
    else:
        # 显示树图
        display_treemap(df)
        
        # 更新说明 - 使用相同的基础样式类
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
    """显示树图可视化"""
    # 准备树图数据
    treemap_df = df.copy()
    treemap_df['hospital_name'] = treemap_df['hospCode'].map(hospital_names)
    
    # 确保等待时间显示在文本中
    treemap_df['display_name'] = treemap_df['hospital_name'] + '<br>' + treemap_df['hospCode'] + ' ' + treemap_df['topWait']
    
    # 添加标记长等待时间的列（用于着色）
    treemap_df['is_long_wait'] = treemap_df['topWait'].apply(
        lambda x: '> 3' in x or '> 4' in x or '> 5' in x or '> 6' in x or '> 7' in x or '> 8' in x
    )
    
    # 生成树图
    fig = px.treemap(
        treemap_df,
        path=['display_name'],  # 单层树图
        values='waitTimeNumeric',  # 根据等待时间调整方块大小
        color='waitTimeNumeric',   # 根据等待时间着色
        color_continuous_scale=get_color_scale(),  # 使用原有的渐变色方案
        range_color=[0, 9],  # 颜色映射范围，与原来的9档一致
        custom_data=['topWait', 'hospCode', 'waitTimeNumeric', 'is_long_wait'],  # 额外数据用于标签和悬停
        branchvalues='total'  # 确保数值正确累加
    )
    
    # 配置树图样式 - 完全去除边框
    fig.update_traces(
        texttemplate='%{label}',  # 只显示标签，等待时间已包含在label中
        hovertemplate='<b>%{label}</b><br>',
        marker_line_width=0,  # 边框宽度设为0
        marker_line_color='rgba(0,0,0,0)',  # 边框颜色设为透明
        marker=dict(
            line=dict(width=0, color='rgba(0,0,0,0)'),  # 额外确保边框设置
        ),
        root_color='rgba(0,0,0,0)',  # 使用rgba格式的透明色
        textposition='middle center',  # 文本居中
        textfont=dict(
            family="Arial, sans-serif",
            size=20  # 使用固定字体大小，替换原来的动态大小
        )
    )
    
    # 设置布局
    fig.update_layout(
        margin=dict(t=0, l=0, r=0, b=0),  # 去除边距
        coloraxis_showscale=False,  # 隐藏色彩比例尺
        height=600,  # 调整高度
        paper_bgcolor='rgba(0,0,0,0)',  # 透明背景
        plot_bgcolor='rgba(0,0,0,0)',  # 透明背景
        # 强制去除所有边框设置
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False)
    )
    
    # 额外设置，强制去除边框
    fig.update_traces(
        marker_line=dict(width=0, color='rgba(0,0,0,0)'),
        line=dict(width=0, color='rgba(0,0,0,0)')
    )
    
    # 显示树图
    st.plotly_chart(fig, use_container_width=True)
    
    # 添加强制去除边框的JavaScript
    st.markdown("""
    <script>
    setTimeout(function() {
        var paths = document.querySelectorAll('.js-plotly-plot svg path');
        paths.forEach(function(path) {
            path.style.stroke = 'none';
            path.style.strokeWidth = '0';
            path.setAttribute('stroke', 'none');
            path.setAttribute('stroke-width', '0');
        });
    }, 1500);
    
    setTimeout(function() {
        var paths = document.querySelectorAll('.js-plotly-plot svg path');
        paths.forEach(function(path) {
            path.style.stroke = 'none';
            path.style.strokeWidth = '0';
        });
    }, 3000);
    </script>
    """, unsafe_allow_html=True)

# 确保脚本在直接运行时执行主函数
if __name__ == "__main__":
    main()
