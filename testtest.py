import time
from urllib.parse import urljoin

import requests

import test
if __name__ == '__main__':
    class url_update_context:
        def __init__(self,session,root_url,suffix,username,password):
            self.session = session
            self.suffix = suffix
            self.root_url = root_url

            self.base_url = urljoin(self.root_url, self.suffix)

            self.username = username
            self.password = password


  

    username = "yh1"
    password = "yh123456"

    titles_and_texts = {"测试title122222": "测试text1222222",
                        "测试title333333": "测试text3333333",
                        "测试title4444444": "测试text4444444"
                        }
    sleeptime = 3
    menu_value = "1"
    suffix = "e/AcoyKcy7s9"
    root_url = "http://lin.cqleshun.com"
    
    session = requests.Session()
    upload_date = url_update_context(session, root_url, suffix, username, password)

    zixun_page = test.upload_before(upload_date)

    for title, text in titles_and_texts.items():
        test.upload(session, zixun_page, upload_date.base_url, menu_value, title, text)
        time.sleep(3)
    # test.get_menu(upload_date)






