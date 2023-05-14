import requests
import re
import store   # 文件储存模块
from pip._vendor import requests, urllib3
"""
需要配合抓包工具获取相应的参数才能获取信息
"""

# 微信公众号唯一ID
biz = '抓包工具获取'
# 个人微信id
uin = '抓包工具获取'
# 定时获取的验证的key
key = '抓包工具获取'
offset = 0  # 页数，0开始，每10增长
count = '10'  # 每页显示的数量，有限制最多数


def gett(biz, uin, key, offset, count):
    rul = f"https://mp.weixin.qq.com/mp/profile_ext?action=getmsg&__biz={biz}==&" \
          f"f=json&offset={offset}&count={count}&is_ok=1&uin={uin}&" \
          f"key={key}"
    ttt = f'https://mp.weixin.qq.com/mp/profile_ext?action=getmsg&__biz={biz}==&f=json&offset={offset}&count={count}&is_ok=1&uin={uin}%3D%3D&key={key}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36'}

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  # 解决证书报错

    response = requests.get(ttt, headers=headers, verify=False).text  # 获取页面返回的文本

    new = response.replace('/', '')  # 删除获取文章中的反斜杠
    title_re = re.compile(r'(?<=title\\":\\").*?(?=\\",\\"digest)')  # 获取标题的正表达式
    wxrul_re = re.compile(r'(?<=content_url\\":\\").*?(?=#wechat_redirect)')  # 获取文章链接的正表达式
    jpgrul_re = re.compile(r'(?<=cover\\":\\").*?=jpeg')  # 获取封面图片的正表达式

    title_data = title_re.findall(new)
    wxrul_data = wxrul_re.findall(new)
    jpgrul_data = jpgrul_re.findall(new)
    datass = []
    for i, o, p in zip(title_data,wxrul_data,jpgrul_data):
        list = [i,'https://mp.weixin.qq.com/s?'+re.sub(r'http:\\mp.weixin.qq.com\\s\?|amp;','',o),p]
        datass.append(list)
    return datass


store = store.Dataxls('gat公众号.xlsx',['标题', '文章链接', '图片'])

while True:
    ttt = gett(biz, uin, key, offset, count)
    for i in ttt:
        print(f'正在储存:{i[0]}\n')
        store.xls_1(i)
    if offset == 1000:
        break
    else:
        offset = offset + 10
