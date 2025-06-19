"""
Friendli AI LLM API Client for Processing Semantic Search Results
"""

import os
import json
import requests
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

class FriendliLLMAPI:
    def __init__(self):
        self.api_key = os.getenv('FRIENDLI_API_KEY')
        self.endpoint_id = os.getenv('FRIENDLI_LLM_ENDPOINT_ID', 'depkg9bk8f3in12')  # Default from provided info
        self.base_url = "https://api.friendli.ai/dedicated/v1/chat/completions"
        
        if not self.api_key:
            raise ValueError("FRIENDLI_API_KEY environment variable not set")
    
    def generate_response(self, prompt, system_prompt=None, max_tokens=500, temperature=0.7):
        """
        Generate a response using Friendli AI LLM API
        
        Args:
            prompt (str): User prompt/question
            system_prompt (str, optional): System prompt to guide the model's behavior
            max_tokens (int, optional): Maximum tokens to generate
            temperature (float, optional): Temperature for response generation
            
        Returns:
            dict: Response from the API
        """
        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        # Prepare request body
        data = {
            "model": self.endpoint_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        # Print request details for debugging
        print(f"LLM API - Request URL: {self.base_url}")
        print(f"LLM API - Headers: {headers}")
        print(f"LLM API - Messages: {messages}")
        print(f"LLM API - Endpoint ID: {self.endpoint_id}")
        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=data
            )
            
            # Print response details for debugging
            print(f"Status code: {response.status_code}")
            print(f"Response headers: {response.headers}")
            print(f"Response content: {response.text[:200]}...")
            
            # Check for successful response
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Error calling Friendli LLM API: {str(e)}"
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
    if __name__ == "__main__":
        try:
            friendli_llm = FriendliLLMAPI()
            response = friendli_llm.generate_response(
                prompt="What are the key features of the Qwen/QwQ-32B model?",
                system_prompt="You are a helpful AI assistant."
            )
            print(json.dumps(response, indent=2))
        except Exception as e:
            print(f"Error: {e}")

main()
