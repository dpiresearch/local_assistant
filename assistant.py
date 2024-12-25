import openai
import base64
import os
import subprocess
import shutil
import time
import ollama
from typing import Optional, List, Any

#
# Environment variables to set
#
# DONE_PATH
# DISPLAY_PATH
# OUTPUT_DIRECTORY
# AZURE_OPENAI_API_KEY
# AZURE_OPENAI_ENDPOINT
# AZURE_OPENAI_API_VERSION
# AZURE_OPENAI_MODEL
# MONITOR_START_TOKEN
# MONITOR_END_TOKEN

# Read the OpenAI API key from an environment variable
openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
openai.api_type = "azure"
openai.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://ada-garageweek-experiment.openai.azure.com/")
openai.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-01-preview")

GEN_PROMPT=["Determine if what you are seeing in the attached image is one of the following\
    1. Looking at code\
    2. Doing research\
    3. Looking at a production issue\
    4. Wasting time",
    "Please summarize the attached file"
]

CODE_PROMPT="If you are looking at code, tell the user 'I think you are looking at code' and output the following fields: 1. What project is the code related to.  The field name should be called 'Project' 2. What is the function of the code the user is looking at.  The field name should be called 'Code Summary:'"
RESEARCH_PROMPT="If you are doing research, tell the user ' I think you are doing research' and output the following fields 1. A one-liner summarizing the field the user is research.  The field should be called 'Synopsis' 2. A more detailed description of the research, including links to other web pages related to the research.  This field should be called 'Description'."
PRODUCTION_PROMPT="If you are looking at a production issue, tell the user 'Looks like you are looking at a production issue.  Do you want me to create a Jira ticket?'.  You should determine and output the following fields based on what you see in the image: 1. Summary 2. Description 3. Severity 4. Priority 5. Component"
WASTING_PROMPT="If you are wasting time, you should tell the user 'You are just wasting time'"

# Function to encode the image
def encode_image(image_path: str) -> str:
    """Encode the image at the given path to base64 format."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def summarize_text(text: str) -> str:
    """Summarize the provided text using OpenAI's chat completion."""
    response = openai.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_MODEL", "ada-gpt4o"),
        messages=[{"role": "user", "content": f"Please summarize the following text: {text}"}]
    )
    return response.choices[0].message.content

def analyze_image(image_path: str) -> str:
    """Analyze the provided image using OpenAI's vision model."""
    with open(image_path, "rb") as image_file:
        response = openai.Image.create(
            model=os.getenv("AZURE_OPENAI_MODEL", "ada-gpt4o"),
            file=image_file
        )
    return response['data'][0]['text']  # Adjust based on the actual response structure

accum_vision = 0
attempts_vision = 0

def call_vision_model(image_file: str) -> str:
    """Call the vision model with the provided image file."""
    global accum_vision, attempts_vision
    base64_image = encode_image(image_file)
    start_time = time.time()
    
    response = openai.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_MODEL", "ada-gpt4o"),
        messages=[
            {
                "role": "user", "content": [
                    {
                        "type": "text",
                        "text": f"{GEN_PROMPT[0]} {CODE_PROMPT} {RESEARCH_PROMPT} {PRODUCTION_PROMPT} {WASTING_PROMPT}",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        },
                    },
                ],
            }
        ]
    )

    duration_time = time.time() - start_time
    accum_vision += duration_time
    attempts_vision += 1
    print(f"call_vision execution time: {duration_time:.2f} seconds")
    print(f"call_vision average: {accum_vision / attempts_vision:.2f} seconds")
    
    return response.choices[0].message.content
   

def find_latest_png() -> Optional[str]:
    """Find the most recently modified PNG file in the specified directory."""
    monitor_start_token = os.getenv("MONITOR_START_TOKEN", "monitor")
    monitor_end_token = os.getenv("MONITOR_END_TOKEN", ".png")
    output_directory = os.getenv("OUTPUT_DIRECTORY", "/Users/dpang/.screenpipe/output/")
    latest_file = None
    latest_time = 0

    for root, _, files in os.walk(output_directory):
        for file in files:
            if file.lower().startswith(monitor_start_token) and file.lower().endswith(monitor_end_token):
                full_path = os.path.join(root, file)
                mod_time = os.path.getmtime(full_path)
                
                if mod_time > latest_time:
                    latest_file = full_path
                    latest_time = mod_time

    return latest_file

def send_notification(title: str, message: str) -> None:
    """Send a notification to macOS.

    Args:
        title (str): The title of the notification.
        message (str): The message content of the notification.
    """
    try:
        # Use osascript to send a notification
        subprocess.run(["osascript", "-e", f'display notification "{message}" with title "{title}"'])
        print(f"Notification sent: {title} - {message}")
    except Exception as e:
        print(f"Failed to send notification: {e}")

model_timings = {
    'llama3.2-vision': {'accum_time': 0.0, 'attempts': 0}
}

def call_ollama_models(image_file: str, model: str = 'llama3.2-vision') -> Any:
    """Call the Ollama chat model with the provided image file and prompts.

    Args:
        image_file (str): The path to the image file to analyze.
        model (str): The model to use for the chat. Default is 'llama3.2-vision'.

    Returns:
        Any: The response from the Ollama chat model.
    """
    if model not in model_timings:
        model_timings[model] = {'accum_time': 0.0, 'attempts': 0}
        print(f"Creating new timing entry for model {model} ")

    start_time = time.time()
    response = ollama.chat(
        model=model,
        messages=[{
            'role': 'user',
            'content': f"{GEN_PROMPT[0]} {CODE_PROMPT} {RESEARCH_PROMPT} {PRODUCTION_PROMPT} {WASTING_PROMPT}",
            'images': [image_file]
        }]
    )
    end_time = time.time()
    duration_time = end_time - start_time
    print(f"call_ollama execution time for {model}: {duration_time:.2f} seconds")  # Print the execution time

    # Update timing statistics for the specified model
    model_timings[model]['accum_time'] += duration_time
    model_timings[model]['attempts'] += 1
    average_time = model_timings[model]['accum_time'] / model_timings[model]['attempts']
    print(f"call_ollama average time for {model}: {average_time:.2f} seconds")  # Print the average time
    
    return response.message.content
# Example usage
#if __name__ == "__main__":
#    send_notification("Test Notification", "This is a test message from Python!") 
if __name__ == "__main__":

    image_file = [
       "/Users/dpang/Desktop/ELCReceipt2024.png",
       "/Users/dpang/Desktop/work1.png", # research
       "/Users/dpang/Desktop/code1.png", # code
       "/Users/dpang/Desktop/research1.png", # research
       "/Users/dpang/Desktop/waste1.png", # wasting time
    ]   

    done_path = os.getenv("DONE_PATH", "/Users/dpang/.screenpipe/done/")
    display_path = os.getenv("DISPLAY_PATH", "/Users/dpang/dev/ada-agent/notif.png")

    while True:
        image_file_to_examine = find_latest_png()
        print(f"AI query on: {image_file_to_examine}")

        # image_analysis = analyze_image("/Users/dpang/Desktop/ELCReceipt2024.png")  # Replace with your image path
        image_analysis = call_vision_model(image_file_to_examine)  # Replace with your image path
        
        # Grab the first line of image_analysis
        first_line = image_analysis.splitlines()[0] if isinstance(image_analysis, str) else image_analysis[0]
            # Create notif_message by removing the first line from image_analysis
        if isinstance(image_analysis, str):
            notif_message = "\n".join(image_analysis.splitlines()[1:])  # Join remaining lines
        else:
            notif_message = image_analysis[1:]  # Remove the first element from the list

        print("First Line of Image Analysis:", first_line)
        send_notification(first_line, notif_message)

        print(f"\n======= Notification ========\n {notif_message}")

        # List of models to iterate over
        models = ['moondream', 'llava-llama3', 'llava', 'llama3.2-vision']

        # Loop through each model and call the call_ollama function
        for model in models:
            ollama_resp = call_ollama_models(image_file_to_examine, model)
            print(f"\n ===== OLLAMA {model} response ====== \n{ollama_resp}\n\n")

        #ollama_resp = call_ollama(image_file_to_examine, "moondream")
        #print(f"\n ===== OLLAMA LLAMA3.2 Vision response ====== \n{ollama_resp}\n\n")

        try:
            # Move the file
            shutil.copy(image_file_to_examine, display_path)
            shutil.move(image_file_to_examine, done_path)
            print(f"File '{image_file_to_examine}' moved to '{done_path}' successfully.")
        except Exception as e:
            raise Exception(f"An error occurred while moving the file: {e}")

        time.sleep(15)  # Sleep for 10 seconds before the next iteration



