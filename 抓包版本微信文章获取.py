import requests
import re
import store
from pip._vendor import requests, urllib3

# 微信公众号唯一ID
biz = 'MjM5NTYzMzU3Mg'
# 暂时未知（不改变的确认值）
uin = 'MjU4MjYwMDIxNA'
# 定时获取的验证的key
key = '2ac1ab72d9f9ae7fd2b041edfc1e3ec7757b3a74a173fee78d3d13e1694f61a37fede2ad73ef7baf281fa2afeedb8bc4f2992f294e335af0d' \
      'c5807260bfe0bc43c54a3bf53fa7c3c28de62f5cde116ddea13e839f633047f553a3cd675316ae8191c5c5bdadc3467d5fdbd013cd78c4ef' \
      '41645c8add1c8f16fdf375e5c6f7ec5'
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
