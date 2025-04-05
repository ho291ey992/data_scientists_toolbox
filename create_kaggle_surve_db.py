import pandas as pd
import sqlite3
import string

# ---------------------- part_1 將資料匯入 dict 中 --------------------------
class CreateKaggleSurveyDB:
    def __init__(self):
        self.survey_years = [2020, 2021, 2022]
        df_dict = dict()
        for year in self.survey_years:
            # read_csv 出現 DtypeWarning，你的 CSV 檔案中 某些欄位的數據類型不一致（mixed types）
            # 當 pandas 在載入 CSV 時，會嘗試根據前幾行的內容來推測每個欄位的數據類型 (dtype)，但如果一個欄位中 有不同類型的數據（例如某些行是數字、某些行是文字），就會觸發這個警告。
            # low_memory=False：讓 pandas 讀取整個檔案後，再判斷數據類型，而不是只根據部分數據來推測。
            df = pd.read_csv(f"資料分析的七個練習專案_累積個人作品集/練習專案三：資料科學家的工具箱/data_scientists_toolbox/data/kaggle_survey_{year}_responses.csv", low_memory=False)
            # 讀取"回答資料"
            df_dict[year, "responses"] = df.iloc[1:, :]

            # 讀取"題目敘述"
            question_descriptions = df.iloc[0, :].values
            # 等等處裡資料會使用zip，所以事先將資料轉換成一維 (355,)。
            # 如果沒有做這個動作資料會是 (1, 355)，在使用zip 會出現錯誤。
            df_dict[year, "question_descriptions"] = question_descriptions
        self.df_dict = df_dict

    def tidy_2020_2021_data(self, survey_year: int) -> tuple:
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
        question_df = pd.DataFrame()
        # 新增 "題號" 資料
        question_df["question_index"] = question_indexes
        # 新增 "單複選" 資料
        question_df["question_type"] = question_types
        # 新增 "問題敘述" 資料
        question_df["question_description"] = question_descriptions
        # 新增 "年份" 資料
        question_df["surveyed_in"] = survey_year
        # 移除重複資料
        question_df = question_df.groupby(["question_index", "question_type", "question_description", "surveyed_in"]).count().reset_index()
        
        # ----------- 回覆資料處理 寬資料_轉_長資料--------------
        response_df = self.df_dict[survey_year, "responses"]

        # 選取台灣資料
        # response_df = response_df[response_df['Q3'] == 'Taiwan']

        # 將分割好的 "題目資料" 導入，取代 "題目columns"。
        response_df.columns = question_indexes
        response_df_reset_index = response_df.reset_index()
        # 將 "寬資料表" 轉為 "長資料表"
        response_df_melted = pd.melt(response_df_reset_index, id_vars="index", var_name="question_index", value_name="response")

        # 回答年分
        response_df_melted["responded_in"] = survey_year
        response_df_melted = response_df_melted.rename(columns={"index": "respondent_id"})

        # 清除NaN(空)的回覆資料
        response_df_melted = response_df_melted.dropna().reset_index(drop=True)
        return question_df, response_df_melted

    def tidy_2022_data(self, survey_year: int) -> tuple:
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
                # 處理複選( Q7_Part_1 )資料。
                question_index = column_name_split[0]
                question_indexes.append(question_index)
                question_types.append("Multiple selection")
                question_descriptions.append(question_description_split[0])
        question_df = pd.DataFrame()
        # 新增 "題號" 資料
        question_df["question_index"] = question_indexes
        # 新增 "單複選" 資料
        question_df["question_type"] = question_types
        # 新增 "問題敘述" 資料
        question_df["question_description"] = question_descriptions
        # 新增 "年份" 資料
        question_df["surveyed_in"] = survey_year
        # 移除重複資料
        question_df = question_df.groupby(["question_index", "question_type", "question_description", "surveyed_in"]).count().reset_index()
        
        # ----------- 回覆資料處理 寬資料_轉_長資料--------------
        response_df = self.df_dict[survey_year, "responses"]

        # 選取台灣資料
        # response_df = response_df[response_df['Q4'] == 'Taiwan']

        # 將分割好的 "題目資料" 導入，取代 "題目columns"。
        response_df.columns = question_indexes
        response_df_reset_index = response_df.reset_index()
        # 將 "寬資料表" 轉為 "長資料表"
        response_df_melted = pd.melt(response_df_reset_index, id_vars="index", var_name="question_index", value_name="response")

        # 回答年分
        response_df_melted["responded_in"] = survey_year
        response_df_melted = response_df_melted.rename(columns={"index": "respondent_id"})

        # 清除NaN(空)的回覆資料
        response_df_melted = response_df_melted.dropna().reset_index(drop=True)
        return question_df, response_df_melted

    def create_database(self):
        question_df = pd.DataFrame()
        response_df = pd.DataFrame()
        for year in self.survey_years:
            if year == 2022:
                q_df, r_df = self.tidy_2022_data(year)
            else :
                q_df, r_df = self.tidy_2020_2021_data(year)
            question_df = pd.concat([question_df, q_df], ignore_index=True)
            response_df = pd.concat([response_df, r_df], ignore_index=True)

        # 建立 SQL DB檔
        # 全部資料
        connection = sqlite3.connect("資料分析的七個練習專案_累積個人作品集/練習專案三：資料科學家的工具箱/data_scientists_toolbox/data/kaggle_survey.db")
        # 台灣資料
        # connection = sqlite3.connect("資料分析的七個練習專案_累積個人作品集/練習專案三：資料科學家的工具箱/data_scientists_toolbox/data/kaggle_survey_taiwan.db")
        question_df.to_sql("questions", con=connection, if_exists="replace", index=False)
        response_df.to_sql("responses", con=connection, if_exists="replace", index=False)
        cur = connection.cursor()
        drop_view_sql = """
        drop view if exists aggregated_responses;
        """

        create_view_sql = """
        create view aggregated_responses as
        
        select q.surveyed_in,
               q.question_index,
               q.question_type,
               q.question_description,
               r.response,
               count(r.response) as response_count
          from questions q
          join responses r
            on q.surveyed_in = r.responded_in and
               q.question_index = r.question_index
         group by q.surveyed_in,
                  q.question_description,
                  r.response;
        """
        cur.execute(drop_view_sql)
        cur.execute(create_view_sql)
        connection.close()

create_kaggle_survey_db = CreateKaggleSurveyDB()
create_kaggle_survey_db.create_database()


# ---------------------- 備註 ----------------------------

# 這種 dict 的 key 使用方法是叫 "元祖"
[(2020, 'responses'), 
 (2020, 'question_descriptions'), 
 (2021, 'responses'), 
 (2021, 'question_descriptions'), 
 (2022, 'responses'), 
 (2022, 'question_descriptions')]
# Python 字典的 key 必須是 不可變 (immutable) 的對象，例如： ✅ int, str, tuple, bool 可以當 key
# ❌ list, dict, set 不能當 key（因為它們是可變的）
# 元組 (2020, "responses") 是 不可變 (immutable)，所以可以作為 key。

# 在分割資料時出現I/O 堵塞問題，最後我決定在程式碼後加上 ";" ,直接完中斷完成程式碼。
# question_description_split[0]

# 查看資料
# for (year, dtype), df in df_dict.items():
#     if dtype == "responses":
#         print(f"Year: {year}, Type: {dtype}, Shape: {df.shape}")
#         print(df.head(1))
#     else :
#         print(f"Year: {year}, Type: {dtype}, Shape: {df.shape}")
#         print(df[1]);

'''
Year: 2020, Type: responses, Shape: (20036, 355)
Year: 2020, Type: question_descriptions, Shape: (355,)
Year: 2021, Type: responses, Shape: (25973, 369)
Year: 2021, Type: question_descriptions, Shape: (369,)
Year: 2022, Type: responses, Shape: (23997, 296)
Year: 2022, Type: question_descriptions, Shape: (296,)
'''
