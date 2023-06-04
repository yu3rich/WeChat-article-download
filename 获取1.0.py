import time
from selenium import webdriver
from selenium.webdriver.common.by import By
import json
import xlsxwriter

#初始变量参数
n = 0
s = 1
#打开浏览器窗口
driver = webdriver.Chrome()
#设置浏览器窗口参数
print('调整浏览器窗口大小')
driver.set_window_size(1900,500)
#进入公众号登陆页面
url = 'https://mp.weixin.qq.com/'
driver.get(url)

try:
    # 从保存文件中提取cookies
    print('-----读取缓存-----')
    f1 = open('cookies.txt')
    cookie = f1.read()
    cookie_list = json.loads(cookie)    #json读取cookies
    print('-----写入缓存-----')
    for c in cookie_list:
        driver.add_cookie(c)    #取出的cookie循环加入drive
    print('-----重新载入网页-----')
    driver.refresh()    # 刷新后页面显示已登录
except:
    #检测页面是否登陆
    print("读取失败\n------请手动登录-----")
    while n >= 0:
        title = driver.title
        if title == "微信公众平台":
            n = n + 1
            time.sleep(5)
            print('-----正在等待第{}次-----'.format(n))
        else:
            print('-----登陆成功-----')
            break
cookies = driver.get_cookies()    # 获取cookies
f1 = open('cookies.txt', 'w')    #cookies存入文件JSON字符串
f1.write(json.dumps(cookies))
print('重新写入当前缓存')
f1.close()

#time.sleep(10)
#进入发表记录
driver.find_element(By.XPATH, '//*[@id="js_level2_title"]/li[1]/ul/li[3]/a/span/span').click()

#获取页数
nums = int(driver.find_element(By.XPATH, '//*[@id="app"]/div/div[2]/div[2]/span[1]/span/label[6]').text)
#nums = 2
print('共计{}页,预计文章约{}篇'.format(nums,nums*5))

wechat_datas_1 = []
wechat_datas_2 = []
wechat_datas_3 = []
wechat_datas_4 = []


def dataxls(dataxls):
    workbook = xlsxwriter.Workbook(r'C:\Users\zx\Desktop\公众号数据分析.xlsx')  # 创建文件设置目录
    worksheet = workbook.add_worksheet('公众号数据')  # 设置工作表名
    # 设置表头
    header = ['阅读量', '发表时间', '标题', '链接']
    worksheet.write_row('A1', header)
    # 存入各个数据
    worksheet.write_column('A2', dataxls[0])
    worksheet.write_column('B2', dataxls[1])
    worksheet.write_column('C2', dataxls[2])
    worksheet.write_column('D2', dataxls[3])
    # 关闭文件
    workbook.close()
    return (print('储存成功'))



#循环获取数据
for i in range(nums):
    print('正在获取第{}页'.format(s))
    s = s + 1
    #获取标题，发表时间，阅读量
    wechat_datas = driver.find_elements(By.CSS_SELECTOR, '.publish_content .publish_hover_content')
    for wechat_data in wechat_datas:
        wechat_title = wechat_data.find_element(By.CSS_SELECTOR, '.weui-desktop-mass-appmsg__title').text
        #print(wechat_title)
        wechat_datas_3.append(wechat_title)
        try:
            wechat_time = wechat_data.find_element(By.CSS_SELECTOR, '.weui-desktop-mass__time').text
            #print(wechat_time)
            wechat_datas_2.append(wechat_time)
        except:
            #print(wechat_time)
            wechat_datas_2.append(wechat_time)
        try:
            wechat_read = wechat_data.find_element(By.CSS_SELECTOR, '.weui-desktop-mass-media__data__inner').text
            #print(wechat_read)
            wechat_datas_1.append(int(wechat_read.replace(',', '')))
        except:
            wechat_datas_1.append(0)
        wechat_link = wechat_data.find_element(By.CSS_SELECTOR, '.weui-desktop-mass-appmsg__title').get_attribute('href')
        #print(wechat_link)
        wechat_datas_4.append(wechat_link)
    try:
        #点击下一页
        driver.find_element(By.LINK_TEXT, '下一页').click()
    except:
        print('获取结束')
#创建数据汇列表
datas = []
datas.append(wechat_datas_1)
datas.append(wechat_datas_2)
datas.append(wechat_datas_3)
datas.append(wechat_datas_4)
dataxls(datas)

#等待20秒关闭浏览器
print('即将关闭浏览器')
time.sleep(3)
driver.close()
