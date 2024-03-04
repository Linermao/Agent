import google.generativeai as genai
import requests
import re
import scripts.prompts as prompts
import dashscope
from http import HTTPStatus

class OpenAIModel:
    def __init__(self, base_url: str, api_key: str, model: str, temperature: float, max_tokens: int):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def get_model_response(self, prompt: str, base64_image: str):
        content = [
            {
                "type": "text",
                "text": prompt,
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }
            },
        ]
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": content
                }
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        response = requests.post(self.base_url, headers=headers, json=payload).json()
        if "error" not in response:
            usage = response["usage"]
            prompt_tokens = usage["prompt_tokens"]
            completion_tokens = usage["completion_tokens"]
            print(f"Request cost is " 
                  f"${'{0:.2f}'.format(prompt_tokens / 1000 * 0.01 + completion_tokens / 1000 * 0.03)}")
        else:
            return False, response["error"]["message"]
        return True, response["choices"][0]["message"]["content"]

class GeminiModel:
    def __init__(self, api_key: str, model: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)


    def get_model_response(self, task_description, base64_image, last_action):
        task_description = re.sub(r"<task_description>", task_description, prompts.self_explore_task_template)
        text = re.sub(r"<last_action>", last_action, task_description)
        content = [
            {"text": text},
            {
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": base64_image
                }
            },
        ]
        messages = [
            {
                'role':'user',
                'parts': content,
            }
        ]
        response = self.model.generate_content(messages, stream=False)
        return response.text

class QwenModel:
    def __init__(self, api_key: str, model: str):
        self.model = model
        dashscope.api_key = api_key

    def get_model_response(self, prompt: str, image_path: str):
        image = f"file://{image_path}"
        content = [
            {"text": prompt},
            {"image": image},
        ]
        messages = [
            {
                "role": "user",
                "content": content,
            }
        ]
        response = dashscope.MultiModalConversation.call(model=self.model, messages=messages)

        if response.status_code == HTTPStatus.OK:
            return True, response.output.choices[0].message.content[0]["text"]
        else:
            return False, response.message