import json
import requests
import re
import time
import pandas as pd
import os

def get_data(begin):
    # 从文件中读取cookie和token
    with open('cookie.json', 'r') as file:
        data = json.load(file)
   
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Cookie': data['cookie'],
    }

    url = f'https://mp.weixin.qq.com/cgi-bin/appmsgpublish?sub=list&begin={begin}&count=10&token={data['token']}&lang=zh_CN'

    response = requests.get(url, headers=headers)

    # 正则匹截取json
    pattern = re.compile(r'publish_page\s*=\s*(.*?)isPublishPageNoEncode', re.DOTALL)
    match = pattern.search(response.text)
    publish_content = match.group(1).strip() if match else None
    # 删除json中的最后一个字符
    new_text = re.sub(r'.$', '', publish_content) 
    data = json.loads(new_text)
    return data

def parse_article_data(data):
    columns = ['标题', '时间', '链接', '阅读数', '点赞数', '评论数', '分享数','文章评分']
    df = pd.DataFrame(columns=columns)
    for item in data['publish_list']:
        new_text = re.sub(r'&quot;', '"', item['publish_info'])# 替换&quot;为"
        data = json.loads(new_text)
        for masge in data['appmsg_info']:
            title = masge['title']
            local_time = time.localtime(masge['line_info']['send_time']) # 将时间戳转换为时间元组
            time_str = time.strftime("%Y-%m-%d %H:%M:%S", local_time) # 将时间戳转换为日期时间
            url = masge['content_url']
            read_num = masge['read_num']
            like_num = masge['like_num']
            try:
                comment_num = masge['comment_num']
            except:
                comment_num = 0
            share_num = masge['share_num']
            print(f'时间: {time_str} | 标题: {title}')
            print(f'阅读数: {read_num},点赞数: {like_num},评论数: {comment_num},分享数: {share_num}')
            df.loc[len(df)] = [title, time_str, url, read_num, like_num, comment_num, share_num,read_num*0.1+like_num*0.3+comment_num*0.4+share_num*0.2]
            print('\n') 
        print('\n')
    return df
    
def save_to_excel(df, filename='wechat_articles', append=False):
    """保存数据到Excel文件，支持追加模式"""
    if df.empty:
        print("没有数据可保存")
        return
        
    file_path = f'{filename}.xlsx'
    
    if append and os.path.exists(file_path):
        try:
            existing_df = pd.read_excel(file_path, engine='openpyxl')
            combined_df = pd.concat([existing_df, df], ignore_index=True)
            combined_df.to_excel(file_path, index=False, engine='openpyxl')
            print(f"已追加 {len(df)} 条记录到 {file_path}，共 {len(combined_df)} 条记录")
        except Exception as e:
            print(f"追加数据时出错: {e}")
    else:
        try:
            df.to_excel(file_path, index=False, engine='openpyxl')
            print(f"数据已保存到 {file_path}，共 {len(df)} 条记录")
        except Exception as e:
            print(f"保存Excel文件时出错: {e}")

begin = 0
while True:
    data = get_data(begin)
    total_count = data['total_count'] # 总发表数

    publish_count = data['publish_count'] # 已通知
    masssend_count =  data['masssend_count'] # 未通知
    page_number = (total_count + 10) // 10 # 做页码参数时候*10
    save_to_excel(parse_article_data(data), append=True)
    begin += 10
    # 修正循环条件
    if begin >= page_number*10:
        break
        
    # 避免频繁请求
    time.sleep(1.3)
