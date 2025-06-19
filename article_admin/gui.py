import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog, StringVar
import json
import os
import pickle
import time
from io import BytesIO
from threading import Thread, Event
from urllib.parse import urlparse, parse_qs
import re
import pandas as pd
import requests
from PIL import Image, ImageTk
from fake_useragent import UserAgent
from concurrent.futures import ThreadPoolExecutor

# 读取配置文件
def load_config():
    try:
        if os.path.exists('config.json'):
            with open('config.json', 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"读取配置文件出错: {e}")
    return {}

# 保存配置文件
def save_config(config):
    try:
        with open('config.json', 'w') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"保存配置文件出错: {e}")

config = load_config()
REQUEST_INTERVAL = config.get('request_interval', 1.3)
SAVE_PATH = config.get('save_path', '.')

class ShowQRCode:
    """显示二维码的类，更新界面中的二维码图像"""
    def __init__(self, qr_code_label, log_text):
        self.qr_code_label = qr_code_label
        self.log_text = log_text
        self.qr_image = None
        
    def update_qr_code(self, data):
        try:
            img = Image.open(BytesIO(data))
            img = img.resize((200, 200), Image.LANCZOS)
            self.qr_image = ImageTk.PhotoImage(img)
            self.qr_code_label.config(image=self.qr_image)
            self.log_text.insert(tk.END, "请使用微信扫描界面中的二维码登录\n")
            self.log_text.see(tk.END)
        except Exception as e:
            self.log_text.insert(tk.END, f"显示二维码出错: {e}\n")
            self.log_text.see(tk.END)

class WeChatLogin:
    """微信公众号登录类"""
    def __init__(self, log_text=None):
        self.ua = UserAgent()
        self.headers = {
            'User-Agent': self.ua.random,
            'Referer': 'https://mp.weixin.qq.com/',
            'Host': 'mp.weixin.qq.com'
        }
        self.log_text = log_text
        
    def log(self, message):
        if self.log_text:
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
        else:
            print(message)
            
    def is_login(self, session, cookie_info=None):
        """检查Cookies是否有效"""
        try:
            if cookie_info:
                # 从提供的cookie数据恢复session
                session.cookies = requests.utils.cookiejar_from_dict(json.loads(cookie_info['cookie']))
                
                # 验证Cookies是否有效
                response = session.get(
                    'https://mp.weixin.qq.com/cgi-bin/scanloginqrcode?action=ask&token=&lang=zh_CN&f=json&ajax=1'
                )
                data = response.json()
                
                if data.get('base_resp', {}).get('ret') == 0:
                    self.log('Cookies值有效！')
                    return session, True
        except Exception as e:
            self.log(f"检查登录状态出错: {e}")
            
        self.log('Cookies值已经失效或不存在！')
        return session, False
        
    def login(self, qr_code_updater=None, stop_event=None, save_path=None):
        """执行公众号登录流程"""
        session = requests.Session()
        
        # 检查Cookies有效性
        if save_path:
            session, status = self.is_login(session, save_path)
        else:
            status = False
        
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
            self.log("正在获取登录二维码...")
            qrcode_response = session.get(
                f'https://mp.weixin.qq.com/cgi-bin/scanloginqrcode?action=getqrcode&random={int(time.time() * 1000)}'
            )
            
            # 更新界面中的二维码
            if qr_code_updater:
                qr_code_updater.update_qr_code(qrcode_response.content)
            
            # 等待扫码
            check_url = 'https://mp.weixin.qq.com/cgi-bin/scanloginqrcode?action=ask&token=&lang=zh_CN&f=json&ajax=1'
            
            self.log("等待扫码中...")
            while True:
                # 检查是否请求停止
                if stop_event and stop_event.is_set():
                    self.log("用户请求停止操作")
                    return None
                    
                try:
                    response = session.get(check_url)
                    data = response.json()
                    
                    if data.get('status') == 0:
                        self.log('二维码未失效，请扫码！')
                    elif data.get('status') == 6:
                        self.log('已扫码，请确认！')
                    elif data.get('status') == 1:
                        self.log('已确认，登录成功！')
                        
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
                            cookie_dict = requests.utils.dict_from_cookiejar(session.cookies)
                            cookie_str = json.dumps(cookie_dict)
                            
                            return {'token': token, 'cookie': cookie_str, 'timestamp': int(time.time())}
                        else:
                            self.log('获取token失败')
                            return None
                    
                    time.sleep(2)
                    
                except Exception as e:
                    self.log(f"等待扫码过程出错: {e}")
                    time.sleep(5)  # 出错后等待更长时间
        else:
            # 返回已保存的token和cookie
            return save_path

def get_data(begin, cookie_info, log_text=None):
    """获取公众号文章数据"""
    if log_text:
        log_text.insert(tk.END, f"正在获取第 {begin//10 + 1} 页数据...\n")
        log_text.see(tk.END)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Cookie': '; '.join([f"{name}={value}" for name, value in json.loads(cookie_info['cookie']).items()]),
    }

    url = f'https://mp.weixin.qq.com/cgi-bin/appmsgpublish?sub=list&begin={begin}&count=10&token={cookie_info["token"]}&lang=zh_CN'

    try:
        session = requests.Session()
        response = session.get(url, headers=headers)

        # 正则匹截取json
        pattern = re.compile(r'publish_page\s*=\s*(.*?)isPublishPageNoEncode', re.DOTALL)
        match = pattern.search(response.text)
        publish_content = match.group(1).strip() if match else None
        # 删除json中的最后一个字符
        new_text = re.sub(r'.$', '', publish_content)
        data = json.loads(new_text)
        return data
    except Exception as e:
        if log_text:
            log_text.insert(tk.END, f"获取数据出错: {e}\n")
            log_text.see(tk.END)
        return None

def parse_article_data(data, log_text=None):
    """解析文章数据"""
    if log_text:
        log_text.insert(tk.END, "正在解析文章数据...\n")
        log_text.see(tk.END)
    
    columns = ['标题', '时间', '链接', '阅读数', '点赞数', '评论数', '分享数', '文章评分']
    df = pd.DataFrame(columns=columns)
    
    articles_count = 0
    if data and 'publish_list' in data:
        for item in data['publish_list']:
            new_text = re.sub(r'&quot;', '"', item['publish_info'])  # 替换&quot;为"
            try:
                item_data = json.loads(new_text)
                for msg in item_data['appmsg_info']:
                    title = msg['title']
                    local_time = time.localtime(msg['line_info']['send_time'])  # 将时间戳转换为时间元组
                    time_str = time.strftime("%Y-%m-%d %H:%M:%S", local_time)  # 将时间戳转换为日期时间
                    url = msg['content_url']
                    read_num = msg['read_num']
                    like_num = msg['like_num']
                    comment_num = msg.get('comment_num', 0)
                    share_num = msg['share_num']
                    score = read_num * 0.1 + like_num * 0.3 + comment_num * 0.4 + share_num * 0.2
                    
                    if log_text:
                        log_text.insert(tk.END, f'时间: {time_str} | 标题: {title}\n')
                        log_text.insert(tk.END, f'阅读数: {read_num}, 点赞数: {like_num}, 评论数: {comment_num}, 分享数: {share_num}\n')
                        log_text.insert(tk.END, f'文章评分: {score:.2f}\n\n')
                        log_text.see(tk.END)
                    
                    df.loc[len(df)] = [title, time_str, url, read_num, like_num, comment_num, share_num, score]
                    articles_count += 1
            except Exception as e:
                if log_text:
                    log_text.insert(tk.END, f"解析文章数据出错: {e}\n")
                    log_text.see(tk.END)
    
    if log_text:
        log_text.insert(tk.END, f"成功解析 {articles_count} 篇文章数据\n\n")
        log_text.see(tk.END)
    
    return df

def save_to_excel(df, filename='wechat_articles', append=False, log_text=None):
    """保存数据到Excel文件，支持追加模式"""
    if df.empty:
        if log_text:
            log_text.insert(tk.END, "没有数据可保存\n")
            log_text.see(tk.END)
        return
    
    file_path = os.path.join(SAVE_PATH, f'{filename}.xlsx')
    
    if append and os.path.exists(file_path):
        try:
            existing_df = pd.read_excel(file_path, engine='openpyxl')
            combined_df = pd.concat([existing_df, df], ignore_index=True)
            combined_df.to_excel(file_path, index=False, engine='openpyxl')
            if log_text:
                log_text.insert(tk.END, f"已追加 {len(df)} 条记录到 {file_path}，共 {len(combined_df)} 条记录\n")
                log_text.insert(tk.END, f"文件保存路径: {file_path}\n")
                log_text.see(tk.END)
        except Exception as e:
            if log_text:
                log_text.insert(tk.END, f"追加数据时出错: {e}\n")
                log_text.see(tk.END)
    else:
        try:
            df.to_excel(file_path, index=False, engine='openpyxl')
            if log_text:
                log_text.insert(tk.END, f"数据已保存到 {file_path}，共 {len(df)} 条记录\n")
                log_text.insert(tk.END, f"文件保存路径: {file_path}\n")
                log_text.see(tk.END)
        except Exception as e:
            if log_text:
                log_text.insert(tk.END, f"保存Excel文件时出错: {e}\n")
                log_text.see(tk.END)

def load_cookie_data():
    """加载所有Cookie数据"""
    try:
        if os.path.exists('json_data.json'):
            with open('json_data.json', 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"读取Cookie数据出错: {e}")
    return {}

def save_cookie_data(cookie_data):
    """保存所有Cookie数据"""
    try:
        with open('json_data.json', 'w') as f:
            json.dump(cookie_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"保存Cookie数据出错: {e}")

def get_cookie(log_text, qr_code_label, stop_event, cookie_var):
    """获取Cookie的函数"""
    # 清空日志和二维码区域
    log_text.delete(1.0, tk.END)
    qr_code_label.config(image=None)
    
    # 更新按钮状态
    get_cookie_button.config(state=tk.DISABLED)
    start_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.NORMAL)
    
    # 创建二维码更新器
    qr_code_updater = ShowQRCode(qr_code_label, log_text)
    
    # 创建登录器
    wechat_login = WeChatLogin(log_text)
    
    # 在新线程中执行登录操作
    def login_thread():
        try:
            log_text.insert(tk.END, "开始获取微信公众号Cookie...\n")
            log_text.see(tk.END)
            
            # 登录获取Cookie
            cookie_info = wechat_login.login(qr_code_updater, stop_event)
            
            if cookie_info:
                log_text.insert(tk.END, "Cookie获取成功！\n\n")
                log_text.see(tk.END)
                
                # 加载现有的Cookie数据
                cookie_data = load_cookie_data()
                
                # 为新Cookie生成唯一ID
                new_id = max([int(k) for k in cookie_data.keys()]) + 1 if cookie_data else 1
                
                # 添加新Cookie
                cookie_data[new_id] = {
                    'id': new_id,
                    'token': cookie_info['token'],
                    'cookie': cookie_info['cookie'],
                    'timestamp': cookie_info['timestamp'],
                    'description': f"Token_{cookie_info['token'][:10]}..."
                }
                
                # 保存更新后的Cookie数据
                save_cookie_data(cookie_data)
                
                # 更新Cookie选择框
                root.after(0, lambda: update_cookie_list(cookie_var))
            else:
                log_text.insert(tk.END, "Cookie获取失败，请检查网络或重试\n")
                log_text.see(tk.END)
                
        except Exception as e:
            log_text.insert(tk.END, f"发生错误: {str(e)}\n")
            log_text.see(tk.END)
        finally:
            # 恢复按钮状态
            root.after(0, lambda: get_cookie_button.config(state=tk.NORMAL))
            root.after(0, lambda: start_button.config(state=tk.NORMAL if cookie_var.get() else tk.DISABLED))
            root.after(0, lambda: stop_button.config(state=tk.DISABLED))
    
    # 启动登录线程
    thread = Thread(target=login_thread)
    thread.daemon = True
    thread.start()

def update_cookie_list(cookie_var):
    """更新Cookie选择列表"""
    # 清空当前选项
    cookie_menu.delete(0, tk.END)
    
    # 加载所有Cookie数据
    cookie_data = load_cookie_data()
    
    if not cookie_data:
        cookie_var.set("")
        cookie_menu.add_command(label="没有可用的Cookie", state=tk.DISABLED)
        start_button.config(state=tk.DISABLED)
        return
    
    # 添加选项
    for cookie_id, info in sorted(cookie_data.items(), key=lambda x: x[1]['timestamp'], reverse=True):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(info['timestamp']))
        label = f"{timestamp} - {info['description']}"
        cookie_menu.add_command(label=label, command=lambda value=str(cookie_id): cookie_var.set(value))
    
    # 如果有可用的Cookie，默认选择第一个
    if cookie_data and not cookie_var.get():
        first_id = next(iter(cookie_data))
        cookie_var.set(first_id)
        start_button.config(state=tk.NORMAL)

def browse_cookie_file(cookie_var):
    """浏览并选择json_data.json文件中的Cookie"""
    # 加载所有Cookie数据
    cookie_data = load_cookie_data()
    
    if not cookie_data:
        messagebox.showinfo("提示", "没有可用的Cookie")
        return
    
    # 创建一个简单的选择对话框（宽度缩短为原来的60%）
    dialog = tk.Toplevel(root)
    dialog.title("选择Cookie")
    dialog.geometry("600x400")
    dialog.transient(root)
    dialog.grab_set()
    
    # 创建列表框显示所有Cookie
    frame = tk.Frame(dialog)
    frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)  # 减少内边距
    
    # 创建滚动条
    scrollbar = tk.Scrollbar(frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    # 创建列表框（字体缩小）
    listbox = tk.Listbox(frame, font=("黑体", 8), selectbackground="#7bb32e", yscrollcommand=scrollbar.set)
    listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    # 配置滚动条
    scrollbar.config(command=listbox.yview)
    
    # 存储ID和索引的映射
    id_map = {}
    
    # 添加Cookie到列表
    for idx, (cookie_id, info) in enumerate(sorted(cookie_data.items(), key=lambda x: x[1]['timestamp'], reverse=True)):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(info['timestamp']))
        label = f"{timestamp} - {info['description']}"
        listbox.insert(tk.END, label)
        id_map[idx] = cookie_id
    
    # 创建按钮框架
    button_frame = tk.Frame(dialog)
    button_frame.pack(fill=tk.X, padx=5, pady=5)  # 减少内边距
    
    # 创建选择按钮（按钮宽度和内边距缩小）
    def select_cookie():
        selection = listbox.curselection()
        if selection:
            selected_id = id_map[selection[0]]
            cookie_var.set(selected_id)
            dialog.destroy()
            messagebox.showinfo("成功", f"已选择Cookie: {cookie_data[selected_id]['description']}")
    
    select_btn = tk.Button(button_frame, text="选择", command=select_cookie,
                          font=("黑体", 10), bg="#7bb32e", fg="white", relief=tk.RAISED, bd=2, padx=10, pady=3)
    select_btn.pack(side=tk.LEFT, padx=(0, 5))  # 减少按钮间距
    
    # 创建删除按钮（按钮宽度和内边距缩小）
    def delete_cookie():
        selection = listbox.curselection()
        if not selection:
            messagebox.showinfo("提示", "请先选择一个Cookie")
            return
        
        selected_id = id_map[selection[0]]
        
        # 确认删除
        confirm = messagebox.askyesno("确认删除", f"确定要删除这个Cookie吗？\n{cookie_data[selected_id]['description']}")
        if not confirm:
            return
        
        # 删除选中的Cookie
        del cookie_data[selected_id]
        
        # 保存更新后的Cookie数据
        save_cookie_data(cookie_data)
        
        # 更新列表框
        listbox.delete(selection)
        id_map.pop(selection[0])
        
        # 更新索引映射
        new_id_map = {}
        for i, key in enumerate(id_map.values()):
            new_id_map[i] = key
        id_map.clear()
        id_map.update(new_id_map)
        
        messagebox.showinfo("成功", "Cookie已删除")
        
        # 如果列表为空，关闭对话框
        if listbox.size() == 0:
            dialog.destroy()
            update_cookie_list(cookie_var)
    
    delete_btn = tk.Button(button_frame, text="删除", command=delete_cookie,
                          font=("黑体", 10), bg="#d32f2f", fg="white", relief=tk.RAISED, bd=2, padx=10, pady=3)
    delete_btn.pack(side=tk.LEFT, padx=(0, 5))  # 减少按钮间距
    
    # 创建取消按钮（按钮宽度和内边距缩小）
    cancel_btn = tk.Button(button_frame, text="取消", command=dialog.destroy,
                          font=("黑体", 10), bg="#555555", fg="white", relief=tk.RAISED, bd=2, padx=10, pady=3)
    cancel_btn.pack(side=tk.LEFT)

def start_process(log_text, qr_code_label, stop_event, cookie_var, progress_bar):
    """启动爬取过程的主函数"""
    # 清空日志和二维码区域
    log_text.delete(1.0, tk.END)
    qr_code_label.config(image=None)
    
    # 更新按钮状态
    get_cookie_button.config(state=tk.DISABLED)
    start_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.NORMAL)
    
    # 获取选中的Cookie ID
    cookie_id = cookie_var.get()
    if not cookie_id:
        log_text.insert(tk.END, "请先选择有效的Cookie！\n")
        log_text.see(tk.END)
        # 恢复按钮状态
        get_cookie_button.config(state=tk.NORMAL)
        start_button.config(state=tk.NORMAL)
        stop_button.config(state=tk.DISABLED)
        return
    
    # 加载所有Cookie数据
    cookie_data = load_cookie_data()
    
    if cookie_id not in cookie_data:
        log_text.insert(tk.END, "选中的Cookie不存在！\n")
        log_text.see(tk.END)
        # 恢复按钮状态
        get_cookie_button.config(state=tk.NORMAL)
        start_button.config(state=tk.NORMAL)
        stop_button.config(state=tk.DISABLED)
        return
    
    # 获取选中的Cookie信息
    cookie_info = cookie_data[cookie_id]
    
    # 在新线程中执行爬取操作
    def crawl_thread():
        try:
            log_text.insert(tk.END, f"开始使用Cookie: {cookie_info['token'][:10]}... 获取数据\n")
            log_text.see(tk.END)
            
            begin = 0
            data = get_data(begin, cookie_info, log_text)
            if data:
                total_count = data['total_count']  # 总发表数
                page_number = (total_count + 10) // 10  # 页码
                log_text.insert(tk.END, f"总共有 {total_count} 篇文章，共 {page_number} 页\n")
                log_text.see(tk.END)

                progress_bar['maximum'] = page_number
                progress_bar['value'] = 0

                with ThreadPoolExecutor(max_workers=4) as executor:
                    while True:
                        # 检查是否请求停止
                        if stop_event.is_set():
                            log_text.insert(tk.END, "用户请求停止操作\n")
                            log_text.see(tk.END)
                            break
                        
                        future = executor.submit(get_data, begin, cookie_info, log_text)
                        data = future.result()
                        if data:
                            df = parse_article_data(data, log_text)
                            # 使用Cookie的ID作为文件名的一部分，避免不同账号的数据混淆
                            filename = f'wechat_articles_cookie_{cookie_id}'
                            save_to_excel(df, filename=filename, append=True, log_text=log_text)
                        
                        begin += 10
                        progress_bar['value'] = begin // 10
                        root.update_idletasks()

                        if begin >= page_number * 10:
                            log_text.insert(tk.END, "所有文章数据获取完成！\n")
                            log_text.see(tk.END)
                            break
                        
                        # 避免频繁请求
                        log_text.insert(tk.END, f"等待{REQUEST_INTERVAL}秒后继续获取下一页...\n\n")
                        log_text.see(tk.END)
                        time.sleep(REQUEST_INTERVAL)
        except Exception as e:
            log_text.insert(tk.END, f"发生错误: {str(e)}\n")
            log_text.see(tk.END)
        finally:
            # 恢复按钮状态
            root.after(0, lambda: get_cookie_button.config(state=tk.NORMAL))
            root.after(0, lambda: start_button.config(state=tk.NORMAL))
            root.after(0, lambda: stop_button.config(state=tk.DISABLED))
    
    # 启动爬取线程
    thread = Thread(target=crawl_thread)
    thread.daemon = True
    thread.start()

def stop_process(stop_event):
    """停止爬取过程"""
    stop_event.set()
    log_text.insert(tk.END, "正在停止操作，请稍候...\n")
    log_text.see(tk.END)

def set_save_path():
    global SAVE_PATH
    path = filedialog.askdirectory()
    if path:
        SAVE_PATH = path
        config['save_path'] = SAVE_PATH
        save_config(config)
        messagebox.showinfo("提示", f"保存路径已设置为: {SAVE_PATH}")

# 创建主窗口
root = tk.Tk()
root.title("微信公众号数据获取工具")
root.geometry("900x700")
root.configure(bg="#f0f0f0")

# 创建顶部标题
title_label = tk.Label(root, text="微信公众号数据获取工具", font=("黑体", 16, "bold"), bg="#7bb32e", fg="white", pady=10)
title_label.pack(fill=tk.X)

# 创建作者信息标签
author_label = tk.Label(root, text="作者: yu3rich", font=("黑体", 10), bg="#f0f0f0", fg="#555555")
author_label.pack(anchor=tk.NE, padx=10, pady=5)

# 创建主框架
main_frame = tk.Frame(root, bg="#f0f0f0")
main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

# 创建左侧二维码区域
left_frame = tk.Frame(main_frame, bg="#ffffff", relief=tk.RAISED, bd=1)
left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

qr_label = tk.Label(left_frame, text="扫描二维码登录", font=("黑体", 12), bg="#ffffff")
qr_label.pack(pady=10)

# 二维码显示区域
qr_code_label = tk.Label(left_frame, bg="#ffffff")
qr_code_label.pack(pady=20)

# 创建右侧日志区域
right_frame = tk.Frame(main_frame, bg="#ffffff", relief=tk.RAISED, bd=1)
right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

log_label = tk.Label(right_frame, text="操作日志", font=("黑体", 12), bg="#ffffff")
log_label.pack(pady=10)

# 日志显示区域
log_text = scrolledtext.ScrolledText(right_frame, width=50, height=20, font=('黑体', 10))
log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
log_text.config(state=tk.NORMAL)

# 创建底部按钮区域
button_frame = tk.Frame(root, bg="#f0f0f0")
button_frame.pack(fill=tk.X, padx=20, pady=10)

# 创建停止事件
stop_event = Event()

# 创建Cookie选择变量
cookie_var = StringVar()

# 创建Cookie选择菜单
cookie_label = tk.Label(button_frame, text="选择Cookie:", font=("黑体", 12), bg="#f0f0f0")
cookie_label.pack(side=tk.LEFT, padx=(0, 10))

cookie_menu = tk.Menu(button_frame, tearoff=0)
cookie_button = tk.Menubutton(button_frame, textvariable=cookie_var, font=("黑体", 12), bg="#e0e0e0", relief=tk.RAISED, bd=2, width=5)
cookie_button.pack(side=tk.LEFT, padx=(0, 10))
cookie_button.config(menu=cookie_menu)

# 创建浏览按钮
browse_button = tk.Button(button_frame, text="浏览...", command=lambda: browse_cookie_file(cookie_var),
                         font=("黑体", 12), bg="#555555", fg="white", relief=tk.RAISED, bd=2, padx=10, pady=10)
browse_button.pack(side=tk.LEFT, padx=(10, 10))

# 创建获取Cookie按钮
get_cookie_button = tk.Button(button_frame, text="获取新Cookie", command=lambda: get_cookie(log_text, qr_code_label, stop_event, cookie_var),
                         font=("黑体", 12), bg="#7bb32e", fg="white", relief=tk.RAISED, bd=2, padx=20, pady=10)
get_cookie_button.pack(side=tk.LEFT, padx=(10, 10))

# 创建开始按钮
start_button = tk.Button(button_frame, text="开始获取数据", command=lambda: start_process(log_text, qr_code_label, stop_event, cookie_var, progress_bar),
                         font=("黑体", 12), bg="#7bb32e", fg="white", relief=tk.RAISED, bd=2, padx=20, pady=10)
start_button.pack(side=tk.LEFT, padx=(10, 10))

# 创建停止按钮
stop_button = tk.Button(button_frame, text="停止", command=lambda: stop_process(stop_event),
                        font=("黑体", 12), bg="#d32f2f", fg="white", relief=tk.RAISED, bd=2, padx=20, pady=10)
stop_button.pack(side=tk.LEFT, padx=(10, 0))
stop_button.config(state=tk.DISABLED)

# 创建设置保存路径按钮
set_path_button = tk.Button(button_frame, text="设置保存路径", command=set_save_path,
                            font=("黑体", 12), bg="#555555", fg="white", relief=tk.RAISED, bd=2, padx=20, pady=10)
set_path_button.pack(side=tk.LEFT, padx=(10, 0))

# 创建进度条
progress_bar = ttk.Progressbar(root, orient=tk.HORIZONTAL, length=300, mode='determinate')
progress_bar.pack(pady=10)

# 初始化Cookie列表
update_cookie_list(cookie_var)

# 运行主循环
root.mainloop()
