# %%
import os 
from litellm import completion
import base64
from urllib.parse import urlparse

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def get_image_content(image_path):
    # Check if the path is a URL
    is_url = bool(urlparse(image_path).scheme)
    
    if is_url:
        return {"url": image_path}
    else:
        # Local file - encode as base64
        base64_image = encode_image(image_path)
        return {"url": f"data:image/jpeg;base64,{base64_image}"}

# Example usage
image_path = input("Enter the image path: Either a URL or a local path to an image")
# image_path = "path/to/local/image.jpg"  # Uncomment for local image

response = completion(
    model="gpt-4o-mini",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "What's in this image?"
                },
                {
                    "type": "image_url",
                    "image_url": get_image_content(image_path)
                }
            ]
        }
    ],
)

import textwrap

output_text = response.choices[0].message.content
wrapped_text = textwrap.fill(output_text, width=50)
print(wrapped_text)

# %%
# print(response.choices[0].message.content)
