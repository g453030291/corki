import os

import django

from openai import OpenAI

os.environ['DJANGO_SETTINGS_MODULE'] = 'corki.settings'
django.setup()

client = OpenAI(api_key=os.getenv('DEEPSEEK_API_KEY'), base_url="https://api.deepseek.com")

def chat_completions(system, user):
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        stream=False
    )

    return response.choices[0].message.content

if __name__ == '__main__':
    system = "You are a helpful assistant"
    user = "Hello"
    print(chat_completions(system, user))
