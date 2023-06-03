import json
import time

import requests
import re
import store
from pip._vendor import requests, urllib3
### 微信的历史文章地址：https://mp.weixin.qq.com/mp/profile_ext?action=home&__biz=替换==&scene=123#wechat_redirect
### 替换其中的biz值即可
### biz值可在任意一篇文章中用浏览器查看审核元素

# 微信公众号唯一ID
biz = '抓包工具获取'
# 个人微信id（不改变的确认值）
uin = '抓包工具获取'
# 定时获取的验证的key
key = '抓包工具获取'

offset = 0  # 页数，0开始，每10增长
count = '10'  # 每页显示的数量，有限制最多数
headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36 NetType/WIFI MicroMessenger/7.0.20.1781(0x6700143B) WindowsWechat(0x63090217) XWEB/6939 Flue'}

url = f'https://mp.weixin.qq.com/mp/profile_ext?action=getmsg&__biz={biz}==&f=json&offset={offset}&count={count}&is_ok=1&uin={uin}%3D%3D&key={key}'

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  # 解决证书报错

response = requests.get(url, headers=headers, verify=False)  # 获取页面
datalist = response.json()['general_msg_list']
datalist_1 = json.loads(datalist)  # 转换一下格式数据
for i in datalist_1['list']:
    datatime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(i['comm_msg_info']['datetime']))  # 时间戳转换成正常时间
    head_title = i['app_msg_ext_info']['title']  # 头条文章标题
    content_url = 'https://mp.weixin.qq.com/s'+re.sub(r'http://mp.weixin.qq.com/s/?|amp;','',i['app_msg_ext_info']['content_url'])  # 头条文章链接，正表达式替换成可获取阅读量的链接
    print(f'{datatime}\n{head_title}\n{content_url}')
    for o in i['app_msg_ext_info']['multi_app_msg_item_list']:
        order_title = o['title']  # 次条文章标题
        order_content_url = 'https://mp.weixin.qq.com/s'+re.sub(r'http://mp.weixin.qq.com/s/?|amp;','',o['content_url'])  # 次条文章链接，正表达式替换成可获取阅读量的链接
        print(f'{order_title}\n{order_content_url}')
    print('\n\n')
