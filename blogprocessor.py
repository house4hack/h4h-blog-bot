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

with open ("config.json") as f:
    config = json.load(f)

bot = telebot.TeleBot(config['telegram_bot'])




def update_status(task_fn : str, status: str):
    '''Updates the status of the task'''

    conversation = load_conversation(task_fn)

    conversation['status'] = status

    save_conversation(task_fn, conversation)

def load_conversation(task_fn:str):
    '''Loads the conversation from the file'''
    with open(task_fn+"/conversation.json") as f:
        conversation = json.load(f)
    return conversation


def save_conversation(task_fn:str, conversation):
    '''Saves the conversation to the file'''
    with open(task_fn+"/conversation.json", "w") as f:
        json.dump(conversation, f)


def process_task(task_fn : str):
    '''Processes the task'''
    update_status(task_fn, 'Generating')
    conversation = load_conversation(task_fn)

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

    caption_str = "\n".join([f"Photo_{c[0]} : \"{c[2]}\"" for c in caption_list])


    prompt = f"""Write a blog article about: "{". ".join(text_list)}"
    I have {len(caption_list)} photos to add in the article, with the following captions:
    {caption_str}
    
    Indicate the location of the photo using square brackes, for example to place photo_1 write [photo_1].  Do not place photos in the middle of a sentence or paragraph, place it between paragraphs or at the end.
    
    Add a title for the blog post at the top.
    """

    openai.api_key = config['open_ai_key']

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

    contents = bu.get_contents(conversation['user_id'])
    title = bu.get_title(conversation['user_id'])
    preview = f"Title: {title}\n\n{contents}"
    bot.send_message(conversation['user_id'],preview)


def publish_task(task_fn):
    '''Publishes the task to the blog'''
    conversation = load_conversation(task_fn)
    print(conversation)
    re_comp = re.compile("\[Photo_[0-9]+\]",re.IGNORECASE)
    user = config['wordpress_user']
    password = config['wordpress_key']
    credentials = user + ':' + password
    token = base64.b64encode(credentials.encode())

    for m in conversation['messages']:
        if m['kind']=='media':
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
            config["wordpress_v2_json"]+"/media",
            headers=curHeaders,
            data=mediaImageBytes,
            )

            jj = resp.json()

            m['uploaded_href'] = jj['media_details']['sizes']['medium']['source_url']

    
    contents = conversation['contents']
    title = conversation['title']
    for m in conversation['messages']:
        if m['kind'] == 'media':
            if m.get('slug','') != '':
                href = m['uploaded_href']
                slug = m['slug']
                caption = m.get("text","")
                re_comp = re.compile(f"\[{slug}\]",re.IGNORECASE)
                contents = re_comp.sub(f'<figure class="wp-block-image size-large"><img src="{href}" alt=""/></figure><figcaption class="wp-caption-text">{caption}</figcaption>\n<br/>', contents)
            else:
                href = m['uploaded_href']
                contents += f'<figure class="wp-block-image size-large"><img src="{href}" alt=""/></figure>\n<br/>'



    user = config['wordpress_user']
    password = config['wordpress_key']
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
    responce = requests.post(config["wordpress_v2_json"]+"/posts" , headers=header, json=post)
    print(responce)
    bot.send_message(conversation['user_id'],f"Saved as draft on wordpress: {title}")
    bu.set_status(conversation['user_id'], "Published")
    
    


if __name__=='__main__':
    with open('./fifo') as fifo:
        while True:
            select.select([fifo],[],[fifo])
            for task in fifo:
                try:
                    if task is not None:
                        tasktype, task_fn = task.strip().split(",")
                        print(f"Starting {task_fn}")

                        if tasktype == "preview":
                            process_task(task_fn)
                        elif tasktype == "publish":
                            publish_task(task_fn)

                except Exception as e:
                    print(e)
                    traceback.print_exc(file=sys.stdout)
