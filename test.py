from gzip import READ
import re
from urllib.parse import urljoin
import time
import requests
from bs4 import BeautifulSoup
import webbrowser
import tempfile
import os

from werkzeug.local import T
def open_resp(resp):
    # 假设 resp.text 是你的 HTML 内容
    html_content = resp.text  # 替换为实际 HTML 内容

    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # 创建 test_html 文件夹（如果不存在）
    html_dir = os.path.join(current_dir, "test_html")
    os.makedirs(html_dir, exist_ok=True)

    # 在 test_html 目录下创建临时 HTML 文件
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".html", encoding="utf-8", dir=html_dir) as f:
        f.write(html_content)
        temp_file_path = f.name

    # 用默认浏览器打开临时文件
    webbrowser.open(f"file://{temp_file_path}")

def get_js_fr_zixun_page(m_session,m_zixun_page,m_zixun_page_url):
    # 解析HTML获取JavaScript文件URL
    soup = BeautifulSoup(m_zixun_page.text, 'html.parser')
    script_tag = soup.find('script', src=True)
    if script_tag and 'cmsclass.js' in script_tag.get('src', ''):
        js_url = script_tag.get('src')
        print('jsurl'+js_url)


        # 根据页面 src中的url：../data/fc/cmsclass.js?1758779853 ，和页面的url：m_zixun_page_url拼接成完整URL，获取js
        # m_zixun_page_url = "http://lin.cqleshun.com/e/AcoyKcy7s9/AddInfoChClass.php?ehash_i6leQ=3ORDRW6Wj5kqB7kg7nNE"
        js_url = urljoin(m_zixun_page_url, js_url)
        # print('jsurl' + js_url)  # 拼接后 js_url://lin.cqleshun.com/e/data/fc/cmsclass.js?1758783012

        # 获取JavaScript文件内容
        js_response = m_session.get(js_url)
        js_content = js_response.text

        # # 解析JavaScript内容，提取选项信息
        # # 通常JavaScript会包含类似 document.write('<option value="1">|-资讯</option>') 的代码
        if js_content:
            pattern = re.compile(r"value=\\'([^\\']+)\\'[^>]*>([^<]+)</option>")
            js_results = pattern.findall(js_content)
        else:
            print("未找到选项，JavaScript内容:")
            print(js_content[:500])  # 打印前500个字符
        return js_results

def get_upload_writings_page_url(zixun_page,base_url,num ):
    """
    从 zixun_page 中提取 JavaScript 中的 URL 模板
    返回类似 'AddNews.php?&ehash_i6leQ=3ORDRW6Wj5kqB7kg7nNE&enews=AddNews&classid=' 的字符串
    """
    # 解析HTML获取JavaScript内容
    soup = BeautifulSoup(zixun_page.text, 'html.parser')
    
    # 查找包含 changeclass 函数的 script 标签
    script_tags = soup.find_all('script')
    
    for script in script_tags:
        if script.string and 'changeclass' in script.string:
            script_content = script.string
            
            # 使用正则表达式提取 self.location.href 中的 URL 模板
            # 匹配模式：self.location.href='AddNews.php?&ehash_i6leQ=3ORDRW6Wj5kqB7kg7nNE&enews=AddNews&classid='+obj.addclassid.value;
            pattern = r"self\.location\.href='([^']*AddNews\.php[^']*)'"
            match = re.search(pattern, script_content)

            if match:

                url_template = match.group(1)
                url_template_num = url_template + str(num)
                upload_writings_url = urljoin(base_url + '/', url_template_num)
                print(f"提取到的URL模板: {upload_writings_url}")
                return upload_writings_url
            else:
                print("未找到匹配的URL模板")
                print("JavaScript内容:")
                print(script_content)
                return None
    
    print("未找到包含 changeclass 函数的 script 标签")
    return None

def get_meta_jump_url(resp_post_session,login_url):
    # 三： meta refresh 跳转
    match = re.search(r'url=([^"]+)"?', resp_post_session.text, re.IGNORECASE)

    redirect_url = match.group(1)
    # 如果返回的是相对路径，拼接成完整 URL
    if not redirect_url.startswith("http"):
        from urllib.parse import urljoin

        redirect_url = urljoin(login_url, redirect_url)

    return redirect_url
def login_diguo(update_context):

    session = update_context.session
    base_url = update_context.base_url
    print(base_url)
    username = update_context.username
    password = update_context.password
    

    login_url = f"{base_url}/ecmsadmin.php"
    # 初始header：浏览器 Headers
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    }


    # # 一.get请求，测试
    resp_get = session.get(base_url, headers=headers)
    # open_resp(resp_get)


    soup = BeautifulSoup(resp_get.text, "html.parser")
    hidden_inputs = {tag['name']: tag.get('value', '') for tag in soup.select("input[type=hidden]")}

    # 2. 构造登录表单
    login_data = {
        "enews": "login",
        "username": username,
        "password": password,
        "equestion": "0",
        "eanswer": "adminwindow",
        **hidden_inputs  # 如果有隐藏字段
    }

    # 3. 二. POST 登录
    # 不用再显示设置header
    resp_post = session.post(login_url, data=login_data, allow_redirects=True)
    # open_resp(resp_post)

    redirect_url = get_meta_jump_url(resp_post,login_url)

    # 四。得到meta跳转页面.
    resp_redirect = session.get(redirect_url)
    # open_resp(resp_redirect)

    # 假设 resp_redirect 是你请求提示页的 response
    html = resp_redirect.text

    # 提取第一个 a href 链接
    match = re.search(r'<a\s+href=["\'](.*?)["\']', html, re.IGNORECASE)
    if match:
        href = match.group(1)
        target_url = urljoin(resp_redirect.url, href)  # 拼接为完整 URL
        # 五、跳转链接得到主页
        resp_final = session.get(target_url)
        # open_resp(resp_final)
        time.sleep(0.1)

        # 为了得到‘增加信息’标签中跳转到的链接
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(resp_final.text, 'html.parser')
        
        # 找到包含是否是gbk信息的页面
        # 查找指定的链接元素
        target_link = soup.find('a', href=True, title="帝国网站管理系统")
        if target_link:
            href = target_link.get('href')
            # 使用base_url和href拼接得到新的网址
            new_url = urljoin(base_url + '/', href)
            print(f"找到目标链接: {new_url}")
            
            # 进入新页面
            resp_new_page = session.get(new_url)
            soup_new = BeautifulSoup(resp_new_page.text, 'html.parser')
            
            # 查找是否有 <td>GBK</td>
            gbk_td = soup_new.find('td', string='GBK')
            if gbk_td:
                print('这个网站是gbk')
                ifGBK = True
            elif  soup_new.find('td', string='UTF-8'):
                print('这个网站是utf-8')
                ifGBK = False
            else:
                print('这个网站编码类型未知')
                ifGBK = False


        
        # 查找包含"增加信息"文本的TD标签
        td = soup.find('td', string='增加信息')
        if td and td.get('onclick'):
            onclick = td.get('onclick')
            # 从onclick中提取URL
            url_match = re.search(r"JumpToMain\('([^']+)'\)", onclick)
            if url_match:
                zixun_page_url = urljoin(base_url + '/', url_match.group(1))
                # 六，从主页跳转到增加信息的栏目选择页面
                zixun_page = session.get(zixun_page_url)
                # open_resp(zixun_page)
                return zixun_page,zixun_page_url,ifGBK
        else:
            print("从''增加信息''提取URL失败")
    else:
        print("未找到包含'增加信息'的TD标签")                
def upload_before(update_context):

    session = update_context.session
    base_url = update_context.base_url

 

    zixun_page,zixun_page_url,ifGBK = login_diguo(update_context)
    #获取js文件中的内容，得到例如[('1', '|-资讯'), ('2', '|-疾病'), ('3', '|-中医'), ('4', '|-两性')]
    js_result = get_js_fr_zixun_page(session, zixun_page,zixun_page_url)
    print(f'执行upload_before{js_result}')
    return zixun_page,ifGBK
   
def upload(session,zixun_page,base_url,menu_value,title,text,ifGBK=False):
    # 七，获取上传文章页面的url ，menu_value是指定的栏目
    upload_url = get_upload_writings_page_url(zixun_page,base_url,menu_value)
    upload_writing_page = session.get(upload_url)
    # open_resp(upload_writing_page)

    # print(f'上传文件名:{title}')
    '''
    上传文章
    '''
    soup = BeautifulSoup(upload_writing_page.text, "html.parser")

    # 提取表单里的隐藏字段
    hidden_inputs = {tag['name']: tag.get('value', '')
                        for tag in soup.select("form input[type=hidden]")}


    # 3. 构造文章数据
    post_data = {
        **hidden_inputs,  # 必须带上
        "checked": "1",
        "title": title,
        "newstext": text,
        "classid": menu_value,
        "ecmscheck": "0",
        "enews": "AddNews",  # 保持操作类型
        "submit": "提交",
        "copyimg": "1",  # 远程保存图片
        "getfirsttitlepic": "1",  # 取第x张图片为缩略图
        "getfirsttitlespic": "1",  # 是否缩略图
        "getfirsttitlespicw":"300",#缩略图宽度
        "getfirsttitlespich":"200" #缩略图高度

    }
    if ifGBK:
        post_data["newstext"] = text.encode("gbk")
        post_data["title"] = title.encode("gbk")

    # 八，提交文章
    post_url = base_url + "/ecmsinfo.php"
    r = session.post(post_url, data=post_data)
    open_resp(r)
    soup = BeautifulSoup(r.text, 'html.parser')

    # 方法1：直接搜索文本
    if soup.find(string=lambda text: text and "增加信息成功" in text):
        print("✅ 增加信息成功！")
    else:
        print("❌ 没有增加信息成功！")
        
    # 返回状态码
    return r.status_code

      


def get_menu(update_context):
    session = update_context.session

    zixun_page, zixun_page_url, ifGBK = login_diguo(update_context)  
    # 获取js文件中的内容，得到例如[('1', '|-资讯'), ('2', '|-疾病'), ('3', '|-中医'), ('4', '|-两性')]
    js_result = get_js_fr_zixun_page(session, zixun_page, zixun_page_url)
    print(f"执行get_menu得到：{js_result}")
    return js_result


def refresh_all(update_context):
    session = update_context.session
    zixun_page, zixun_page_url, ifGBK = login_diguo(update_context)
    print(zixun_page_url)

    url = zixun_page_url
    match = re.search(r'(\?ehash_[^=]+=[^&]+)', url)
    ehash = match.group(0)  #得到?ehash_xxxxxxxxx


    # 拼接成刷新页面url
    base = urljoin(update_context.base_url + "/", "ReHtml/ChangeData.php")
    refresh_url = base + ehash
    print(refresh_url)
    resp_get = session.get(refresh_url)
    # open_resp(resp_get)
    
    # 解析HTML，找到"刷新首页"按钮并提取onclick中的URL
    soup = BeautifulSoup(resp_get.text, 'html.parser')
    
    # 刷新一：刷新首页
    refresh_button = soup.find('input', {'value': '刷新首页'})
    
    if refresh_button and refresh_button.get('onclick'):
        onclick_content = refresh_button.get('onclick')
        
        # 从onclick中提取URL
        # onclick格式: self.location.href='../ecmschtml.php?enews=ReIndex&ehash_Rx5Oo=...'
        url_match = re.search(r"self\.location\.href='([^']+)'", onclick_content)
        
        if url_match:
            target_url = url_match.group(1)
            # 将HTML实体转换为正常字符
            target_url = target_url.replace('&amp;', '&')
            
            # 拼接成完整URL
            full_url = urljoin(resp_get.url, target_url)
            
            # 访问刷新首页URL
            resp_refresh_index = session.get(full_url)
            # open_resp(resp_refresh_index)
            
            
        else:
            print("未能从onclick中提取刷新首页URL")
    else:
        print("未找到刷新首页按钮")
    
    # 刷新二：刷新所有信息栏目页，有三次跳转
    refresh_all_button = soup.find('input', {'value': '刷新所有信息栏目页'})
    
    if refresh_all_button and refresh_all_button.get('onclick'):
        onclick_content = refresh_all_button.get('onclick')
        
        # 从onclick中提取URL
        # onclick格式: window.open('../ecmschtml.php?enews=ReListHtml_all&...','','');
        url_match = re.search(r"window\.open\('([^']+)'", onclick_content)
        
        if url_match:
            target_url = url_match.group(1)
            # 将HTML实体转换为正常字符
            target_url = target_url.replace('&amp;', '&')
            
            # 拼接成完整URL
            full_url = urljoin(resp_get.url, target_url)
            print(f"提取到的刷新所有栏目页URL: {full_url}")
            
            # 访问刷新所有栏目页URL
            resp_refresh_all_list = session.get(full_url)
            # open_resp(resp_refresh_all_list)
            
            # 检查是否有meta refresh跳转
            meta_match = re.search(r'<meta[^>]+content=["\']?\d+;url=([^"\'>\s]+)', resp_refresh_all_list.text, re.IGNORECASE)
            
            if meta_match:
                redirect_url = meta_match.group(1)
                # 将HTML实体转换为正常字符
                redirect_url = redirect_url.replace('&amp;', '&')
                
                # 拼接成完整URL
                next_url = urljoin(resp_refresh_all_list.url, redirect_url)
                print(f"提取到的meta跳转URL: {next_url}")
                
                # 访问跳转URL
                resp_refresh_all_list = session.get(next_url)
                # open_resp(resp_refresh_all_list)
                
                # 检查是否有JavaScript跳转 self.location.href
                js_match = re.search(r"self\.location\.href='([^']+)'", resp_refresh_all_list.text)
                
                if js_match:
                    redirect_url = js_match.group(1)
                    # 将HTML实体转换为正常字符
                    redirect_url = redirect_url.replace('&amp;', '&')
                    
                    # 拼接成完整URL
                    next_url = urljoin(resp_refresh_all_list.url, redirect_url)
                    
                    # 访问跳转URL
                    resp_refresh_all_list = session.get(next_url)
                    # open_resp(resp_refresh_all_list)
        else:
            print("未能从onclick中提取刷新所有栏目页URL")
    else:
        print("未找到刷新所有信息栏目页按钮")
    
    # 刷新三：勾选"全部刷新"并点击"刷新所有信息内容页面"
    refresh_content_button = soup.find('input', {'value': '刷新所有信息内容页面'})
    
    if refresh_content_button and refresh_content_button.get('onclick'):
        onclick_content = refresh_content_button.get('onclick')
        
        # onclick内容示例：
        # var toredohtml=0;if(document.dorehtml.havehtml.checked==true){toredohtml=1;}
        # window.open('DoRehtml.php?enews=ReNewsHtml&start=0&havehtml='+toredohtml+'&from=...','','');
        
        # 提取URL的各个部分（因为是字符串拼接）
        # 方法：提取所有单引号中的内容，然后拼接
        url_parts = re.findall(r"'([^']+)'", onclick_content)
        
        if len(url_parts) >= 1:
            # 第一部分通常是URL的主要部分
            # 例如：'DoRehtml.php?enews=ReNewsHtml&start=0&havehtml='
            # 然后是 toredohtml 变量
            # 然后是 '&from=...'
            
            # 重新构造完整URL，设置toredohtml=1（模拟勾选checkbox）
            # 从onclick提取完整的URL模式
            full_onclick = onclick_content
            
            # 查找window.open部分
            window_open_match = re.search(r"window\.open\((.+?)\)", full_onclick)
            
            if window_open_match:
                # 提取window.open的第一个参数（URL表达式）
                url_expression = window_open_match.group(1).split(',')[0]
                
                # 移除引号并重建URL，将 '+toredohtml+' 替换为 '1'
                # 例如：'DoRehtml.php?enews=ReNewsHtml&start=0&havehtml='+toredohtml+'&from=...'
                # 替换为：DoRehtml.php?enews=ReNewsHtml&start=0&havehtml=1&from=...
                
                # 方法：提取所有引号内容并用toredohtml=1连接
                parts = re.findall(r"'([^']*)'", url_expression)
                
                # 将所有部分拼接，中间用'1'（toredohtml的值）连接
                # 通常格式是：'part1'+toredohtml+'part2'+toredohtml+'part3'...
                # 我们要把所有部分用toredohtml=1拼接
                target_url = '1'.join(parts)
                
                # 将&amp;转换为&
                target_url = target_url.replace('&amp;', '&')
                
                # 拼接成完整URL
                full_url = urljoin(resp_get.url, target_url)
 
                # 访问URL
                resp_refresh_all_content = session.get(full_url)
                open_resp(resp_refresh_all_content)
                

                # ===============循环跳转，检验的时候用===================
                # # 检查返回页面中是否有iframe src
                # soup_content = BeautifulSoup(resp_refresh_all_content.text, 'html.parser')
                # iframe = soup_content.find('iframe')
                
                # if iframe and iframe.get('src'):
                #     iframe_src = iframe.get('src')
                #     # 将../转换并拼接成完整URL
                #     iframe_url = urljoin(resp_refresh_all_content.url, iframe_src)
                #     print(f"提取到iframe URL: {iframe_url}")

                #     # 实际跳了3次
                #     # 访问iframe中的实际刷新页面，并循环跟踪所有meta refresh跳转
                #     current_url = iframe_url
                #     refresh_count = 0
                #     max_refreshes = 1000  # 防止无限循环
                    
                #     while refresh_count < max_refreshes:
                #         resp_iframe_content = session.get(current_url)
                        
                #         # 解析页面，查找meta refresh
                #         soup_iframe = BeautifulSoup(resp_iframe_content.text, 'html.parser')
                #         meta_refresh = soup_iframe.find('meta', attrs={'http-equiv': 'refresh'})
                        
                #         if meta_refresh and meta_refresh.get('content'):
                #             content = meta_refresh.get('content')
                #             # 从content中提取URL，格式：0;url=...
                #             url_match = re.search(r'url=(.+)', content, re.IGNORECASE)
                            
                #             if url_match:
                #                 next_url = url_match.group(1)
                #                 next_url = urljoin(resp_iframe_content.url, next_url)
                                
                #                 # 提取进度信息
                #                 progress_match = re.search(r'ID:<font color=red><b>(\d+)</b></font>', resp_iframe_content.text)
                #                 if progress_match:
                #                     current_id = progress_match.group(1)
                #                     print(f"刷新进度 - 当前ID: {current_id}")
                                
                #                 current_url = next_url
                #                 refresh_count += 1
                #             else:
                #                 # 没有找到URL，结束循环
                #                 print("刷新完成（未找到下一个URL）")
                #                 open_resp(resp_iframe_content)
                #                 break
                #         else:
                #             # 没有meta refresh，说明刷新完成
                #             print(f"刷新所有信息内容页面完成！总共刷新 {refresh_count} 批次")
                #             open_resp(resp_iframe_content)
                #             break
                    
                #     if refresh_count >= max_refreshes:
                #         print(f"警告：达到最大刷新次数限制 ({max_refreshes})")
                #         open_resp(resp_iframe_content)
                # else:
                #     print("未找到iframe src")
            else:
                print("未能解析window.open语句")
        else:
            print("未能从onclick中提取URL部分")
    else:
        print("未找到刷新所有信息内容页面按钮")

if __name__ == '__main__':
    class url_update_context:
        def __init__(self,session,root_url,suffix,username,password):
            self.session = session
            self.suffix = suffix
            self.root_url = root_url

            self.base_url = urljoin(self.root_url, self.suffix)

            self.username = username
            self.password = password
  
    session = requests.Session()

    username = "yh1"
    password = "yh123456"

    titles_and_texts = {"测试title122222": "测试text1222222", 
    "测试title333333": "测试text3333333",
    "测试title4444444": "测试text4444444"
    }
    sleeptime = 3
    menu_value = "1"
    suffix = "e/AcoyKcy7s9/"
    root_url = "http://zx1.bh308.com"


    upload_date = url_update_context(session,root_url,suffix,username,password)
    
   

    zixun_page = upload_before(upload_date)
    for title,text in titles_and_texts.items():
        upload(session,zixun_page,upload_date.base_url,menu_value,title,text)
        time.sleep(3)



