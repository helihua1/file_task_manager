import re
from urllib.parse import urljoin
import time
import requests
from bs4 import BeautifulSoup
import webbrowser
import tempfile
import os
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
def login(update_context):
    session = update_context.session
    base_url = update_context.base_url
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

    # 四。得到跳转页面.
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

        # 得到‘增加信息’标签中跳转到的链接
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(resp_final.text, 'html.parser')

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
                return zixun_page,zixun_page_url
        else:
            print("从''增加信息''提取URL失败")
    else:
        print("未找到包含'增加信息'的TD标签")                
def upload(update_context):

    session = update_context.session
    base_url = update_context.base_url

    titles_and_texts = update_context.titles_and_texts
    sleeptime = update_context.sleeptime
    menu_value = update_context.menu_value



    zixun_page,zixun_page_url = login(update_context)
    #获取js文件中的内容，得到例如[('1', '|-资讯'), ('2', '|-疾病'), ('3', '|-中医'), ('4', '|-两性')]
    js_result = get_js_fr_zixun_page(session, zixun_page,zixun_page_url)
    print(js_result)


    # 七，获取上传文章页面的url ，menu_value是指定的栏目
    upload_url = get_upload_writings_page_url(zixun_page,base_url,menu_value)
    upload_writing_page = session.get(upload_url)
    open_resp(upload_writing_page)



    '''
    上传文章
    '''
    soup = BeautifulSoup(upload_writing_page.text, "html.parser")

    # 提取表单里的隐藏字段
    hidden_inputs = {tag['name']: tag.get('value', '')
                        for tag in soup.select("form input[type=hidden]")}

    for title,text in titles_and_texts.items():

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
            "getfirsttitlespic": "1"  # 是否缩略图

        }

        # 八，提交文章
        post_url = base_url + "/ecmsinfo.php"
        r = session.post(post_url, data=post_data)
        open_resp(r)
        time.sleep(sleeptime)

 

if __name__ == '__main__':
    class update_context:
        def __init__(self,session,base_url,username,password,titles_and_texts,sleeptime,menu_value):
            self.session = session
            self.base_url = base_url
            self.username = username
            self.password = password
            self.titles_and_texts = titles_and_texts
            self.sleeptime = sleeptime
            self.menu_value = menu_value

    session = requests.Session()
    base_url = "http://lin.cqleshun.com/e/AcoyKcy7s9"
    username = "yh1"
    password = "yh123456"

    titles_and_texts = {"测试title122222": "测试text1222222", 
    "测试title333333": "测试text3333333",
    "测试title4444444": "测试text4444444"
    }
    sleeptime = 3
    menu_value = "1"
    upload_date = update_context(session,base_url,username,password,titles_and_texts,sleeptime,menu_value)
    
    upload(upload_date)


