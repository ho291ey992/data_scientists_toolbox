import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots # 用於建立多圖子圖畫布
import panel as pn # 用於建立互動式面板與數據更新

class SurveyVisualizer :
    def __init__(self, file_path, file_save_part):
        self.file_save_part = file_save_part
        # 載入資料
        con_responses = sqlite3.connect(file_path)

        sql_query ='''
        -- 程式語言
        select *
        from response_df
        '''
        self.responses = pd.read_sql(sql_query, con=con_responses)

        sql_query ='''
        -- 程式語言
        select *
        from responses_single_choice_group r
        '''
        self.responses_single_choice = pd.read_sql(sql_query, con=con_responses)

        sql_query ='''
        select *
        from kaggle_question_reference_table
        '''
        self.kaggle_question_reference_table = pd.read_sql(sql_query, con=con_responses)

        sql_query ='''
        select *
        from salary_order
        '''
        self.salary_order = pd.read_sql(sql_query, con=con_responses)

        sql_query ='''
        select *
        from country_area
        '''
        self.country_area = pd.read_sql(sql_query, con=con_responses)

        sql_query ='''
        select *
        from coding_exp_years_order
        '''
        self.coding_exp_years_order = pd.read_sql(sql_query, con=con_responses)

        sql_query ='''
        select *
        from prog_lang_skill_group
        '''
        self.prog_lang_skill_group = pd.read_sql(sql_query, con=con_responses)

        # 處理朝條圖 y 軸名稱重複問題。
        self.responses.loc[self.responses['response'] == 'Visual Studio', 'response'] = 'Visual　Studio'
        self.responses.loc[self.responses['response'] == 'Build and/or run the data infrastructure that my business uses for storing, analyzing, and operationalizing data', 'response'] = 'Build or/and run the data infrastructure that my business uses for storing, analyzing, and operationalizing data'

        # 修改 分類
        self.kaggle_question_reference_table.loc[self.kaggle_question_reference_table['col_eng'] == 'first_started_helpful', '分類'] = '外部資源與趨勢追蹤'
        self.kaggle_question_reference_table.loc[self.kaggle_question_reference_table['col_eng'] == 'industry', '分類'] = '職業與工作相關分析'

    # 分割資料
    def data(self, c): # 輸入為分類名稱，例如 '基礎輪廓分析'，函式會擷取對應題目的回答資料。
        responses = self.responses
        responses_single_choice = self.responses_single_choice
        kaggle_question_reference_table = self.kaggle_question_reference_table

        # 每題資料會存成 dict 的形式，方便之後個別取出繪圖。
        contents_dict  = {}
        # 資料條件
        col = kaggle_question_reference_table.loc[kaggle_question_reference_table['分類'] == c, 'col_eng']
        # 讀取資料
        df = responses[responses['question_index'].isin(col)]
        # 合併群組
        df = df.merge(responses_single_choice[['id', 'job_title_group', 'salary_group']], left_on='id', right_on='id', how='left')
        # 僅保留特定群組資料（如 Data-related）
        df = df[df['job_title_group']== 'Data-related']
        # salary_group 僅適用 salary，所以只去除 salary 資料中的錯誤資訊。
        df = df[~((df['salary_group']=='wrong_info') & (df['question_index']=='salary'))]
        df = df.iloc[:,:-2].groupby(['response', 'surveyed_in', 'question_index']).count().reset_index().rename(columns={'id':'count'}).sort_values('count')
        # 將回答切短為 short_label
        df['short_label'] = df['response'].apply(lambda x: x[:10] + '...' if len(x) > 12 else x)
        for i in kaggle_question_reference_table.loc[kaggle_question_reference_table['分類'] == c , 'col_eng']:
            x = kaggle_question_reference_table.loc[kaggle_question_reference_table['col_eng'] == i, '欄位'].values[0]
            contents_dict[x] = df[df['question_index'].isin([i])]
        return contents_dict

    # 資料處理
    def data_process(self, d):
        d = d.reset_index(drop=True)
        len_d = len(d)
        
        is_multi_year = len(d['surveyed_in'].drop_duplicates()) > 1
        # 圓餅圖：若有多個年份的資料，聚合後處理 top 9 + other
        if is_multi_year:
            x = {}
            d = d.groupby(['response','question_index','short_label']).sum().sort_values('count').reset_index()
            for i in d.columns :
                if (i == 'response') and ((len_d > 9) and (len(d['surveyed_in'].drop_duplicates()) > 1)):
                    x[i] = ['other']
                elif i == 'count':
                    x[i] = [d[i][:-9].sum()]
                else:
                    x[i] = [d[i][0]]
            d = pd.concat([d[-9:], pd.DataFrame(x)], axis=0).reset_index(drop=True).sort_values('count')
            # 計算百分比。
            d['count_pct'] = round((d['count'] / d['count'].sum()) * 100, 2)
            # 產生 text 文字，將資料轉為文字(str)，例如：1000 人 (50.0%)
            d['text'] = d.apply(lambda row: f"{row['count']}人 ({row['count_pct']:.1f} %)", axis=1)
            return d.drop(columns='surveyed_in').reset_index(drop=True)
        # 橫條圖：若只有單一年度，直接抓 top 9
        else:
            # 計算百分比。
            d['count_pct'] = round((d['count'] / d['count'].sum()) * 100, 2)
            # 產生 text 文字，將資料轉為文字(str)，例如：1000 人 (50.0%)
            d['text'] = d.apply(lambda row: f"{row['count']}人 ({row['count_pct']:.1f} %)", axis=1)
            return d[-9:]
    
    # Callback：更新圖表內容
    def update_plot(self, event):
        print(self.selector, self.selector.value)
        fig = make_subplots(rows=2, cols=2,
                            specs=[[{'type': 'xy'}, {'type': 'xy'}],
                                [{'type': 'xy'}, {'type': 'domain'}]],       # 每格子圖型別（xy 為折線、長條圖，domain 為圓餅圖）
                            subplot_titles=["2020年", "2021年", "2022年", "總計"],    # 子圖標題
                            horizontal_spacing = 0.1,                             # 子圖間水平距離（0 ~ 1）
                            vertical_spacing = 0.1                                # 子圖間垂直距離（0 ~ 1）
                        )
        df_up_data = self.contents_dict[self.selector.value]
        data_2020 = self.data_process(df_up_data[(df_up_data['surveyed_in'] == 2020)])
        data_2021 = self.data_process(df_up_data[(df_up_data['surveyed_in'] == 2021)])
        data_2022 = self.data_process(df_up_data[(df_up_data['surveyed_in'] == 2022)])
        data_all  = self.data_process(df_up_data)
        # 加入長條圖
        if len(data_2020['response']) > 0:
            fig.add_trace(
                go.Bar(y=data_2020['short_label'], 
                    x=data_2020['count'], 
                    orientation='h', 
                    text=data_2020['text'],
                    hovertext = data_2020['response'], # 新增完整題目
                    hovertemplate = ''), 
                row=1, col=1
            )

        if len(data_2021['response']) > 0:
            fig.add_trace(
                go.Bar(y=data_2021['short_label'],
                    x=data_2021['count'], 
                    orientation='h', 
                    text=data_2021['text'],
                    hovertext = data_2021['response'], # 新增完整題目
                    hovertemplate = ''), 
                row=2, col=1
            )

        if len(data_2022['response']) > 0:
            fig.add_trace(
                go.Bar(y=data_2022['short_label'],
                        x=data_2022['count'], 
                        orientation='h', 
                        text=data_2022['text'],
                        hovertext = data_2022['response'], # 新增完整題目
                        hovertemplate = ''), 
                row=1, col=2
                )

        # 加入圓餅圖
        fig.add_trace(
            go.Pie(labels=data_all['response'], 
                values=data_all['count'], 
                text=data_all['count'],
                hole=.5,  # 製作甜甜圈圖樣式，使視覺更清爽
                hovertemplate = ''), 
            row=2, col=2
        )
        
        fig.update_traces(
            customdata=data_all['text'], # 顯示格式為：1000人 (50.0%)，由 data_process() 預先計算好 text 欄位
            textposition='outside',      # 決定文字顯示在柱內或柱外
            row=2, col=2
        )

        fig.update_layout(
            showlegend=False,   # 關閉圖例區
            xaxis_title=None,   # 移除 x軸標籤
            yaxis_title=None,    # 移除 y軸標籤
            margin=dict(l=20, r=20, t=30, b=20) # 設定標題與圖片的間距。
        )

        self.plot_pane.object = fig

    # 長條圖_圓餅圖
    def bar_pie(self):
        for i in self.kaggle_question_reference_table['分類'].drop_duplicates():
            print(i)
            # 資料讀取
            self.contents_dict = self.data(i)
            # 選單
            list_keys = list(self.contents_dict.keys())
            self.selector = pn.widgets.Select(name=i, options=list_keys, value=list_keys[0])
            
            # 將選單改右
            header = pn.Row(
                            pn.pane.Markdown("## 年度資料分析互動圖表", width=600),
                            pn.Spacer(width=50),
                            self.selector,
                            sizing_mode='stretch_width'
                            )

            # 圖表顯示區
            self.plot_pane = pn.pane.Plotly(height=800, width= 600, sizing_mode='stretch_width', # 自定畫布寬度
                                        config={'responsive': True}  # 開啟 Plotly 響應式功能
                                        )
            
            # 註冊 Callback（回呼函式）
            self.selector.param.watch(self.update_plot, 'value')  # 當 year_selector 的值，一旦變動就執行 update_plot()
            self.update_plot(None)  # 初始化一次

            # 包裝頁面
            # app = pn.Column("# 年度資料分析互動圖表", selector, plot_pane) # 預設
            app = pn.Column(header, self.plot_pane, sizing_mode='stretch_width') # 2025/06/24 選單改右

            # 匯出成 HTML（含互動功能）
            app.save(f'{self.file_save_part}{i}.html', embed=True)
            print(i)

    # 讀取折線圖資料
    def line_data(self):
        # 讀取資料
        line_df = self.responses_single_choice[['id','surveyed_in', 'coding_exp_years','country', 'salary', 'salary_group', 'job_title_group']]

        # 設定條件 salary_group = correct_info 、 job_title_group = Data-related。
        col = (line_df['salary_group'] == 'correct_info') & (line_df['job_title_group'] == 'Data-related')

        # 合併 salary_order
        line_df = line_df[col].merge(self.salary_order, left_on='salary', right_on='salary', how='left').rename(columns={'rank':'salary_rank'})

        # 合併 country_area
        line_df = line_df.merge(self.country_area[['country', 'gdp_group', 'area']], left_on='country', right_on='country', how='left')
        
        # 設定條件 gdp_group = ['高收入', '中高收入']
        line_df = line_df[line_df['gdp_group'].isin(['高收入', '中高收入'])]
        line_df = line_df.merge(self.coding_exp_years_order, left_on='coding_exp_years', right_on='coding_exp_years', how='left')

        # 建立中位數
        line_df_group = line_df[['rank', 'coding_exp_years', 'area', 'salary_mean']].groupby(['rank', 'coding_exp_years', 'area']).median().reset_index().rename(columns={'salary_mean':'salary_median'})
        
        # 展開資料
        line_df_group = line_df_group.pivot(index=['rank', 'coding_exp_years'], columns='area', values='salary_median').reset_index()

        return line_df_group

    # 折線圖 
    def go_scatter(self):
        line_df_group = self.line_data()

        data1 = go.Scatter(
            x = line_df_group['coding_exp_years'],
            y = line_df_group['Asia'],
            mode = "lines+markers+text",
            name = 'Asia',
            textposition = "top center",
            line = dict(width=3),
            text = line_df_group['Asia']
        )

        data2 = go.Scatter(
            x = line_df_group['coding_exp_years'],
            y = line_df_group['Europe'],
            mode = "lines+markers+text",
            name = 'Europe',
            textposition = "top center",
            line = dict(width=3),
            text = line_df_group['Europe']
        )

        data3 = go.Scatter(
            x = line_df_group['coding_exp_years'],
            y = line_df_group['North America'],
            mode = "lines+markers+text",
            name = 'North America',
            textposition = "top center",
            line = dict(width=3),
            text = line_df_group['North America']
        )

        data4 = go.Scatter(
            x = line_df_group['coding_exp_years'],
            y = line_df_group['Oceania'],
            mode = "lines+markers+text",
            name = 'Oceania',
            textposition = "top center",
            line = dict(width=3),
            text = line_df_group['Oceania']
        )

        data5 = go.Scatter(
            x = line_df_group['coding_exp_years'],
            y = line_df_group['South America'],
            mode = "lines+markers+text",
            name = 'South America',
            textposition = "top center",
            line = dict(width=3),
            text = line_df_group['South America']
        )

        layout = go.Layout(
            title = '薪資 & 經驗 & 洲別',
            title_font_size = 30,
            xaxis = dict(title='程式經驗 (年)', tickfont=dict(size=10)),
            yaxis = dict(title='年資(中位數)', tickfont=dict(size=10)),
            margin = dict(l=50, r=50, t=60, b=60),
            showlegend = True
        )

        fig = go.Figure(data = [data1, data2, data3, data4, data5], layout = layout)
        fig.write_html(f'{self.file_save_part}洲別_經驗_薪資.html', auto_open=True) 

    # 讀取氣泡圖資料
    def scatter_data(self):
        # 讀取資料
        scatter_df = self.responses_single_choice[['id','surveyed_in', 'coding_exp_years', 'job_title','country', 'salary', 'salary_group', 'job_title_group']]

        # 設定條件 salary_group = correct_info 、 job_title_group = Data-related。
        col = (scatter_df['salary_group'] == 'correct_info') & (scatter_df['job_title_group'] == 'Data-related')

        # 合併 salary_order
        scatter_df = scatter_df[col].merge(self.salary_order, left_on='salary', right_on='salary', how='left')

        # 合併 country_area
        scatter_df = scatter_df.merge(self.country_area[['country', 'gdp_group', 'area']], left_on='country', right_on='country', how='left')

        # 設定條件 gdp_group = ['高收入', '中高收入']
        scatter_df = scatter_df[scatter_df['gdp_group'].isin(['高收入', '中高收入'])]

        # 合併 coding_exp_years_order
        scatter_df = scatter_df.merge(self.coding_exp_years_order, left_on='coding_exp_years', right_on='coding_exp_years', how='left')

        # 合併 prog_lang_skill_group
        scatter_df = scatter_df.merge(self.prog_lang_skill_group, left_on='id', right_on='id', how='left')

        # 提取資料
        scatter_df = scatter_df[['id', 'salary','job_title','count', 'coding_exp_years_mean', 'salary_mean']]

        # 移除錯誤資料，正常的中高收入國家的年薪不應該低於 5000 美金，感覺應該要設定 10000 美金比較正確。
        scatter_df = scatter_df[scatter_df['salary_mean'] > 5000]

        # 建立 人數、技能數量(平均)、程式經驗年(平均)、年薪(中位數)。
        scatter_df = scatter_df.groupby(['job_title','salary']).agg(count = ('id', 'count'),
                                                                    lang_count_mean=('count', 'mean'),
                                                                    coding_exp_year_mean=('coding_exp_years_mean', 'mean'),
                                                                    salary_median=('salary_mean', 'median')
                                                                    ).round(2).reset_index()

        # 建立 文字顯示
        scatter_df['text'] = '經驗 = ' + scatter_df['coding_exp_year_mean'].astype(str) + ' year'

        return scatter_df

    # 氣泡圖 (年薪 & 技能(數量) & 職稱) 
    def px_scatter(self):
        scatter_df = self.scatter_data()
        fig = px.scatter(
                scatter_df,                       # 數據來源的 DataFrame
                x="lang_count_mean",              # 技能數量(平均)
                y="salary_median",                # 年薪(中位數)
                size="count",                     # 設定氣泡大小對應 人數
                color="job_title",                # 各職稱來區分顏色
                hover_name="text",                # 滑鼠懸停時顯示 程式經驗(平均)
                size_max=50,                      # 設定氣泡的最大大小
                range_x=[1.5, 5.5],               # 設定 x 軸的範圍
                range_y=[0, 200000],              # 設定 y 軸的範圍
                log_x=True                        # 以對數尺度顯示 x 軸，有助於處理資料密集區的壓縮與分布差異
            )

        fig.update_layout(title_text='年薪 & 技能(數量) & 職稱', 
                        title_font_size = 24,
                        xaxis=dict(
                            title=dict(text='學習程式語言數量 的平均'),
                            gridcolor='white',
                            type='log',
                            gridwidth=2,
                        ), 
                        yaxis_title=None) # 關閉 y 軸標籤
        fig.write_html(f'{self.file_save_part}年薪_技能(數量)_職稱.html', auto_open=True) # 儲存檔案

    def create_html(self):
        self.bar_pie()
        print('橫條圖_圓餅圖 pass')
        self.go_scatter()
        print('折線圖 pass')
        self.px_scatter()
        print('氣泡圖 pass')

file_path = "D:/data_scientists_toolbox/data/kaggle.db"
file_save_part = "D:/data_scientists_toolbox/"
test = SurveyVisualizer(file_path, file_save_part)
test.create_html()