import json
import os
import pickle
import time
from io import BytesIO
from threading import Thread
from urllib.parse import urlparse, parse_qs

import requests
from PIL import Image
from fake_useragent import UserAgent


class ShowQRCode(Thread):
    """显示二维码的线程类"""
    def __init__(self, data):
        super().__init__()
        self.data = data
        
    def run(self):
        try:
            img = Image.open(BytesIO(self.data))
            img.show()
        except Exception as e:
            print(f"显示二维码出错: {e}")


class WeChatLogin:
    """微信公众号登录类"""
    
    def __init__(self):
        self.ua = UserAgent()
        self.headers = {
            'User-Agent': self.ua.random, 
            'Referer': 'https://mp.weixin.qq.com/',
            'Host': 'mp.weixin.qq.com'
        }
    
    def is_login(self, session):
        """检查Cookies是否有效"""
        try:
            if os.path.exists('gzhcookies.cookie'):
                session.cookies = pickle.load(open('gzhcookies.cookie', 'rb'))
                session.cookies.load(ignore_discard=True)
                
                # 验证Cookies是否有效
                response = session.get(
                    'https://mp.weixin.qq.com/cgi-bin/scanloginqrcode?action=ask&token=&lang=zh_CN&f=json&ajax=1'
                )
                data = response.json()
                
                if data.get('base_resp', {}).get('ret') == 0:
                    print('Cookies值有效，无需扫码登录！')
                    return session, True
        except Exception as e:
            print(f"检查登录状态出错: {e}")
        
        print('Cookies值已经失效，请重新扫码登录！')
        return session, False
    
    def login(self):
        """执行公众号登录流程"""
        session = requests.Session()
        
        # 检查Cookies有效性
        session, status = self.is_login(session)
        
        if not status:
            session = requests.Session()
            session.headers.update(self.headers)
            
            # 初始化登录
            session.get('https://mp.weixin.qq.com/')
            session.post(
                'https://mp.weixin.qq.com/cgi-bin/bizlogin?action=startlogin',
                data=f'userlang=zh_CN&redirect_url=&login_type=3&sessionid={int(time.time() * 1000)}&token=&lang=zh_CN&f=json&ajax=1'
            )
            
            # 获取二维码
            qrcode_response = session.get(
                f'https://mp.weixin.qq.com/cgi-bin/scanloginqrcode?action=getqrcode&random={int(time.time() * 1000)}'
            )
            
            # 显示二维码
            qrcode_thread = ShowQRCode(qrcode_response.content)
            qrcode_thread.start()
            
            # 等待扫码
            check_url = 'https://mp.weixin.qq.com/cgi-bin/scanloginqrcode?action=ask&token=&lang=zh_CN&f=json&ajax=1'
            
            while True:
                try:
                    response = session.get(check_url)
                    data = response.json()
                    
                    if data.get('status') == 0:
                        print('二维码未失效，请扫码！')
                    elif data.get('status') == 6:
                        print('已扫码，请确认！')
                    elif data.get('status') == 1:
                        print('已确认，登录成功！')
                        
                        # 完成登录
                        login_response = session.post(
                            'https://mp.weixin.qq.com/cgi-bin/bizlogin?action=login',
                            data='userlang=zh_CN&redirect_url=&cookie_forbidden=0&cookie_cleaned=1&plugin_used=0&login_type=3&token=&lang=zh_CN&f=json&ajax=1'
                        )
                        
                        login_data = login_response.json()
                        redirect_url = login_data.get('redirect_url', '')
                        token = parse_qs(urlparse(redirect_url).query).get('token', [None])[0]
                        
                        if token:
                            session.get(f'https://mp.weixin.qq.com{redirect_url}')
                            
                            # 保存Cookies和token
                            with open('gzhcookies.cookie', 'wb') as f:
                                pickle.dump(session.cookies, f)
                            
                            cookie_str = '; '.join([f"{name}={value}" for name, value in session.cookies.items()])
                            
                            with open('cookie.json', 'w') as f:
                                json.dump({'token': token, 'cookie': cookie_str}, f, ensure_ascii=False)
                            
                            return {'token': token, 'cookie': cookie_str}
                        else:
                            print('获取token失败')
                            return None
                    
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"等待扫码过程出错: {e}")
                    time.sleep(5)  # 出错后等待更长时间
        else:
            # 读取已保存的token和cookie
            try:
                with open('cookie.json', 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"读取登录信息出错: {e}")
                return None


if __name__ == "__main__":
    wechat_login = WeChatLogin()
    login_info = wechat_login.login()
    
    if login_info:
        print("登录成功，获取到的信息:")
        print(f"Token: {login_info['token']}")
        print(f"Cookie: {login_info['cookie'][:50]}...")  # 只显示部分Cookie
    else:
        print("登录失败")