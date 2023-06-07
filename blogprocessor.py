import blogbot_utils as bu
import json
import telebot
import openai
import select 
import traceback
import sys

import requests
import base64
import os
import re
from datetime import datetime

import threading
import queue
import time




class BlogProcessorWorker(threading.Thread):
    def __init__(self, q:queue.Queue, config:dict, *args, **kwargs):
        self.q = q
        self.config = config
        with open ("config.json") as f:
            self.config = json.load(f)

        self.bot = telebot.TeleBot(self.config['telegram_bot'])
        super().__init__(*args, **kwargs)

    def run(self):
        while True:
            try:
                tasktype, user_id = self.q.get(block=False)  # 3s timeout
                have_work = True
            except queue.Empty:
                have_work = False
                time.sleep(1)

            if have_work:
                try:
                    if tasktype == "preview":
                        self.process_task(user_id)
                        
                    elif tasktype == "publish":
                        self.publish_task(user_id)
                        
                except Exception as e:
                    print(e)
                    traceback.print_exc()
                    self.bot.send_message(user_id, "Something went wrong, please try again later:\n {}".format(e))


    def process_task(self, user_id : str):
        '''Processes the task'''
        
        bu.set_status(user_id, "Generating")
        conversation = bu.get_conversation(user_id)

        text_list = []

        # make caption strings
        caption_list = []
        i = 1
        for m in conversation['messages']:
            if m['kind'] == "text":
                text_list.append(m['text'])
            elif m['kind'] == 'media':
                if m.get('text',None) is not None and m.get('text','').strip() != '':
                    caption_list.append((i, m['filename'],m['text']))
                    m['slug'] = f"Photo_{i}"
                    i+=1

        bu.save_conversation(user_id, conversation)
        caption_str = "\n".join([f"Photo_{c[0]} : \"{c[2]}\"" for c in caption_list])


        prompt = f"""Write a blog article about: "{". ".join(text_list)}"
        I have {len(caption_list)} photos to add in the article, with the following captions:
        {caption_str}
        
        Indicate the location of the photo using square brackes, for example to place photo_1 write [photo_1].  Do not place photos in the middle of a sentence or paragraph, place it between paragraphs or at the end.
        
        Add a title for the blog post at the top.
        """

        openai.api_key = self.config['open_ai_key']

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                    {"role": "system", "content": "You are a blog writer for a makerspace called House4Hack. The makerspace gets together Tuesday evenings at the House and these articles chronicles the activities."},
                    {"role": "user", "content": prompt},
                ]
        )

        contents = ''
        for choice in response.choices:
            contents += choice.message.content

        title = contents.split("\n")[0]
        contents = "\n".join(contents.split("\n")[1:])

        title = title.split("Title:")[1].strip()

        bu.set_status(conversation['user_id'], "Preview")
        bu.set_contents(conversation['user_id'], contents)
        bu.set_title(conversation['user_id'], title)

        contents = bu.get_contents(user_id)
        title = bu.get_title(user_id)
        preview = f"Title: {title}\n\n{contents}"
        self.bot.send_message(user_id,preview)


    def publish_task(self, user_id:str):
        '''Publishes the task to the blog'''
        conversation = bu.get_conversation(user_id)
        task_fn = bu.get_task_fn(user_id)

        re_comp = re.compile("\[Photo_[0-9]+\]",re.IGNORECASE)
        user = self.config['wordpress_user']
        password = self.config['wordpress_key']
        credentials = user + ':' + password
        token = base64.b64encode(credentials.encode())

        for m in conversation['messages']:
            if m['kind']=='media' and m.get('uploaded_href',None) is None:
                toUploadImagePath = task_fn+"/"+m['filename']
                mediaImageBytes = open(toUploadImagePath, 'rb').read()


                uploadImageFilename = m['filename']
                _, ext = os.path.splitext(m['filename'])
                curHeaders = {
                'Authorization': 'Basic ' + token.decode('utf-8'),
                "Content-Type": f"image/{ext[1:]}",
                "Accept": "application/json",
                'Content-Disposition': "attachment; filename=%s" % uploadImageFilename,
                }

                resp = requests.post(
                self.config["wordpress_v2_json"]+"/media",
                headers=curHeaders,
                data=mediaImageBytes,
                )

                if resp.status_code != 201 and resp.status_code != 200:
                    raise Exception("Error uploading image: {}".format(resp.reason))

                jj = resp.json()

                if jj['mime_type'].startswith("video"):
                    m['uploaded_href'] = jj['source_url']
                    height = jj['media_details']['height']
                    width = jj['media_details']['width'] 
                    m['tag'] = f'[video width="{width}" height="{height}" mp4="{jj["source_url"]}"][/video]'
                else:
                    m['uploaded_href'] = jj['media_details']['sizes']['medium']['source_url']
                    m['tag']=f"""<img src="{m['uploaded_href']}" alt="{m.get('text','')}" />"""

                bu.save_conversation(user_id, conversation)

        contents = conversation['contents']

        today = datetime.strftime(datetime.now(),"%Y/%m/%d")

        title = today + " - " + conversation['title']
        for m in conversation['messages']:
            if m['kind'] == 'media':
                if m.get('slug','') != '':
                    href = m['uploaded_href']
                    slug = m['slug']
                    caption = m.get("text","")
                    tag = m.get("tag","")
                    re_comp = re.compile(f"\[{slug}\]",re.IGNORECASE)
                    contents = re_comp.sub(f'<figure class="wp-block-image size-large">{tag}</figure><figcaption class="wp-caption-text">{caption}</figcaption>\n<br/>', contents)
                    # <figure class="wp-block-image size-large">[video width="720" height="1280" mp4="http://www.house4hack.co.za/wp-content/uploads/2023/06/d952c368-ff0b-45d6-8ba8-67071336142b.mp4"][/video]</figure>
                else:
                    href = m['uploaded_href']
                    contents += f'<figure class="wp-block-image size-large"><img src="{href}" alt=""/></figure>\n<br/>'



        user = self.config['wordpress_user']
        password = self.config['wordpress_key']
        credentials = user + ':' + password
        token = base64.b64encode(credentials.encode())
        header = {'Authorization': 'Basic ' + token.decode('utf-8')}

        post = {
        'title'    : title,
        'status'   : 'draft', 
        'content'  : contents,
        'categories': 38, # category ID
        'date'   : datetime.now().isoformat().split('.')[0]
        }
        responce = requests.post(self.config["wordpress_v2_json"]+"/posts" , headers=header, json=post)
        if responce.status_code != 201 and responce.status_code != 200:
            raise Exception("Error publishing post: {}".format(responce.reason))
        
        jj = responce.json()
        #link = jj['link']
        id = jj['id']
        link = f"https://www.house4hack.co.za/wp-admin/post.php?post={id}&action=edit"

        self.bot.send_message(user_id,f"Saved as draft on wordpress: {title}\n{link}")
        bu.set_status(user_id, "Published")
        
    


#if __name__=='__main__':
#    config = json.load(open("config.json"))
#    work_queue = queue.Queue()
#    worker = BlogProcessorWorker(work_queue, config)
#    worker.daemon = True
#    worker.start()
#
#    inFD = os.open('./fifo', os.O_RDWR | os.O_NONBLOCK)
#    sIn = os.fdopen(inFD, 'r')
#    while True:
#        select.select([sIn],[],[sIn])
#        for task in sIn:
#            try:
#                if task is not None:
#                    tasktype, user_id = task.strip().split(",")
#                    print(f"Starting {tasktype} for {user_id}")
#                    work_queue.put_nowait((tasktype, user_id))
#                    #work_queue.join()
#                time.sleep(1)
#                    
#
#            except Exception as e:
#                print(e)
#                traceback.print_exc(file=sys.stdout)
