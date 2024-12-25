### Local Assistant

LLM based workflow that works locally on your laptop

# To run

Following env variables may have to be set

BASE_DIRECTORY - path where screenpipe writes video files

OUTPUT_DIRECTORY - path where video processor writes frames

DONE_PATH - path where assistant puts processed frames

DISPLAY_PATH - path where the frame currently processed is staged to visualize during debugging

AZURE_OPENAI_API_KEY

AZURE_OPENAI_ENDPOINT

AZURE_OPENAI_API_VERSION

AZURE_OPENAI_MODEL

MONITOR_START_TOKEN - start token of the file we want to process.  For multiple displays, it may be monitor_1, monitor_2, etc...

MONITOR_END_TOKEN - the end suffix for the frame, usually '.png'

% python ./VideoProcessor.py

% python ./assistant.py

# Details

The VideoProcessor uses ffmpeg to split the latest video file into individual frames according to the frame_interval, which is currently set to 5 seconds.

The assistant picks up the latest frame and calls local ollama models to determine what the user is doing.

It'll use osascript to send notifications on the Mac.

