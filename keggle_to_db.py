import pandas as pd
import sqlite3
import string

class CreateKaggleSurveyDB:
    def __init__(self, file_path):
        self.file_path = file_path
        survey_years = [2020, 2021, 2022]
        df_dict = dict()
        for year in survey_years:
            # read_csv 出現 DtypeWarning，你的 CSV 檔案中 某些欄位的數據類型不一致（mixed types）
            # 當 pandas 在載入 CSV 時，會嘗試根據前幾行的內容來推測每個欄位的數據類型 (dtype)，但如果一個欄位中 有不同類型的數據（例如某些行是數字、某些行是文字），就會觸發這個警告。
            # low_memory=False：讓 pandas 讀取整個檔案後，再判斷數據類型，而不是只根據部分數據來推測。
            df = pd.read_csv(f"{self.file_path}kaggle_survey_{year}_responses.csv", low_memory=False)
            # 讀取"回答資料"
            df_dict[year, "responses"] = df.iloc[1:, :]

            # 讀取"題目敘述"
            question_descriptions = df.iloc[0, :].values
            # 等等處裡資料會使用zip，所以事先將資料轉換成一維 (355,)。
            # 如果沒有做這個動作資料會是 (1, 355)，在使用zip 會出現錯誤。
            df_dict[year, "question_descriptions"] = question_descriptions

        self.df_dict = df_dict
        # 讀取對照表
        kaggle_question_reference_table = pd.read_csv(f"{file_path}kaggle_question_reference_table.csv", low_memory=False)
        kaggle_question_reference_table.columns
        # 找出單選欄位
        self.kaggle_question_reference_table = kaggle_question_reference_table

    def tid_data(self, survey_year):
        # 分割資料
        # ----------- 分割題目、題號處理 --------------
        column_names = self.df_dict[survey_year, "responses"].columns
        descriptions = self.df_dict[survey_year, "question_descriptions"]
        question_indexes, question_types, question_descriptions = [], [], []
        # 實際分割資料
        for column_name, question_description in zip(column_names, descriptions):
            # 分割 "題號資料"，共有 3 種資料型態 ( Q1、 Q7_Part_1、 Q35_B_Part_1 )。
            column_name_split = column_name.split("_")
            # 分割問題資料，資料型態 (問題 - Selected Choice -  回覆 )
            question_description_split = question_description.split(" - ")
            # 單選題_處理
            if len(column_name_split) == 1:
                question_index = column_name_split[0]
                question_indexes.append(question_index)
                question_types.append("Single Choice")
                question_descriptions.append(question_description_split[0])
            # 多選題_處理
            else:
                # 處理有大寫字母( Q35_B_Part_1 )資料。
                if column_name_split[1] in string.ascii_uppercase:
                    question_index = column_name_split[0] + column_name_split[1]
                    question_indexes.append(question_index)
                # 處理複選( Q7_Part_1 )資料。
                else:
                    question_index = column_name_split[0]
                    question_indexes.append(question_index)
                question_types.append("Multiple selection")
                question_descriptions.append(question_description_split[0])

        # 修改名稱
        for i, name in enumerate(question_indexes):
            con_1 = (name ==  self.kaggle_question_reference_table[str(survey_year)])
            if any(con_1):
                question_indexes[i] =  self.kaggle_question_reference_table[self.kaggle_question_reference_table[str(survey_year)] == question_indexes[i]]['col_eng'].values[0]

        question_df = pd.DataFrame()
        # 新增 "題號" 資料
        question_df["question_index"] = question_indexes
        # 新增 "單複選" 資料
        question_df["question_type"] = question_types
        # 新增 "問題敘述" 資料
        question_df["question_description"] = question_descriptions
        # 新增 "年份" 資料
        question_df["surveyed_in"] = survey_year

        question_df = question_df.groupby(["question_index", "question_type", "question_description", "surveyed_in"]).count().reset_index()
        
        # ----------- 單選 --------------
        response_df =  self.df_dict[survey_year, "responses"].copy()
        # 選取台灣資料
        # response_df = response_df[response_df['Q3'] == 'Taiwan']
        # 將分割好的 "題目資料" 導入，取代 "題目columns"。
        response_df.columns = question_indexes
        response_df = response_df.reset_index().rename(columns={"index": "response_id"})

        # 將共通題目為 "-" 填補為 None 值 
        name = self.kaggle_question_reference_table[~self.kaggle_question_reference_table['col_eng'].isin(response_df.columns)]['col_eng'].values
        response_df[name] = None
        
        # 回答年分
        response_df["surveyed_in"] = survey_year

        return question_df, response_df
    
    def safe_replace(self, df, mask, column, mapping):
        # 函式 response 資料標準化。
        df.loc[mask, column] = df.loc[mask, column].replace(mapping)
        return df

    def data_clean(self):
        # 建立 response 
        q_22 ,r_22  = self.tid_data(2022)
        q_21 ,r_21  = self.tid_data(2021)
        q_20 ,r_20  = self.tid_data(2020)

        # 建立主鍵（Primary Key），重設 id 用來唯一識別資料表中每一筆記錄的欄位或欄位組合。
        df_re_id = pd.concat([r_20[['response_id','surveyed_in']], r_21[['response_id','surveyed_in']], r_22[['response_id','surveyed_in']]], ignore_index=True)
        df_re_id = df_re_id.reset_index().rename(columns={"index": "id"})
        r_22 = r_22.merge(df_re_id, left_on=['response_id', 'surveyed_in'], right_on=['response_id', 'surveyed_in'], how='left').drop(columns = ['response_id', 'Duration (in seconds)'])
        r_21 = r_21.merge(df_re_id, left_on=['response_id', 'surveyed_in'], right_on=['response_id', 'surveyed_in'], how='left').drop(columns = ['response_id', 'Time from Start to Finish (seconds)'])
        r_20 = r_20.merge(df_re_id, left_on=['response_id', 'surveyed_in'], right_on=['response_id', 'surveyed_in'], how='left').drop(columns = ['response_id', 'Time from Start to Finish (seconds)'])

        # 將 "寬資料表" 轉為 "長資料表"
        r_22_df = pd.melt(r_22, id_vars=["id",'surveyed_in'], var_name="question_index", value_name="response")
        r_21_df = pd.melt(r_21, id_vars=["id",'surveyed_in'], var_name="question_index", value_name="response")
        r_20_df = pd.melt(r_20, id_vars=["id",'surveyed_in'], var_name="question_index", value_name="response")

        # 合併資料表
        response_df = pd.concat([r_20_df, r_21_df, r_22_df], ignore_index=True)
        question_df = pd.concat([q_22, q_21, q_20], ignore_index=True)

        # 清除NaN(空)的回覆資料
        response_df = response_df.dropna().reset_index(drop=True)

        # -------------------------- age(年齡) -------------------------- OK 無須修改
        # -------------------------- gender(性別) -------------------------- OK 無須修改
        # -------------------------- job_role(工作職責) -------------------------- OK 無須修改
        # -------------------------- company_size(公司規模) -------------------------- OK 無須修改
        # -------------------------- ds_team_size(DS 團隊規模) -------------------------- OK 無須修改
        # -------------------------- company_uses_ml(公司是否使用機器學習) -------------------------- OK 無須修改
        # -------------------------- prog_lang(使用的程式語言) -------------------------- OK 無須修改
        # -------------------------- ml_algo(常用 ML 演算法) -------------------------- OK 無須修改
        # -------------------------- cv_tech(常用 CV 技術：影像、照片) -------------------------- OK 無須修改
        # -------------------------- nlp_tech(常用 NLP 技術：自然語言) -------------------------- OK 無須修改
        # -------------------------- nlp_tech(常用 NLP 技術：自然語言) -------------------------- OK 無須修改
        # -------------------------- ml_exp(常用 NLP 技術：自然語言) -------------------------- OK 無須修改
        # -------------------------- tup_usage_count(使用TPU的次數) -------------------------- OK 無須修改
        # -------------------------- fav_ds_media(最愛的資料科學媒體來源) -------------------------- OK 無須修改
        # -------------------------- ds_course(資料科學課程平台) -------------------------- OK 無須修改
        # -------------------------- industry(產業) -------------------------- OK 無須修改
        # -------------------------- first_started_helpful(對第一次學習有幫助) -------------------------- OK 無須修改
        
        # -------------------------- country(國家) -------------------------- OK
        # 查看修改前的唯一值
        response_df.loc[response_df['question_index'] == 'country', 'response'].drop_duplicates().tolist()

        # 進行標準化
        mapping = {'United States of America':'USA',
                'United Kingdom of Great Britain and Northern Ireland':'UK',
                'Hong Kong (S.A.R.)':'Hong Kong',
                'Iran, Islamic Republic of...':'Iran',
                'Viet Nam':'Vietnam',
                'Republic of Korea':'South Korea'
                }
        response_df = self.safe_replace(response_df, response_df['question_index']=='country', 'response', mapping)

        # 查看修改後的唯一值（驗證修改結果）
        response_df.loc[response_df['question_index'] == 'country', 'response'].drop_duplicates().tolist()

        # education(學歷)
        response_df.loc[response_df['question_index'] == 'education', 'response'].drop_duplicates().tolist()

        mapping = {'Bachelor’s degree': 'Bachelor\'s degree',
                'Master’s degree': 'Master\'s degree',
                'Some college/university study without earning a bachelor’s degree': 'Some college, no degree',
                'No formal education past high school': 'High school or lower',
                'I prefer not to answer': 'Prefer not to answer'
                }

        response_df = self.safe_replace(response_df, response_df['question_index']=='education', 'response', mapping)

        # -------------------------- salary(年薪) -------------------------- OK
        # 備註：之後要建立 salary_rank、salary_mean。
        response_df.loc[response_df['question_index'] == 'salary', 'response'].drop_duplicates()

        mapping = {'$0-999': '0-999',
                '300,000-500,000':'300,000-499,999',
                '$500,000-999,999':'500,000-999,999',
                '> $500,000':'1,000,000',
                '>$1,000,000':'1,000,000'
                }

        response_df = self.safe_replace(response_df, response_df['question_index']=='salary', 'response', mapping)

        # -------------------------- job_title(職稱) -------------------------- OK

        # 處理2022年資料 - 找到 2022 職稱 id
        job_id_list = response_df.loc[(response_df['question_index'] == 'job_title') & (response_df['surveyed_in'] == 2022), 'id'].drop_duplicates()

        # 處理2022年資料 - 找到 2022 學生資料
        study_df = response_df[(response_df['question_index'] == 'Q5') & (response_df['response'] == 'Yes') & (response_df['surveyed_in'] == 2022)]

        # 處理2022年資料 - 找到 無職業 且是 學生 的人: 發現全無職業，直接修改 question_index、response。
        study_df = study_df[~study_df['id'].isin(job_id_list)].replace({'Q5':'job_title', 'Yes':'Student'})

        # 處理2022年資料 - 合併將 2022年的 Q5 合併到 job_title
        mask = (response_df['question_index'] == 'Q5') & (response_df['response'] == 'Yes') & (response_df['surveyed_in'] == 2022)
        response_df[mask] = response_df[mask].replace({'Q5':'job_title', 'Yes':'Student'})

        # 標準化
        response_df.loc[response_df['question_index'] == 'job_title', 'response'].drop_duplicates()

        mapping = {'Product Manager':'Product/Project Manager',
                'Data Analyst (Business, Marketing, Financial, Quantitative, etc)':'Data Analyst',
                'Developer Relations/Advocacy':'Developer Advocate',
                'Machine Learning/ MLops Engineer':'Machine Learning Engineer',
                'Manager (Program, Project, Operations, Executive-level, etc)':'Product/Project Manager'}

        response_df = self.safe_replace(response_df, response_df['question_index']=='job_title', 'response', mapping)

        # -------------------------- ide_tool(使用 IDE) -------------------------- OK
        response_df.loc[response_df['question_index'] == 'ide_tool', 'response'].drop_duplicates().tolist()

        # 標準化：資料一堆空白
        mapping = {'Jupyter (JupyterLab, Jupyter Notebooks, etc) ':'Jupyter Notebook', 
                ' RStudio ':'RStudio', 
                ' PyCharm ':'PyCharm', 
                '  Spyder  ':'Spyder', 
                '  Notepad++  ':'Notepad++', 
                '  Sublime Text  ':'Sublime Text', 
                '  Vim / Emacs  ':'Vim / Emacs', 
                ' MATLAB ':'MATLAB', 
                ' Visual Studio ':'Visual Studio', 
                ' Visual Studio Code (VSCode) ':'Visual Studio Code (VSCode)', 
                ' Jupyter Notebook':'Jupyter Notebook', 
                'JupyterLab ':'JupyterLab'}

        response_df = self.safe_replace(response_df, response_df['question_index']=='ide_tool', 'response', mapping)

        # -------------------------- visualization(使用視覺化函數) -------------------------- OK
        response_df.loc[response_df['question_index'] == 'visualization', 'response'].drop_duplicates().tolist()
        # 標準化：資料一堆空白
        mapping = {' Matplotlib ':'Matplotlib',
                ' Seaborn ':'Seaborn',
                ' Plotly / Plotly Express ':'Plotly / Plotly Express',
                ' Ggplot / ggplot2 ':'Ggplot / ggplot2',
                ' Shiny ':'Shiny',
                ' D3 js ':'D3 js',
                ' Altair ':'Altair',
                ' Bokeh ':'Bokeh',
                ' Geoplotlib ':'Geoplotlib',
                ' Leaflet / Folium ':'Leaflet / Folium',
                ' Pygal ':'Pygal',
                ' Dygraphs ':'Dygraphs',
                ' Highcharter ':'Highcharter'}

        response_df = self.safe_replace(response_df, response_df['question_index']=='visualization', 'response', mapping)

        # -------------------------- ml_framework(ML 框架使用情況) -------------------------- OK
        response_df.loc[response_df['question_index'] == 'ml_framework', 'response'].drop_duplicates().tolist()
        # 標準化：資料一堆空白
        mapping = {'  Scikit-learn ':'Scikit-learn',
                '  TensorFlow ':'TensorFlow',
                ' Keras ':'Keras',
                ' PyTorch ':'PyTorch',
                ' Fast.ai ':'Fast.ai',
                ' MXNet ':'MXNet',
                ' Xgboost ':'Xgboost',
                ' LightGBM ':'LightGBM',
                ' CatBoost ':'CatBoost',
                ' Prophet ':'Prophet',
                ' H2O 3 ':'H2O 3',
                ' Caret ':'Caret',
                ' Tidymodels ':'Tidymodels',
                ' JAX ':'JAX',
                ' PyTorch Lightning ':'PyTorch Lightning',
                ' Huggingface ':'Huggingface'}

        response_df = self.safe_replace(response_df, response_df['question_index']=='ml_framework', 'response', mapping)

        # -------------------------- coding_exp_years(程式經驗(年)) -------------------------- OK
        response_df.loc[response_df['question_index'] == 'coding_exp_years', 'response'].drop_duplicates().tolist()

        # 標準化
        mapping = {'1-2 years':'1-3 years'}
        response_df = self.safe_replace(response_df, response_df['question_index']=='coding_exp_years', 'response', mapping)

        # -------------------------- 建立 responses_single_choice_group -------------------------- OK
        # 抓單選
        single_choice_list = self.kaggle_question_reference_table.loc[self.kaggle_question_reference_table['question_type'] == 'S', 'col_eng'].tolist()

        # 抓取全部 id, surveyed_in 為基礎資料
        responses_single_choice_group = response_df[['id', 'surveyed_in']].drop_duplicates().copy()

        for i in single_choice_list:
            responses_single_choice_group = responses_single_choice_group.merge(response_df.loc[response_df['question_index'] == i,['id', 'response']].rename(columns={'response':i}), left_on='id', right_on='id', how='left')

        # 建立 job_title_group
        data_related = ['Business Analyst', 'DBA/Database Engineer', 'Data Administrator', 'Data Analyst', 'Data Architect', 'Data Engineer', 'Data Scientist', 'Software Engineer']
        responses_single_choice_group['job_title_group'] = responses_single_choice_group.apply(lambda row: 'Data-related' if row['job_title'] in data_related else 'Exclude', axis=1)

        self.response_df =  response_df
        self.question_df =  question_df
        self.responses_single_choice_group = responses_single_choice_group
        print('data_clean pass')

    def prog_lang_skill_group_table(self):
        # 抓取全部 id, surveyed_in 為基礎資料
        prog_lang_skill_group = self.response_df[['id', 'surveyed_in']].drop_duplicates().reset_index(drop=True).copy()

        # 建立 prog_lang_skill_group
        prog_lang_df= self.response_df[self.response_df['question_index'] == 'prog_lang'].copy()
        prog_lang_df['count'] = 1
        prog_lang_df = prog_lang_df.pivot(index='id', columns='response', values='count').reset_index()

        # 合併資料表
        prog_lang_skill_group = prog_lang_skill_group.merge(prog_lang_df, left_on='id', right_on='id', how='left').fillna(0).astype(int)
        prog_lang_skill_group['count'] = prog_lang_skill_group.iloc[:,2:].sum(axis=1).astype(int)
        prog_lang_skill_group['Python_SQL_group'] = prog_lang_skill_group.apply(lambda x: 1 if (x['Python'] == 1) & (x['SQL'] == 1)  else 0, axis=1)
        prog_lang_skill_group['R_SQL_group'] = prog_lang_skill_group.apply(lambda x: 1 if (x['R'] == 1) & (x['SQL'] == 1)  else 0, axis=1)
        prog_lang_skill_group['Python_R_SQL_group'] = prog_lang_skill_group.apply(lambda x: 1 if (x['Python'] == 1) & (x['SQL'] == 1) & (x['R'] == 1) else 0, axis=1)
        
        self.prog_lang_skill_group = prog_lang_skill_group
        print('prog_lang_skill_group_table pass')

    def salary_order_table(self):
        salary_order = self.responses_single_choice_group['salary'].drop_duplicates().dropna()
        salary_mean = salary_order.str.replace(',','').str.split('-',expand=True).fillna('1000000').replace({',':""}).astype(int).mean(axis=1).rename('salary_mean')

        salary_order = pd.concat([salary_order, salary_mean], axis=1)
        salary_order = salary_order.sort_values('salary_mean').reset_index(drop=True).reset_index().rename(columns={'index':'rank'})

        self.salary_order = salary_order
        print('salary_order_table pass')

    def coding_exp_years_order_table(self):
        coding_exp_years_order = self.responses_single_choice_group['coding_exp_years'].drop_duplicates().dropna()
        year = coding_exp_years_order.str.replace(r'[^\d\.\-]+', '', regex=True).apply(lambda x: (int(x.split('-')[0])+int(x.split('-')[1]))/2 if len(x.split('-')) == 2  
                                                                                else (0 if x.split('-')[0] == '' else int(x.split('-')[0])))

        coding_exp_years_order = pd.DataFrame({'coding_exp_years': coding_exp_years_order})
        coding_exp_years_order['coding_exp_years_mean'] = year
        coding_exp_years_order['rank'] = coding_exp_years_order['coding_exp_years_mean'].rank().astype(int)
        self.coding_exp_years_order = coding_exp_years_order.reset_index(drop=True)
        print('coding_exp_years_order_table pass')

    def country_area_gdp_table(self):
        country_area = self.responses_single_choice_group['country'].drop_duplicates().reset_index(drop=True)
        country_area = pd.DataFrame({'country':country_area})
        # 建立州別 gpd_group(年分、GDP)、area(國家名稱、地區)
        # 資料來源：Gapminder，https://www.gapminder.org/data/，關鍵字 https://www.gapminder.org/data/
        # 檔案名稱：ddf--datapoints--gdp_pcap--by--country--time.csv、ddf--entities--geo--country.csv
        gpd = pd.read_csv(f'{self.file_path}ddf--datapoints--gdp_pcap--by--country--time.csv')
        area = pd.read_csv(f'{self.file_path}ddf--entities--geo--country.csv')
        country = pd.read_csv(f'{self.file_path}country_area.csv', low_memory=False , encoding='big5') # 這個資料是依靠GPT補齊的、翻譯也是。
        country_area = country_area.merge(country[['country', 'area', '國家']], right_on='country', left_on='country', how='left')
        # 檢查缺失資料
        # country_area[country_area.isna().any(axis=1)]

        # 取 2022年資料，因為問卷位於2022年。
        gpd = gpd[gpd['time'].isin([2022,2023])]
        # 提取國家縮寫、名稱、地區。
        area = area[['country', 'name']]
        gpd_area = gpd.merge(area, left_on='country', right_on='country', how='left')
        # 長轉寬
        gpd_area = gpd_area.pivot(index=['country', 'name'], columns='time', values='gdp_pcap').reset_index()

        # 標準化 country 名稱
        # country_area.loc[~country_area['country'].isin(gpd_area['name']), 'country'].values # 檢查缺少國家。
        # gpd_area.loc[~gpd_area['name'].isin(country_area['country']), 'name'].values # 找出名稱不符合的國家。
        mapping = {'Hong Kong, China':'Hong Kong',
                   'UAE':'United Arab Emirates'}
        gpd_area['name'] = gpd_area['name'].replace(mapping)
        gpd_area = gpd_area.iloc[:,1:].rename(columns={'name':'country'})
        # 合併 gpd_area
        country_area = country_area.merge(gpd_area, left_on='country', right_on='country', how='left')
        # 建立 gpd_group
        country_area['gdp_group'] = country_area.apply(lambda x: '低收入' if x[2023] < 10000
                                                                else ('中低收入' if x[2023] < 25000
                                                                else ('中高收入' if x[2023] < 50000
                                                                else ('高收入' if x[2023] > 50000
                                                                else 'Unknown'))), axis=1)
        # 修改欄位名稱
        country_area = country_area.rename(columns={2022:'gpd_2022', 2023:'gpd_2023'})

        # 檢查缺失直
        # country_area[country_area.isna().any(axis=1)]

        self.country_area = country_area
        print('country_area_gdp_table pass')

    def minimum_wage(self):
        country_area = self.country_area

        minimum_wage = pd.read_csv(f'{file_path}EAR_4MMN_CUR_NB_A-20250529T0752.csv', low_memory=False )
        minimum_wage = minimum_wage[minimum_wage['time'] >= 2022][['ref_area.label', 'time', 'classif1.label', 'obs_value', 'note_indicator.label']]
        minimum_wage = minimum_wage[minimum_wage['classif1.label'] == 'Currency: Local currency']
        # 檢查資料數量
        # minimum_wage[minimum_wage['time']==2024].count() # 170
        # minimum_wage[minimum_wage['time']==2023].count() # 169
        # minimum_wage[minimum_wage['time']==2022].count() # 172

        # 分割欄位貨幣
        currency_unit = minimum_wage['note_indicator.label'].str.split(" ")

        # 提取貨幣單位
        currency_unit_list = []
        for i in currency_unit:
            for j in i:
                if j[0] == '(' and len(j) < 6:
                    # 資料不只 貨幣代碼 還有 ((unskilled、(manufacturing)...etc，所以只提取長小於6的資料)
                    currency_unit_list.append(j)
        minimum_wage['currency_unit'] = currency_unit_list

        # 移除()號
        minimum_wage['currency_unit'] = minimum_wage['currency_unit'].apply(lambda x: x.replace('(','').replace(')',''))

        # 刪除特定列(columns)
        minimum_wage = minimum_wage.drop(minimum_wage.columns[[2,4]], axis=1)

        # 修改欄位名稱
        minimum_wage = minimum_wage.rename(columns={'ref_area.label':'country','time':'year'})

        # 長轉寬
        minimum_wage = minimum_wage.pivot(index=['country', 'currency_unit'], columns='year', values='obs_value').reset_index()

        # 標準化 - 國家名稱
        country_area.loc[~country_area['country'].isin(minimum_wage['country']), 'country'].values # 檢查缺少國家。
        minimum_wage.loc[~minimum_wage['country'].isin(country_area['country']), 'country'].values # 找出名稱不符合的國家。
        mapping = {'Czechia':'Czech Republic'
                ,'Hong Kong, China':'Hong Kong'
                ,'Iran (Islamic Republic of)':'Iran'
                ,'Republic of Korea':'South Korea'
                ,'Russian Federation':'Russia'
                ,'Taiwan, China':'Taiwan'
                ,'Türkiye':'Turkey'
                ,'United Kingdom of Great Britain and Northern Ireland':'UK'
                ,'United States of America':'USA'
                ,'Viet Nam':'Vietnam'}
        minimum_wage['country'] = minimum_wage['country'].replace(mapping)

        # 檢查缺少國家。
        country_area.loc[~country_area['country'].isin(minimum_wage['country']), 'country'].values 
        '''這些國家並無最低薪資，之後需要補貨幣單位。
        ['Singapore', 'Italy', 'United Arab Emirates', 'Sweden', 'Austria', 'Denmark', 'Ethiopia', 'Norway']
        '''

        # 合併 minimum_wage
        country_area = country_area.merge(minimum_wage, left_on='country', right_on='country', how='left')
        # 檢查缺失直：minimum_wage 目前還缺少國家 ['Singapore', 'Italy', 'United Arab Emirates', 'Sweden', 'Austria', 'Denmark', 'Ethiopia', 'Norway']
        country_area[country_area['currency_unit'].isna()]

        # 補幣別：因為 minimum_wage 並無部分國家資料，所以需要自己補齊資料。 這一步其實可以不用作因為他們並無基礎薪資的資料，所以也無法轉換資料。
        currency_unit_list = {'Singapore':'SGD', 
                            'Italy':'EUR', 
                            'United Arab Emirates':'AED', 
                            'Sweden':'SEK', 
                            'Austria':'EUR', 
                            'Denmark':'DKK', 
                            'Ethiopia':'ETB', 
                            'Norway':'NOK'
                            }
        country_area.loc[country_area[['currency_unit']].isna().any(axis=1),'currency_unit'] = country_area.loc[country_area[['currency_unit']].isna().any(axis=1),'country'].map(currency_unit_list)

        # 檢查是否補完缺失資料
        # country_area[country_area['currency_unit'].isna()]

        # 加入匯率、月薪、基礎年薪。
        # 2022 年 12 月最後一週匯率對照表（以每 1 美元等於多少該國貨幣 → 取倒數換算）
        exchange_rate_dict_2022 = {
            'USD': 1,
            'EUR': 1 / 0.9398,
            'JPY': 1 / 132.65,
            'CNY': 1 / 6.986,
            'TWD': 1 / 30.65,
            'KRW': 1 / 1301.61,
            'GBP': 1 / 0.83,
            'AUD': 1 / 1.47,
            'CAD': 1 / 1.36,
            'BRL': 1 / 5.2365,
            'INR': 1 / 82.46,
            'MXN': 1 / 19.797,
            'ZAR': 1 / 17.34,
            'TRY': 1 / 18.7,
            'RUB': 1 / 70.0,
            'HKD': 1 / 7.7852,
            'SGD': 1 / 1.3505,
            'MYR': 1 / 4.4004,
            'THB': 1 / 34.5,
            'PHP': 1 / 55.0,
            'VND': 1 / 23600.0,
            'EGP': 1 / 24.7,
            'SEK': 1 / 10.46,
            'NOK': 1 / 9.86,
            'DKK': 1 / 7.0,
            'PLN': 1 / 4.39,
            'CZK': 1 / 23.85,
            'HUF': 1 / 391.5,
            'ILS': 1 / 3.52,
            'CLP': 1 / 869.75,
            'COP': 1 / 4873.5,
            'RON': 1 / 4.64,
            'TND': 1 / 3.12,
            'PEN': 1 / 3.81,
            'KZT': 1 / 464.0,
            'ARS': 1 / 177.13,
            'BDT': 1 / 104.2,
            'PKR': 1 / 225.4,
            'NGN': 1 / 448.55,
            'IRR': 1 / 42000.0,
            'IQD': 1 / 1459.5,
            'MAD': 1 / 10.22,
            'UAH': 1 / 36.94,
            'KES': 1 / 123.6,
            'UGX': 1 / 3700.0,
            'ETB': 1 / 53.2,
            'GHS': 1 / 9.0,
            'ZWL': 1 / 654.1,
            'SAR': 1 / 3.75,
            'AED': 1 / 3.6725,
            'CHF': 1 / 0.923,
            'BHD': 1 / 0.377,
            'DZD': 1 / 138.5,
            'LKR': 1 / 366.7,
            'BYN': 1 / 2.52,
            'XAF': 0.0016,
            'INR': 0.012,
            'NPR': 0.0075,
            'IDR': 0.000064
        }
        # 補上匯率並計算最低工資（以 2022 為基礎）
        country_area['usd_exchange_rate'] = country_area['currency_unit'].map(exchange_rate_dict_2022)
        # 檢查是否有缺失直
        # country_area[country_area['usd_exchange_rate'].isna()]

        # 月薪 轉 美元
        country_area['minimum_wage_in_usd'] = country_area[2022] * country_area['usd_exchange_rate']
        # 年薪
        country_area['annual_salary'] = country_area['minimum_wage_in_usd'] * 12

        # 檢查缺失值
        # country_area[country_area.isna().any(axis=1)]

        # 這些國家採用的機制不相同，所以沒有制定最低薪資，因此使用鄰近的 area & gpd 的國家 平均值來補充 最低薪資。
        # 補缺失值 - 最低所得
        miss_values = country_area.loc[(country_area['annual_salary'].isna()) & ~(country_area['area'].isna()),['country', 'area', 'gpd_2023', 'gdp_group']]

        # 修改成以gpd_group為主。
        for i in range(len(miss_values)):
            country_df = country_area['country'] == miss_values.iloc[i]['country']
            area_df = country_area['area'] == miss_values.iloc[i]['area']
            gpd_df = country_area['gdp_group'] == miss_values.iloc[i]['gdp_group']
            if len(country_area.loc[area_df & gpd_df & ~country_area['annual_salary'].isna(), 'annual_salary']) > 0:
                annual_salary_mean = country_area.loc[area_df & gpd_df & ~country_area['annual_salary'].isna(), 'annual_salary'].mean()
            else :
                annual_salary_mean = country_area.loc[gpd_df & ~country_area['annual_salary'].isna(), 'annual_salary'].mean()
            country_area.loc[country_df, 'annual_salary'] = annual_salary_mean

        self.country_area = country_area

        print('minimum_wage pass')

    def salary_group(self):
        # 最後一步，建立 salary_group
        salary_group = self.responses_single_choice_group[['id', 'country', 'coding_exp_years','salary']].copy()
        # 合併 country_area，確認最低年薪數值。
        salary_group = salary_group.merge(self.country_area[['country', 'annual_salary']], left_on='country', right_on='country', how='left')
        # 合併 salary_order，將文字轉數字。
        salary_group = salary_group.merge(self.salary_order[['salary', 'salary_mean']], left_on='salary', right_on='salary', how='left')
        # 合併 coding_exp_years_order，確認年資
        salary_group = salary_group.merge(self.coding_exp_years_order.iloc[:-1], left_on='coding_exp_years', right_on='coding_exp_years', how='left')
        # 發現不知道為什麼合併後 coding_exp_years 中的 'I have never written code'，'coding_exp_years_mean' 變成 NaN，需要補為 0。
        salary_group.loc[salary_group['coding_exp_years_mean'].isna(),'coding_exp_years_mean'] = 0
        # 建立欄位 salary_group
        salary_group['salary_group'] = 'correct_info' 
        # salary_mean = NaN 為 無效資料(wrong_info)
        salary_group.loc[salary_group['salary_mean'].isna(),'salary_group'] = 'wrong_info'
        # salary_mean = NaN ， 小於 annual_salary * 0.9 為 無效資料(wrong_info)
        salary_group.loc[salary_group['salary_mean'] < (salary_group['annual_salary'] *  0.9) ,'salary_group'] = 'wrong_info'
        # coding_exp_years_mean < 3 且 salary_mean >  annual_salary * 2 為 無效資料(wrong_info)
        salary_group.loc[(salary_group['salary_mean'] > (salary_group['annual_salary'] *  2.5)) &
                        (salary_group['coding_exp_years_mean'] < 3 ),'salary_group'] = 'wrong_info'
        salary_group.groupby('salary_group').count() 
        # 重新清理的資料從原本的  
        # correct_info 16233 > 18748(錯誤) > 19571
        # wrong_info 53773 > 51258(錯誤) > 48765

        # 合併 responses_single_choice_group
        self.responses_single_choice_group = self.responses_single_choice_group.merge(salary_group[['id', 'salary_group']], left_on='id', right_on='id', how='left')
        print('salary_group pass')

    def create_database(self):
        self.data_clean()
        self.prog_lang_skill_group_table()
        self.salary_order_table()
        self.coding_exp_years_order_table()
        self.country_area_gdp_table()
        self.minimum_wage()
        self.salary_group()

        # 建立 kaggle.db
        connection = sqlite3.connect(f"{self.file_path}kaggle.db")
        self.kaggle_question_reference_table.to_sql("kaggle_question_reference_table", con=connection, if_exists="replace", index=False)
        self.response_df.to_sql("response_df", con=connection, if_exists="replace", index=False)
        self.question_df.to_sql("question_df", con=connection, if_exists="replace", index=False)
        self.responses_single_choice_group.to_sql("responses_single_choice_group", con=connection, if_exists="replace", index=False)
        self.prog_lang_skill_group.to_sql("prog_lang_skill_group", con=connection, if_exists="replace", index=False)
        self.salary_order.to_sql("salary_order", con=connection, if_exists="replace", index=False)
        self.coding_exp_years_order.to_sql("coding_exp_years_order", con=connection, if_exists="replace", index=False)
        self.country_area.to_sql("country_area", con=connection, if_exists="replace", index=False)

        return self.response_df, self.question_df, self.responses_single_choice_group, self.prog_lang_skill_group, self.salary_order, self.coding_exp_years_order, self.country_area

file_path = 'data_scientists_toolbox/data/'
df_db = CreateKaggleSurveyDB(file_path)

response_df, question_df, responses_single_choice_group, prog_lang_skill_group, salary_order, coding_exp_years_order, country_area_df = df_db.create_database()


