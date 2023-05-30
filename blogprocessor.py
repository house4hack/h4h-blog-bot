import blogbot_utils as bu
import json
import telebot
import openai
import select 
import traceback
import sys


with open ("config.json") as f:
    config = json.load(f)

bot = telebot.TeleBot(config['telegram_bot'])




def update_status(task_fn : str, status: str):

    conversation = load_conversation(task_fn)

    conversation['status'] = status

    save_conversation(task_fn, conversation)

def load_conversation(task_fn:str):
    with open(task_fn+"/conversation.json") as f:
        conversation = json.load(f)
    return conversation


def save_conversation(task_fn:str, conversation):
    with open(task_fn+"/conversation.json", "w") as f:
        json.dump(conversation, f)


def process_task(task_fn : str):
    update_status(task_fn, 'Generating')
    conversation = load_conversation(task_fn)
    prompt_count, photo_count, caption_count = bu.summary_conversation(conversation)

    if photo_count < 5:
        kind = "blog"
    else:
        kind = "gallery"

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

    if kind == "blog":
        prompt = f"""Write a blog article about: "{". ".join(text_list)}"
        I have {len(caption_list)} photos to add in the article, with the following captions:
        {caption_str}
        
        Indicate the location of the photo using square brackes, for example to place photo_1 write [photo_1].
        
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

    result = ''
    for choice in response.choices:
        result += choice.message.content


    conversation["contents"] = result
    conversation["status"] = "Preview"

    save_conversation(task_fn, conversation)
    

    bot.send_message(conversation['user_id'],bu.show_contents(conversation["user_id"]))

if __name__=='__main__':
    with open('./fifo') as fifo:
        while True:
            select.select([fifo],[],[fifo])
            for task_fn in fifo:
                try:
                    if task_fn is not None:
                        print(f"Starting {task_fn}")
                        process_task(task_fn.strip())
                except Exception as e:
                    print(e)
                    traceback.print_exc(file=sys.stdout)
