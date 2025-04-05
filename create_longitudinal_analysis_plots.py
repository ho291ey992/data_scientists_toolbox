import pandas as pd
import sqlite3
import matplotlib.pyplot as plt

def plot_horizontal_bars(sql_query: str, fig_name: str, shareyaxis: bool=False):
    # 讀取資料
    connection = sqlite3.connect('資料分析的七個練習專案_累積個人作品集/練習專案三：資料科學家的工具箱/data_scientists_toolbox/data/kaggle_survey.db')
    response_counts = pd.read_sql(sql_query, con=connection)
    connection.close()

    # 建立三個水平畫布
    fig, axes = plt.subplots(ncols=3, figsize=(32, 8), sharey=shareyaxis)
        # sharey： True：若是列名稱相同，只顯示axes[0]的就好。

    # 分別建立個年分橫條圖
    survey_years = [2020, 2021, 2022]
    # 為方便控制畫布axes[0]、axes[1]、axes[2]，所以迴圈使用 len(survey_years) 來控制。
    for i in range(len(survey_years)):
        survey_year = survey_years[i]
        response_counts_year = response_counts[response_counts["surveyed_in"] == survey_year]
        y = response_counts_year["response"].values
        width = response_counts_year["response_count"].values
        axes[i].barh(y ,width)
        axes[i].set_title(f"{survey_year}")
    plt.tight_layout()
    fig.savefig(f"資料分析的七個練習專案_累積個人作品集/練習專案三：資料科學家的工具箱/data_scientists_toolbox/{fig_name}.png")

# 1.從事資料科學工作的職缺抬頭（title）有哪些？
'''Select the title most similar to your current role.
2020: Q5
2021: Q5
2022: Q23
'''
sql_query = '''
select surveyed_in ,
	   question_type ,
	   response ,
	   response_count 
 from aggregated_responses
 where (surveyed_in < 2022 and question_index = 'Q5') or
 	   (surveyed_in = 2022 and question_index = 'Q23')
 order by surveyed_in ,
 		  response_count;
'''
plot_horizontal_bars(sql_query, 'data_science_job_titles')

# 2.從事資料科學工作的日常內容是什麼？
'''Select any activities that make up an important part of your role at work.
2020: Q23
2021: Q24
2022: Q28
'''
sql_query = '''
select surveyed_in ,
	   question_type ,
	   response ,
	   response_count 
 from aggregated_responses
 where (surveyed_in = 2020 and question_index = 'Q23') or
 	   (surveyed_in = 2021 and question_index = 'Q24') or
 	   (surveyed_in = 2022 and question_index = 'Q28')
 order by surveyed_in ,
 		  response_count;
'''
plot_horizontal_bars(sql_query, "data_science_job_tasks", shareyaxis=True)

# 3 想要從事資料科學工作，需要具備哪些技能與知識？（程式語言）
'''What programming languages do you use on a regular basis?
2020: Q7
2021: Q7
2022: Q12
'''
sql_query = '''
select surveyed_in ,
	   question_type ,
	   response ,
	   response_count 
 from aggregated_responses
 where (surveyed_in < 2022 and question_index = 'Q7') or
 	   (surveyed_in = 2022 and question_index = 'Q12')
 order by surveyed_in ,
 		  response_count;
'''
plot_horizontal_bars(sql_query, "data_science_job_programming_languages")

# 4 想要從事資料科學工作，需要具備哪些技能與知識？（資料庫）
'''Which of the following big data products do you use most often?
2020: Q29A
2021: Q32A
2022: Q35
''' 
sql_query = '''
select surveyed_in ,
	   question_type ,
	   response ,
	   response_count 
 from aggregated_responses
 where (surveyed_in = 2020 and question_index = 'Q29A') or
 	   (surveyed_in = 2021 and question_index = 'Q32A') or
 	   (surveyed_in = 2022 and question_index = 'Q35')
 order by surveyed_in ,
 		  response_count;
'''
plot_horizontal_bars(sql_query, "data_science_job_databases")

# 5 想要從事資料科學工作，需要具備哪些技能與知識？（視覺化）
'''What data visualization libraries or tools do you use on a regular basis?
2020: Q14
2021: Q14
2022: Q15
'''
sql_query = '''
select surveyed_in ,
	   question_type ,
	   response ,
	   response_count 
 from aggregated_responses
 where (surveyed_in < 2022 and question_index = 'Q14') or
 	   (surveyed_in = 2022 and question_index = 'Q15')
 order by surveyed_in ,
 		  response_count;
'''
plot_horizontal_bars(sql_query, "data_science_job_visualizations")

# 6 想要從事資料科學工作，需要具備哪些技能與知識？（機器學習）
'''Which of the following ML algorithms do you use on a regular basis?
2020: Q17
2021: Q17
2022: Q18
'''
sql_query = '''
select surveyed_in ,
	   question_type ,
	   response ,
	   response_count 
 from aggregated_responses
 where (surveyed_in < 2022 and question_index = 'Q17') or
 	   (surveyed_in = 2022 and question_index = 'Q18')
 order by surveyed_in ,
 		  response_count;
'''
plot_horizontal_bars(sql_query, "data_science_job_machine_learnings")

# 檢測2020-2022 題目相符的題號。
sql_query = '''
select q2022.question_description,
	   q2022.question_index as '2022_question_index',
       q2021.question_index as '2021_question_index',
       q2020.question_index as '2020_question_index'
 from questions q2022
 join questions q2021
   on q2022.question_description = q2021.question_description and
      q2021.surveyed_in = 2021
  join questions q2020
   on q2022.question_description = q2020.question_description and
      q2020.surveyed_in = 2020
 where q2022.surveyed_in =2022
 group by q2022.question_description 
'''