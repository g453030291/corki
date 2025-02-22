import os
from typing import Optional, Literal

import django
import requests
from loguru import logger
from sympy import false
from volcenginesdkarkruntime import Ark
from volcenginesdkarkruntime.types.chat.completion_create_params import ResponseFormat

os.environ['DJANGO_SETTINGS_MODULE'] = 'corki.settings'
django.setup()

doubao_api_key = os.getenv('DOUBAO_API_KEY')
client = Ark(api_key=doubao_api_key)
url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

def completions(system_prompts, user_prompts, model="ep-20250215205722-f2z27", image_list=None,
                messages=None, stream: Optional[Literal[False, True]] = False):
    logger.info(f"completions request start")
    if image_list:
        if not isinstance(image_list, list):
            image_list = [image_list]
        contents = [
            {
                "type": "text",
                "text": user_prompts
            }
        ]
        # Append each image to the content list
        for image_url in image_list:
            contents.append({
                "type": "image_url",
                "image_url": {
                    "url": image_url
                }
            })
        completion = requests.post(
            url=url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {doubao_api_key}"
            },
            json={
                "model": "ep-20241207172529-lnrkx",
                "messages": [
                    {
                        "role": "user",
                        "content": contents
                    }
                ]
            }
        )
        logger.info(completion.json())
        return completion.json()['choices'][0]['message']['content']
    elif messages:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=stream
        )
    else:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompts},
                {"role": "user", "content": user_prompts},
            ],
            stream=stream,
            temperature=0.8,
            top_p=0.7,
            frequency_penalty=0.2,
            response_format={'type': 'json_object'}
        )
    logger.info(completion)
    if stream:
        # 流式处理
        full_response = ""
        for chunk in completion:
            if hasattr(chunk.choices[0].delta, 'content'):
                content = chunk.choices[0].delta.content
                if content is not None:
                    print(content, end='', flush=True)  # 实时输出内容
                    full_response += content
        print()  # 换行
        return full_response
    else:
        # 非流式处理
        return completion.choices[0].message.content

if __name__ == '__main__':
    # result = completions(system_prompts="", user_prompts="看一下这两张图片里都有什么", image_list=[
    #     "http://tristana-oss.oss-cn-shanghai.aliyuncs.com/2024/12/07/WeChat4c873b73053bb6a23a0bc16997a951eb.jpg",
    #     "http://tristana-oss.oss-cn-shanghai.aliyuncs.com/2024/12/07/WeChatb1a41731ac954a691f199d7fb3737001.jpg"
    # ])
    result = completions("你是豆包，是由字节跳动开发的 AI 人工智能助手", "常见的十字花科植物有哪些？")
    print(result)
