# %%
import os 
from litellm import completion
import base64
from urllib.parse import urlparse
from typing import List, Union
from pathlib import Path
from dotenv import load_dotenv
import httpx
import litellm
load_dotenv(dotenv_path='/home/gyasis/Documents/code/Applied_AI/.env')


def encode_file(file_path):
    """Encode any file to base64, handling both local files and URLs."""
    if urlparse(file_path).scheme in ('http', 'https'):
        # If it's a URL, fetch and encode
        response = httpx.get(file_path)
        response.raise_for_status()  # Ensure the request was successful
        return base64.standard_b64encode(response.content).decode('utf-8')
    else:
        # If it's a local file, read and encode
        with open(file_path, "rb") as file:
            return base64.standard_b64encode(file.read()).decode('utf-8')

def get_content_type(file_path: str) -> str:
    """Determine content type based on file extension"""
    extension = Path(file_path).suffix.lower()
    if extension in {'.mp4', '.avi', '.mov', '.wmv'}:
        return 'video/mp4'
    elif extension in {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}:
        return 'image/jpeg'
    else:
        raise ValueError(f"Unsupported file type: {extension}")

def get_media_content(file_path):
    """Handle both remote and local media files"""
    is_url = bool(urlparse(file_path).scheme)
    
    if is_url:
        return {"url": file_path}
    else:
        base64_content = encode_file(file_path)
        content_type = get_content_type(file_path)
        return {"url": f"data:{content_type};base64,{base64_content}"}

class MediaBatchProcessor:
    def __init__(self, model: str = "openai/gpt-4o-mini", prompt: str = "What's in this media?"):
        self.model = model
        self.prompt = prompt
        self.MAX_BATCH_SIZE = 20
        
        # Validate model for video processing
        if 'video' in prompt.lower() and not model.startswith('gemini/'):
            raise ValueError("Video processing is only supported with Gemini models")

    def _get_media_paths(self, path: Union[str, Path]) -> List[str]:
        """Get list of media paths from a file or directory"""
        path = Path(path)
        if path.is_file():
            return [str(path)]
        
        # List all files with supported extensions
        media_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.mp4', '.avi', '.mov', '.wmv'}
        return [str(f) for f in path.glob('*') if f.suffix.lower() in media_extensions]

    def _create_message_content(self, media_paths: List[str]) -> List[dict]:
        """Create the message content for multiple media files"""
        content = [{"type": "text", "text": self.prompt}]
        
        for path in media_paths:
            media_content = get_media_content(path)
            # print(f"media_content: {media_content}")
            if self.model.startswith("anthropic/"):
                # Ensure the base64 data is correctly extracted
                base64_data = media_content["url"].split(",")[1] 
                # print(f"base64_data: {base64_data}")
                 # Extract base64 data
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": base64_data
                    }
                })
            else:
                content.append({
                    "type": "image_url",
                    "image_url": media_content
                })
            
        return content

    def process_media(self, path: Union[str, Path], max_tokens: int = 8192) -> List[str]:
        """Process media files in batches and return responses"""
        media_paths = self._get_media_paths(path)
        responses = []

        batch_size = min(len(media_paths), self.MAX_BATCH_SIZE)
        
        for i in range(0, len(media_paths), batch_size):
            batch_paths = media_paths[i:i + batch_size]
            messages = [{
                "role": "user",
                "content": self._create_message_content(batch_paths)
            }]
            
            # Prepare common parameters for the completion call
            completion_params = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens
            }
            
            # Add specific parameters for hosted VLLM models
            if self.model.startswith("hosted_vllm/"):
                completion_params.update({
                    "api_base": "https://hosted-vllm-api.co",  # Your hosted VLLM server
                    "temperature": 0.2
                })
            
            # Call the completion method
            response = litellm.completion(**completion_params)
            
            responses.append(response.choices[0].message.content)
            
        return responses

# Example usage:
if __name__ == "__main__":
    # For video processing
    # processor = MediaBatchProcessor(
    #     model="gemini/gemini-1.5-flash",
    #     prompt="Describe what happens in this video"
    # )
    
    # For image processing
    processor = MediaBatchProcessor(
        model="ollama/llava",
        prompt="Describe these images in detail"
    )
    
    results = processor.process_media("/home/gyasis/Downloads/output (1).png")
    
    for i, result in enumerate(results, 1):
        print(f"\nBatch {i} Response:")
        print(result)

# %%
# print(response.choices[0].message.content)
