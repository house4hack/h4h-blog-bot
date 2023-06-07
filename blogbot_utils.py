import uuid
import os.path
from pathlib import Path
import json
import time
import shutil
import glob
import queue

FOLDER = "./conversations/"
STASH_FOLDER = "./stash/"



def make_filename(folder, id, filename=""):
    '''Makes a filename from the folder and id'''
    folder = str(folder) + str(id) 
    if filename != "":
        folder += "/" +str(filename)
    return folder

def new_convesation(user_id : int):
    '''Creates a new conversation'''
    return {"user_id":user_id, "messages":[],"status":"Draft"}

def make_sane_filename(org_filename, caption):
    '''Makes a sane filename from the original filename and the caption'''
    keepcharacters = (' ','.','_')
    if caption is not None:
        filename = "".join(c for c in caption if c.isalnum() or c in keepcharacters).rstrip()
        filename = filename.replace(' ','-') + "-"
    else:
        filename = ""

    filename = filename[:30]

    _ , file_extension = os.path.splitext(org_filename)
    return f"{filename}{uuid.uuid4()}{file_extension}" 

def get_task_fn(user_id : str):
    '''Gets the task filename for the user'''
    return make_filename(FOLDER, user_id)

def summary_conversation_for_user(user_id:int):
    '''Returns a summary of the conversation for the user'''
    conv = get_conversation(user_id)
    return summary_conversation(conv)

def summary_conversation(conv):
    '''Returns a summary of the conversation'''
    media_count = 0
    prompt_count = 0
    caption_count = 0
    for m in conv['messages']:
        if m['kind'] == 'media':
            media_count += 1
            if m.get('text',None) is not None:
                if not m['text'].strip() == '':
                    caption_count +=1
        if m['kind'] == 'text':
            prompt_count +=1
    return prompt_count, media_count, caption_count


def validate_conversation(user_id: str, check_preview : bool = False):
    '''Validates the conversation for the user'''
    conv = get_conversation(user_id)
    prompt_count, media_count, caption_count = summary_conversation(conv)
    status = True
    message = ""
    if (prompt_count == 0 and caption_count==0) or media_count==0:
            message = "For a blog post, you need at least one prompt (or caption) and one media file"
            status = False

    if check_preview:
        if conv.get("contents","") == "":
            message += "\nPlease generate a preview before publishing using /make"
            status = False

    return status, message



def clear_conversation(user_id : str):
    '''Clears the conversation for the user'''
    if os.path.exists(make_filename(FOLDER, user_id)):
        shutil.rmtree(make_filename(FOLDER, user_id))
    

def edit_message(user_id:str, message_id:str, new_prompt:str):
    '''Edits the message for the user'''
    conv = get_conversation(user_id)
    for m in conv['messages']:
        if m['id'] == message_id:
            m['text'] = new_prompt
    save_conversation(user_id, conv)
    
def save_conversation(user_id, conv):

    with open(make_filename(FOLDER,user_id,"conversation.json"),'w') as f:
        json.dump(conv, f)

def show_conversation_as_list(user_id:str):
    '''Shows the conversation for the user as a list'''
    conv = get_conversation(user_id)
    reply = []
    for i,m in enumerate(conv['messages']):
        if m['kind'] == 'text':
            reply.append(str(i+1) +". Prompt:" + m['text'])
        elif m['kind'] == 'media':
            reply.append(str(i+1)+". Media")
            if m.get('text',None) is not None:
                reply[-1] += ':'+m['text'] 
        else:
            pass

    if get_status(user_id) != "Draft":
        title_item = len(reply) +1 
        contents_item = len(reply) + 2

        reply.append(f"{title_item}. Title: "+get_title(user_id))
        reply.append(f"{contents_item}. Contents: "+get_contents(user_id)[:50]+"...")
    else:
        title_item = 9999
        contents_item = 9999

       
    return reply, title_item, contents_item

# add functions to get and set the status of the conversation
def get_status(user_id:str):
    '''Gets the status of the conversation for the user'''
    conv = get_conversation(user_id)
    return conv['status']

def set_status(user_id:str, status:str):
    '''Sets the status of the conversation for the user'''
    conv = get_conversation(user_id)
    # validate the status as either Draft, Published or Generating or Preview
    if status not in ['Draft', 'Published', 'Generating', 'Preview']:
        raise Exception("Invalid status")
    conv['status'] = status
    save_conversation(user_id, conv)


def show_conversation(user_id:str):
    '''Shows the conversation for the user'''
    conv = get_conversation(user_id)
    reply, title_item, content_item = show_conversation_as_list(user_id)

    result = f"Status: {conv['status']}\n" + "\n".join(reply)
    if result.strip()=="":
        result = "No prompts or media yet"
    return result, title_item, content_item



def remove_item(user_id:str, item:str):
    '''Removes the item from the conversation for the user'''
    success = True
    conv = get_conversation(user_id)

    try:
        item_int = int(item)-1
        if item_int < len(conv['messages']):
            del conv['messages'][item_int]
            save_conversation(user_id, conv)
        else:
            success = False
    except:
        success = False
    return success


def add_to_conversation(user_id : str , message_id, text: str , image_file = None):
    '''Adds to the conversation for the user'''
    is_new = False
    if not os.path.exists(make_filename(FOLDER, user_id)):
        os.mkdir(make_filename(FOLDER, user_id))
        is_new = True

    if os.path.exists(make_filename(FOLDER, user_id,"conversation.json")):
        try:
            with open(make_filename(FOLDER, user_id,"conversation.json")) as f:
                conversation = json.load(f)
        except:
            conversation = new_convesation(user_id)
            is_new = True
    else:
        conversation = new_convesation(user_id)
        is_new

    conversation['messages'].append({"time":time.time(), "kind":"text", "text":text, "id":message_id})
    
    if image_file is not None:
        
        filename = make_sane_filename(image_file, text)
        with open(image_file,"rb") as f:
            contents = f.read()  

        with open(make_filename(FOLDER, user_id, filename), "wb") as f:
            f.write(contents)

        conversation['messages'][-1]['filename'] = filename   
        conversation['messages'][-1]['kind'] = 'media'   

    
    save_conversation(user_id, conversation)

    return {"is_new":is_new}

def get_conversation(user_id : str):
    '''Gets the conversation for the user'''
    conversation = new_convesation(user_id)
    try:
        fn = make_filename(FOLDER, user_id,"conversation.json")
        with open(fn) as f:
            text = f.readlines()
            conversation = json.loads("".join(text))
    except Exception as e:
        pass
    return conversation



def make_description(conv):
    '''Makes a description for the conversation'''
    description = []
    for m in conv['messages']:
        if m['kind'] == 'text':
            description.append(m.get('text',''))
    return " ".join(description)[:15]

def process_blog(user_id : str, queue:queue.Queue):
    '''Processes the blog for the user'''

    conv = get_conversation(user_id)
    set_status(user_id, 'Submitted')
    save_conversation(user_id, conv)


    #fifo = make_filename("./","fifo")
    #if not os.path.exists(fifo):
    #    os.mkfifo(fifo)
    #f = open(fifo, "w")
#
    #
    #f.write(f"preview,{user_id}\n")
    #f.flush()
    queue.put(("preview",user_id))

def publish_blog(user_id : str, queue:queue.Queue):
    '''Publishes the blog for the user'''

    conv = get_conversation(user_id)
    conv['status'] = 'Published'
    save_conversation(user_id, conv)


    #fifo = make_filename("./","fifo")
    #if not os.path.exists(fifo):
    #    os.mkfifo(fifo)
    #f = open(fifo, "w")

    
    #f.write(f"publish,{user_id}\n")
    #f.flush()
    queue.put(("publish",user_id))

def get_contents(user_id:str):
    '''Gets the preview text for the user'''
    conv = get_conversation(user_id)
    return conv.get('contents','')

def get_title(user_id:str):
    '''Gets the title for the user'''
    conv = get_conversation(user_id)
    return conv.get('title','')


def set_title(user_id:str,  title_text:str):
    '''Sets the title for the user'''
    try:
        title_text = title_text.strip()
        conv = get_conversation(user_id)
        conv['title'] = title_text
        save_conversation(user_id, conv)
        return True
    except:
        return False

def set_contents(user_id:str,  contents_text:str):
    '''Edits the preview text for the user'''
    try:
        contents_text = contents_text.strip()
        conv = get_conversation(user_id)
        conv['contents'] = contents_text
        save_conversation(user_id, conv)
        return True
    except:
        return False

def stash(user_id:str):
    '''Stashes the conversation for the user'''
    stash_parent = make_filename(STASH_FOLDER,user_id)
    if not os.path.exists(stash_parent):
        os.mkdir(stash_parent)

    original = make_filename(FOLDER, user_id)
    conv = get_conversation(user_id)

    if 'stash_token' in conv:
        token = conv['stash_token']
    else:
        token = str(uuid.uuid4())
        conv['stash_token'] = token

    save_conversation(user_id, conv)

    stash_folder = make_filename(STASH_FOLDER,user_id, token )
    if os.path.exists(stash_folder):
        shutil.rmtree(stash_folder)

    shutil.move(original, stash_folder)
    return token


def stash_list(user_id:str):
    '''Lists the stashes for the user'''
    dirpath = STASH_FOLDER+"/"+str(user_id)
    paths = sorted(Path(dirpath).iterdir(), key=os.path.getmtime)
    l = []
    for i,p in enumerate(paths):
        with open(str(p)+"/conversation.json") as f:
            conv = json.load(f)
        text = ""
        if 'title' in conv:
            text = conv['title']
        elif 'contents' in conv:
            text = conv['contents']
        else:
            text = make_description(conv)

        l.append(f"{i+1}. {text[:30]} ({conv['status']})")
    return "\n".join(l)





def unstash(user_id:str, taskno:int):
    '''Unstashes the conversation for the user'''
    taskno = int(taskno)
    clear_conversation(user_id)
    stash_parent = make_filename(STASH_FOLDER,user_id)
    if not os.path.exists(stash_parent):
        os.mkdir(stash_parent)

    target = make_filename(FOLDER, user_id)
    dirpath = STASH_FOLDER+"/"+str(user_id)
    paths = sorted(Path(dirpath).iterdir(), key=os.path.getmtime)

    unstash_folder = paths[taskno-1]

    shutil.move(str(unstash_folder), target)


def delete_stash(user_id:str, taskno:int):
    '''Deletes the stash for the user'''
    taskno = int(taskno)
    stash_parent = make_filename(STASH_FOLDER,user_id)
    if not os.path.exists(stash_parent):
        os.mkdir(stash_parent)

    dirpath = STASH_FOLDER+"/"+str(user_id)
    paths = sorted(Path(dirpath).iterdir(), key=os.path.getmtime)

    unstash_folder = paths[taskno-1]

    shutil.rmtree(str(unstash_folder))


def edit_item(user_id:str, taskno:int, text:str):
    '''Edits the item for the user'''
    try:
        taskno = int(taskno)
        conv = get_conversation(user_id)
        conv['messages'][taskno-1]['text'] = text
        save_conversation(user_id, conv)
        return True
    except Exception as e:
        return False

