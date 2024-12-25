import os
import time
import subprocess
from typing import Optional, List
from datetime import datetime, timedelta

#
# Have to set environment variables
# export BASE_DIRECTORY=/Users/dpang/.screenpipe/data
# export FRAME_INTERVAL=5
# export OUTPUT_DIRECTORY=/users/dpang/.screenpipe/output
# 
class VideoProcessor:
    """
    A class to process video files in a subdirectory, extracting frames at regular intervals.
    
    Attributes:
        base_directory (str): Root directory to search for video files
        processed_files (set): Set to track previously processed files
        frame_interval (int): Interval between frame extractions in seconds
    """

    def __init__(
        self, 
        base_directory: str, 
        frame_interval: int = 5, 
        output_directory: Optional[str] = None
    ):
        """
        Initialize the VideoProcessor.

        Args:
            base_directory (str): Directory to search for MP4 files
            frame_interval (int, optional): Interval between frame extractions. Defaults to 5.
            output_directory (Optional[str], optional): Directory to save extracted frames. 
                If None, uses a subdirectory in base_directory.
        """
        self.base_directory = base_directory
        self.processed_files: set = set()
        self.frame_interval = frame_interval
        
        # Set output directory from environment variable or default
        self.output_directory = output_directory or os.environ.get('OUTPUT_DIRECTORY', os.path.join(base_directory, 'extracted_frames'))
        os.makedirs(self.output_directory, exist_ok=True)

    def find_latest_mp4(self) -> Optional[str]:
        """
        Find the most recently modified MP4 file in the base directory and its subdirectories.

        Returns:
            Optional[str]: Path to the latest MP4 file, or None if no file found
        """
        latest_file = None
        latest_time = 0

        for root, _, files in os.walk(self.base_directory):
            for file in files:
                if file.lower().startswith('monitor') and file.lower().endswith('.mp4'):
                    full_path = os.path.join(root, file)
                    mod_time = os.path.getmtime(full_path)
                    
                    if mod_time > latest_time:
                        latest_file = full_path
                        latest_time = mod_time

        return latest_file

    def extract_frame(
        self, 
        video_path: str, 
        timestamp: float, 
        output_filename: Optional[str] = None
    ) -> Optional[str]:
        """
        Extract a frame from a video at a specific timestamp and optionally encode to base64.

        Args:
            video_path (str): Path to the video file
            timestamp (float): Timestamp to extract the frame from
            output_filename (Optional[str], optional): Custom output filename

        Returns:
            Optional[str]: Path to the extracted frame, or None if extraction fails
        """
        try:
            # Generate output filename if not provided
            if not output_filename:
                timestamp_str = f"{int(timestamp):04d}"
                filename = f"{os.path.basename(video_path)}_{timestamp_str}.png"
                output_path = os.path.join(self.output_directory, filename)
            else:
                output_path = output_filename

            print(f"Output path is : {output_path}")
            # Extract frame using ffmpeg
            
            subprocess.run([
                'ffmpeg', 
                '-ss', str(timestamp),  
                '-i', video_path,      
                '-frames:v', '1',      
                '-q:v', '2',           
                output_path
            ], check=True, capture_output=True)
            '''
            subprocess.run([
                'ffmpeg', 
                '-i', video_path,
                'vf fps=1',
                '%04d.png'      
            ], check=True, capture_output=True)
'''
            return output_path

        except subprocess.CalledProcessError as e:
            print(f"Frame extraction error: {e}")
            return None

    def process_video(self, video_path: str) -> List[str]:
        """
        Process a video by extracting frames at regular intervals.

        Args:
            video_path (str): Path to the video file to process

        Returns:
            List[str]: Paths to extracted frames
        """
        # Get video duration
        duration_output = subprocess.check_output([
            'ffprobe', 
            '-v', 'error', 
            '-show_entries', 'format=duration', 
            '-of', 'default=noprint_wrappers=1:nokey=1', 
            video_path
        ]).decode().strip()
        
        video_duration = float(duration_output)

        print(f"Video duration is: {video_duration}")
        # Extract frames
        extracted_frames = []
        current_timestamp = 0.0

        while current_timestamp < video_duration:
            frame_path = self.extract_frame(video_path, current_timestamp)
            if frame_path:
                extracted_frames.append(frame_path)
            
            current_timestamp += self.frame_interval

        return extracted_frames

    def run(self) -> None:
        """
        Main processing method to find and process the latest video file.
        """
        while True:
            latest_video = self.find_latest_mp4()

            if latest_video and latest_video not in self.processed_files:
                print(f"Processing new video: {latest_video}")
                
                try:
                    extracted_frames = self.process_video(latest_video)
                    print(f"Extracted {len(extracted_frames)} frames")
                    
                    # Add to processed files
                    self.processed_files.add(latest_video)

                except Exception as e:
                    print(f"Error processing video {latest_video}: {e}")

            # Wait before checking again
            time.sleep(10)  # Check every 10 seconds

def main():
    # Example usage
    processor = VideoProcessor(
        base_directory=os.environ.get('BASE_DIRECTORY', '/root/.screenpipe/data'), 
        frame_interval=int(os.environ.get('FRAME_INTERVAL', 5)),
        output_directory=os.environ.get('OUTPUT_DIRECTORY', '/root/.screenpipe/output')
    )
    
    try:
        processor.run()
    except KeyboardInterrupt:
        print("Video processing stopped.")

if __name__ == "__main__":
    main()