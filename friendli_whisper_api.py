import os
import requests
from dotenv import load_dotenv
import json
from pathlib import Path

# Load environment variables
load_dotenv()

class FriendliWhisperAPI:
    def __init__(self):
        self.api_key = os.getenv('FRIENDLI_API_KEY')
        self.endpoint_id = os.getenv('FRIENDLI_ENDPOINT_ID', 'dep2zfjfglqfzjb')  # Default from your provided info
        self.base_url = "https://api.friendli.ai/dedicated/v1/audio/transcriptions"
        
        if not self.api_key:
            raise ValueError("FRIENDLI_API_KEY environment variable not set")
    
    def transcribe_audio(self, audio_file_path, language=None, prompt=None):
        """
        Transcribe audio using Friendli Whisper API
        
        Args:
            audio_file_path (str): Path to the audio file
            language (str, optional): Language code (e.g., 'en', 'es')
            prompt (str, optional): Optional prompt to guide the transcription
            
        Returns:
            dict: Transcription response from the API
        """
        # Check if file exists
        audio_path = Path(audio_file_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
        
        # Prepare headers
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Open the file to make sure it exists and is readable
        try:
            file_content = open(audio_path, "rb")
            file_size = os.path.getsize(audio_path)
            print(f"API - Reading file: {audio_path}, Size: {file_size} bytes")
            if file_size == 0:
                raise ValueError(f"File is empty: {audio_path}")
        except Exception as e:
            raise ValueError(f"Error reading audio file: {str(e)}")
            
        # Prepare files and additional form data
        files = {
            "file": (audio_path.name, file_content)
        }
        
        data = {
            "model": self.endpoint_id
        }
        
        # Add optional parameters if provided
        if language:
            data["language"] = language
        if prompt:
            data["prompt"] = prompt
            
        # Print request details for debugging
        print(f"API - Request URL: {self.base_url}")
        print(f"API - Headers: {headers}")
        print(f"API - Data: {data}")
        print(f"API - File name: {audio_path.name}")
        print(f"API - Endpoint ID: {self.endpoint_id}")
        print(f"API - API Key (first 10 chars): {self.api_key[:10]}...")
        print(f"API - Files dictionary keys: {files.keys()}")

        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                files=files,
                data=data
            )
            
            # Close the file after the request
            files["file"][1].close()
            
            # Print response details for debugging
            print(f"Status code: {response.status_code}")
            print(f"Response headers: {response.headers}")
            print(f"Response content: {response.text}")
            
            # Check for successful response
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            # Close the file in case of an exception
            files["file"][1].close()
            error_msg = f"Error calling Friendli API: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg += f" - Details: {error_detail}"
                except ValueError:
                    error_msg += f" - Response text: {e.response.text}"
            print(error_msg)
            raise Exception(error_msg)

# Example usage
def main():
    # Example usage of the API
    transcriber = FriendliWhisperAPI()
    
    # Example path - replace with actual audio file path
    audio_file = "path/to/your/audio/file.mp3"
    
    try:
        result = transcriber.transcribe_audio(audio_file)
        print("Transcription result:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()