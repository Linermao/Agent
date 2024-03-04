import sys
import os
import re
import time
from scripts.utils import encode_image, get_image_size, draw_bbox_multi
from scripts.android_controller import select_device, get_elem_list
from scripts.config import load_configs
from scripts.ask_models import OpenAIModel, GeminiModel, QwenModel
# from scripts.real_time import record_audios, to_text
import scripts.prompts as prompts

def run(mllm):

    print("Checking device...")

    # select device
    controller = select_device()
    width, height = controller.get_size()

    print("Please enter the description of the task you want me to complete in a few sentences:")
    # keyboard input
    task_description = input()
    # audio input
    # frames = record_audios()
    # task_description = to_text(frames)

    round_count = 0
    last_action = "None"

    observation_list = []
    thought_list = []
    action_list = []
    summary_list = []

    while round_count < 7:

        round_count += 1
        print(f"ROUND: {round_count}")
        folder_path = f"task/{round_count}"
        os.makedirs(folder_path, exist_ok=True)
        
        screenshot_before_path = controller.get_screenshot("screenshot_before", f"{folder_path}")
        base64_img_before = encode_image(screenshot_before_path)
        i_width, i_height = get_image_size(screenshot_before_path)

        xml_path = controller.get_xml(f"xml", f"{folder_path}")
        elem_list = get_elem_list(xml_path)
        
        screenshot_labeled_path = f"{folder_path}/screenshot_labeled.png"
        draw_bbox_multi(screenshot_before_path, screenshot_labeled_path, elem_list)

        base64_img_before = encode_image(screenshot_labeled_path)

        print("Thinking about what to do in the next step...")

        msg = mllm.get_model_response(task_description, base64_img_before, last_action)
        observation = re.findall(r"Observation: (.*?)$", msg, re.MULTILINE)[0]
        thought = re.findall(r"Thought: (.*?)$", msg, re.MULTILINE)[0]
        action = re.findall(r"Action: (.*?)$", msg, re.MULTILINE)[0]
        last_action = re.findall(r"Summary: (.*?)$", msg, re.MULTILINE)[0]

        print("Observation:")
        print(observation)
        print("Thought:")
        print(thought)
        print("Action:")
        print(action)
        print("Summary:")
        print(last_action)

        if "tap" in action:
            parameter = int(action.split("(")[1].split(")")[0])
            tl, br = elem_list[parameter - 1].bbox
            x, y = (tl[0] + br[0]) // 2, (tl[1] + br[1]) // 2
            controller.tap(x, y)

        elif "type" in action:
            parameter = (action.split("(")[1].split(")")[0])
            controller.type(parameter)

        elif "swipe" in action:
            parameter = action.split("(")[1].split(")")[0]
            area, swipe_dir, dist = parameter.split(",")
            area = int(area)
            swipe_dir = swipe_dir.strip()[1:-1]
            dist = dist.strip()[1:-1]
            tl, br = elem_list[area - 1].bbox
            x, y = (tl[0] + br[0]) // 2, (tl[1] + br[1]) // 2
            controller.swipe(x, y, swipe_dir, dist)

        elif "stop" in action:
            break
        
        observation_list.append(observation)
        thought_list.append(thought)
        action_list.append(action)
        summary_list.append(last_action)

        # wait device
        # time.sleep(2)

    # output
    output_file_name = "task/output.txt"
    with open(output_file_name, 'w') as file:
        file.write("Your command:\n")
        file.write(task_description)
        for observation, thought, action, summary in zip(observation_list, thought_list, action_list, summary_list):
                file.write("Observation:\n")
                file.write(observation + "\n")
                file.write("Thought:\n")
                file.write(thought + "\n")
                file.write("Action:\n")
                file.write(action + "\n")
                file.write("Summary:\n")
                file.write(summary + "\n\n")
    file.close()

    print(f"The steps are written to {output_file_name} successfully. You can check it.")

if __name__ == "__main__":
    
    configs = load_configs()
    if configs["CHOOSE_MODEL"] == "OpenAI":
        mllm = OpenAIModel(base_url=configs["OPENAI_API_BASE"],
                       api_key=configs["OPENAI_API_KEY"],
                       model=configs["OPENAI_API_MODEL"],
                       temperature=configs["TEMPERATURE"],
                       max_tokens=configs["MAX_TOKENS"])
        
    elif configs["CHOOSE_MODEL"] == "Gemini":
        mllm = GeminiModel(api_key=configs["GEMINI_API_KEY"],
                        model=configs["GEMINI_API_MODEL"])
        
    elif configs["CHOOSE_MODEL"] == "Qwen":
        mllm = QwenModel(api_key=configs["QWEN_API_KEY"],
                        model=configs["QWEN_API_MODEL"])
        
    else:
        print(f"ERROR: Unsupported model type {configs['MODEL']}!")
        sys.exit()

    run(mllm)
