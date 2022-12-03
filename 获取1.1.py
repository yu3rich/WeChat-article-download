import requests
import re

# 微信公众唯一ID
biz = 'MzI0MTA3NDU4OQ'
# 暂时未知（不改变的确认值）
uin = 'MjU4MjYwMDIxNA%3D%3D'
# 定时获取的验证的key
key = 'a5caf4e3c7ba63cbe6c4fbb37d4d7577c07d617c1cf1e1a7f4129caa82848ea81191282b75ca5c8fc51f8983154937450fe4ea59321c' \
      '1f871acbca4de8c24d21878e66d69763a29352ee8a7c329ebc0decb43e65c9f8fcaaf301bf0bac283614bef3626139bcd0d' \
      '81052f3cc6594b893d92fdd5a834e9820bc601f458ac0c5a3'
offset = '0'  # 页数，0开始，每10增长
count = '30'  # 每页限时的数量，有限制最多数

rul = f"https://mp.weixin.qq.com/mp/profile_ext?action=getmsg&__biz={biz}==&" \
      f"f=json&offset={offset}&count={count}&is_ok=1&scene=&uin={uin}&" \
      f"key={key}"

headers = {'user-agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) '
                         'Chrome/81.0.4044.138 Safari/537.36 NetType/WIFI MicroMessenger/7.0.20.1781(0x6700143B) '
                         'WindowsWechat(0x6308001f)'}

response = requests.get(rul, headers=headers, verify=False).text

new = response.replace('/', '')

pattern = re.compile('(?<=title).*?(?=digest)')

print(pattern.search(new))
