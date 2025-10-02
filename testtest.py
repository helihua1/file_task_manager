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



    username = ""
    password = ""

    titles_and_texts = {
        # "测试title122222": "测试text1222222",
        #                 "测试title333333": "测试text3333333",
                        "测试title4444444": "测试text4444444"
                        }
    sleeptime = 3
    menu_value = "1"
    suffix = ""
    root_url = ""
    
    session = requests.Session()
    upload_date = url_update_context(session, root_url, suffix, username, password)

    zixun_page = test.upload_before(upload_date)

    for title, text in titles_and_texts.items():
        test.upload(session, zixun_page, upload_date.base_url, menu_value, title, text,True)
        # time.sleep(3)
    # test.get_menu(upload_date)





# 原来excute_task的代码

        # '''
        # 执行器机制：APScheduler默认使用ThreadPoolExecutor，每个job在独立的线程中执行。
        # 执行方式：每个 execute_task 在 APScheduler 的线程池中运行
        # 并发控制：受 max_instances: 10 限制
        # 职责：获取文件列表，调用文件上传逻辑
        # '''
#   with self.app.app_context():
#             try:
#                 # [4-2.1] 获取任务信息
#                 task = Task.query.get(task_id)
#                 if not task or not task.can_execute():
#                     self.remove_task_job(task_id)
#                     return
                
#                 # [4-2.2] 获取目标URL列表
#                 target_urls = task.target_url.split(',')
                
#                 # [4-2.3] 获取要执行的文件（根据每日执行数量乘以目标URL数量）
#                 files_to_execute = []
#                 for _ in range(task.daily_execution_count*len(target_urls)):
#                     file_to_execute = task.get_next_file()
#                     if file_to_execute:
#                         files_to_execute.append(file_to_execute)
#                     else:
#                         break
                
#                 if not files_to_execute:
#                     # 没有更多文件可执行，完成任务
#                     task.complete_task()
#                     self.remove_task_job(task_id)
#                     logger.info(f"任务 {task.task_name} 已完成，所有文件执行完毕")
#                     return
                
#                 # [4-2.4] 并行执行文件上传到多个目标网站
#                 self.execute_parallel_uploads(task, files_to_execute, target_urls)
                
#             except Exception as e:
#                 logger.error(f"执行任务 {task_id} 时发生错误: {str(e)}")
                
#                 # [4-2.5] 记录系统错误
#                 try:
#                     task = Task.query.get(task_id)
#                     if task:
#                         task.fail_task()
#                         self.remove_task_job(task_id)
#                 except Exception:
#                     pass