import uuid
import os.path
import json
import time
import shutil
import glob


FOLDER = "./conversations/"
TASK_FOLDER = "./tasks/"



def make_filename(folder, id, filename=""):
    folder = str(folder) + str(id) 
    if filename != "":
        folder += "/" +str(filename)
    return folder

def new_convesation(user_id : int):
    return {"user_id":user_id, "messages":[]}

def make_sane_filename(org_filename, caption):
    keepcharacters = (' ','.','_')
    if caption is not None:
        filename = "".join(c for c in caption if c.isalnum() or c in keepcharacters).rstrip()
        filename = filename.replace(' ','-') + "-"
    else:
        filename = ""

    _ , file_extension = os.path.splitext(org_filename)
    return f"{filename}{uuid.uuid4()}{file_extension}" 


def summary_conversation(conv):
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


def validate_conversation(user_id: str):
    conv = get_conversation(user_id)
    prompt_count, media_count, caption_count = summary_conversation(conv)
    status = True
    message = ""
    if (prompt_count == 0 and caption_count==0) or media_count==0:
            message = "For a blog post, you need at least one prompt (or caption) and one photo"
            status = False

    return status, message



def clear_conversation(user_id : str):
    if os.path.exists(make_filename(FOLDER, user_id)):
        shutil.rmtree(make_filename(FOLDER, user_id))
    

def edit_message(user_id:str, message_id:str, new_prompt:str):
    conv = get_conversation(user_id)
    for m in conv['messages']:
        if m['id'] == message_id:
            m['text'] = new_prompt
    save_conversation(user_id, conv)
    
def save_conversation(user_id, conv):

    with open(make_filename(FOLDER,user_id,"conversation.json"),'w') as f:
        json.dump(conv, f)


def show_conversation(user_id:str):
    conv = get_conversation(user_id)
    reply = []
    for i,m in enumerate(conv['messages']):
        if m['kind'] == 'text':
            reply.append(str(i+1) +". Prompt:" + m['text'])
        elif m['kind'] == 'media':
            reply.append(str(i+1)+". Photo")
            if m.get('text',None) is not None:
                reply[-1] += ':'+m['text'] 
        else:
            pass

    result = "\n".join(reply)
    if result.strip()=="":
        result = "No prompts or photos yet"
    return result

def remove_item(user_id:str, item:str):
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
    conversation = new_convesation(user_id)
    try:
        fn = make_filename(FOLDER, user_id,"conversation.json")
        with open(fn) as f:
            text = f.readlines()
            conversation = json.loads("".join(text))
    except Exception as e:
        print(e)
        pass
    return conversation


def make_description(conv):
    description = []
    for m in conv['messages']:
        if m['kind'] == 'text':
            description.append(m.get('text',''))
    return " ".join(description)[:15]

def process_blog(user_id : str):
    conv = get_conversation(user_id)
    conv['description'] = make_description(conv)
    conv['status'] = 'Submitted'
    save_conversation(user_id, conv)

    original = make_filename(FOLDER, user_id)

    target = make_filename(TASK_FOLDER,user_id, uuid.uuid4()) 
    if os.path.exists(target):
        shutil.rmtree(target)

    shutil.move(original, target)

    clear_conversation(user_id)

    fifo = make_filename(TASK_FOLDER,"fifo")
    if not os.path.exists(fifo):
        os.mkfifo(fifo)
    f = open(fifo, "w")

    f.write(target + "\n")
    f.flush()

def get_tasks(user_id : str):
    blogfolder = make_filename(TASK_FOLDER,user_id)
    globlist = glob.glob(blogfolder+"/*")
    desc_list = []
    for g in globlist:
        with open(g+"/conversation.json") as f:
            conv = json.load(f)
            desc_list.append(conv.get('description','') +'... [' + conv.get('status','UNKNOWN') + ']')
            
    tasklist = [f"{i+1}. %s {z[1]}" % z[0].split("/")[-1][:5]  for i,z in enumerate(zip(globlist, desc_list))]
    return "\n".join(tasklist)
