from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import sys
import os
import logging
from datetime import datetime
import uvicorn

# Set up logging
log_directory = "logs"
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_directory, f'image_processing_{datetime.now().strftime("%Y%m%d")}.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Update the module path to reflect the correct directory structure
module_path = os.path.join(os.path.dirname(__file__), '..', '..', 'utils', 'multimodal')
sys.path.append(module_path)
logger.info(f"Added module path: {module_path}")

from multimodal.litellm_image_processing import MediaBatchProcessor, get_content_type, get_media_content, encode_file

class ImageProcessor:
    def __init__(self, model="openai/gpt-4o-mini"):
        logger.info(f"Initializing ImageProcessor with model: {model}")
        self.processor = MediaBatchProcessor(
            model=model,
            prompt="Please read this image carefully and extract all text. Format the text properly maintaining any structure or layout present in the image."
        )
    
    def process_image(self, image_bytes):
        temp_path = "temp_image.png"
        logger.info(f"Saving temporary image to: {temp_path}")
        
        try:
            # Log image size
            image_size = len(image_bytes)
            logger.info(f"Processing image of size: {image_size} bytes")
            
            # Save bytes to temporary file
            with open(temp_path, "wb") as f:
                f.write(image_bytes)
            
            logger.info("Starting image processing with MediaBatchProcessor")
            # Process the image using MediaBatchProcessor's methods
            media_content = get_media_content(temp_path)
            logger.info(f"Media content prepared: {type(media_content)}")
            
            # Process the image
            results = self.processor.process_media(temp_path)
            
            if results:
                logger.info("Successfully processed image")
                logger.debug(f"Raw results: {results}")
                return results[0]
            else:
                logger.warning("No results returned from processor")
                return ""
                
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}", exc_info=True)
            raise Exception(f"Failed to process image: {str(e)}")
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_path):
                logger.info(f"Cleaning up temporary file: {temp_path}")
                os.remove(temp_path)

class ImageCaptureGateway:
    def __init__(self, collector):
        self.collector = collector
        self.app = FastAPI()
        self.setup_routes()
        self.setup_middleware()
        self.templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), 'templates'))

    def setup_middleware(self):
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def setup_routes(self):
        @self.app.post("/process-image/")
        async def process_image(file: UploadFile = File(...)):
            logger.info(f"Received image upload request: {file.filename}")
            logger.info(f"File content type: {file.content_type}")
            
            try:
                # Read the image file
                logger.info("Reading uploaded file contents")
                contents = await file.read()
                
                # Validate content type
                try:
                    content_type = get_content_type(file.filename)
                    logger.info(f"Validated content type: {content_type}")
                except ValueError as e:
                    logger.error(f"Invalid file type: {str(e)}")
                    return JSONResponse(
                        status_code=400,
                        content={"error": "Invalid file type. Please upload a valid image file."}
                    )
                
                # Initialize the processor
                logger.info("Initializing ImageProcessor")
                processor = ImageProcessor()
                
                # Process the image
                logger.info("Starting image processing")
                result = processor.process_image(contents)
                
                # Process the image and send the result to the collector
                self.collector.process_text(result.strip())
                
                # Return the extracted text
                return JSONResponse(content={"text": result.strip()})
            except Exception as e:
                logger.error(f"Error in process_image endpoint: {str(e)}", exc_info=True)
                return JSONResponse(
                    status_code=500,
                    content={"error": f"Failed to process image: {str(e)}"}
                )

        @self.app.post("/process-text/")
        async def process_text(request: Request):
            data = await request.json()
            text = data.get("text", "")
            logger.info(f"Received text input: {text}")
            self.collector.process_text(text)
            return JSONResponse(content={"status": "Text processed successfully"})

        @self.app.get("/", response_class=HTMLResponse)
        async def read_root(request: Request):
            logger.info("Serving root endpoint")
            return self.templates.TemplateResponse("index.html", {"request": request})

        @self.app.on_event("startup")
        async def startup_event():
            logger.info("Starting up FastAPI application")
            logger.info(f"Current working directory: {os.getcwd()}")
            logger.info(f"Python path: {sys.path}")

    # def run(self, host="0.0.0.0", port=5667):
    #     logger.info(f"Starting server on http://{host}:{port}")
    #     uvicorn.run(self.app, host=host, port=port)

    # Use this for HTTPS(necessary for accessing camera in browser on machine(mobile device does not need this))
    def run(self, host="0.0.0.0", port=5667):
        logger.info(f"Starting server on https://{host}:{port}")
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            ssl_certfile="cert.pem",
            ssl_keyfile="key.pem"
        )

# If this script is run directly, start the server
if __name__ == "__main__":
    app_instance = ImageCaptureGateway()
    app_instance.run()
