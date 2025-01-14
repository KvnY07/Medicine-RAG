import sys
import logging
import json
import os
from dotenv import load_dotenv, find_dotenv

if './' not in sys.path:
    sys.path.append('./')

load_dotenv()

ENV_QUESION_NUM = "ENV_QUESION_NUM"

LLM_DIAG_SEP = "\n\n~~~~--------~~~~\n\n"
LLM_DIAG_LED = "~~~~"
LLM_DIAG_ROL = ":::: "

def _get_root_dir():
    root_dir = os.path.abspath(os.path.dirname(find_dotenv()))  
    return root_dir

def _json_loads_repair(response_json_string):
    import json_repair
    ret = json_repair.repair_json(response_json_string, return_objects=True)
    return ret

def get_chat_messages(system_prompt, user_prompt):
    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": user_prompt
        },
    ]
    return messages

def set_question_num(quetion_num):
    os.environ[ENV_QUESION_NUM] = str(quetion_num)

def get_question_num():
    question_num = int(os.environ.get(ENV_QUESION_NUM, "0"))   
    return question_num 

def get_next_question_num():
    question_num = get_question_num()
    question_num += 1
    set_question_num(question_num)
    return question_num


def save_llm_diag_messages(messages, response, model="gpt4-o", top_p=0.8, temperature=0.2, max_tokens=None, prefix=None, is_json_response=True, question_num=None):
    try:
        if question_num is None:
            question_num = get_question_num()
        output_dir = os.path.join(_get_root_dir(), f"_work/llm_dialogs")
        os.makedirs(output_dir, exist_ok=True)

        llmfname = os.path.join(output_dir, f"llm_{prefix}_q{question_num}.txt")

        logging.info(f"SLD: last llm_diag saved at {llmfname}")
        with open(llmfname, 'w', encoding='utf-8') as f:
            for message in messages:
                if isinstance(message, dict):
                    for key, val in message.items():
                        f.write(f"{LLM_DIAG_LED}{key}{LLM_DIAG_ROL}{val}\n")
                    f.write("\n")
                else:
                    f.write(str(message) + "\n")
            f.write(LLM_DIAG_SEP)

            # response.choices[0].message.content
            if hasattr(response, "choices"):
                response = response.choices[0].message.content
            json.dump(response, f, ensure_ascii=False, indent=4)
            f.write(LLM_DIAG_SEP)

            dict_extra = {"top_p": top_p,
                          "temperature": temperature,
                          "is_json_response": is_json_response,
                          "model": model,
                          "ver": 1.1, 
                          "max_token": max_tokens}
            json.dump(dict_extra, f, ensure_ascii=False, indent=4)            

        logging.info(f"{llmfname} saved")
    except Exception as ex:
        logging.exception(ex)

def save_llm_diag_prompt(prompt, response, system_prompt=None, model="gpt4-o", top_p=0.8, temperature=0.2, prefix=None, is_json_response=True, question_num=None):
    if system_prompt is None:
        system_prompt = ""
    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": prompt
        },
    ]
    return save_llm_diag_messages(messages, response, model=model, top_p=top_p, temperature=temperature, prefix=prefix, is_json_response=is_json_response, question_num=question_num)

def load_llm_diag(filename):
    file_content = ""
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    file_content = "".join(lines)
    
    ma = file_content.split(LLM_DIAG_SEP)
    if len(ma) != 3:
        raise ValueError("Not right format")

    message_raw = ma[0].strip()
    answer_raw = ma[1].strip()
    extra_raw = ma[2].strip()

    raw_messages = message_raw.split(LLM_DIAG_LED)
    messages = []
    role, role_msg = None, None
    for ndx, raw_message in enumerate(raw_messages):
        if len(raw_message) == 0 or raw_message.find(LLM_DIAG_ROL) == -1:
            continue
        part1, part2 = raw_message.split(LLM_DIAG_ROL)
        if part1 == "role":
            role = part1
            role_msg = part2.strip() 
        elif part1 == "content":
            content = part1
            content_msg = part2.strip()

            dicm = {}
            dicm[role] = role_msg
            dicm[content] = content_msg
            messages.append(dicm)
        else:
            raise ValueError(f"what? {raw_message}")

    try:
        answer = json.loads(answer_raw)  # json output 
    except: # noqa 
        answer = answer_raw.strip()  # might be string (if no json output required)

    extra = _json_loads_repair(extra_raw)
    if not isinstance(extra, dict):
        raise ValueError("not right format")
    
    if extra["ver"] < 1.0:
        raise ValueError("ver is not correct")
    return messages, answer, extra 
