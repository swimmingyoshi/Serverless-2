#!/usr/bin/env python3
import os
import time
import runpod
import requests
import sys
from urllib.parse import urlparse

# Global variables
API_URL = "http://127.0.0.1:3000/sdapi/v1"
MODEL_DIR = "/workspace/webui/models/Stable-diffusion"

def download_model(url, local_path):
    """Download a model file from URL if it doesn't exist."""
    if os.path.exists(local_path):
        print(f"Model already exists at {local_path}")
        return True
    
    print(f"Downloading model from {url} to {local_path}")
    try:
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        response = requests.get(url, stream=True)
        
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        print(f"Model download complete: {local_path}")
        return True
    except Exception as e:
        print(f"Error downloading model: {e}")
        return False

def get_model_name_from_url(url):
    """Extract model name from URL."""
    parsed_url = urlparse(url)
    return os.path.basename(parsed_url.path)

def check_api_status():
    """Check if the WebUI API is available."""
    try:
        response = requests.get(f"{API_URL}/sd-models", timeout=5)
        if response.status_code == 200:
            return True
        return False
    except:
        return False

def load_model(model_name):
    """Load a specific model in the WebUI."""
    try:
        # Get current model
        response = requests.get(f"{API_URL}/sd-models")
        models = response.json()
        
        # Find the requested model
        model_info = None
        for model in models:
            if model_name in model["title"]:
                model_info = model
                break
        
        if not model_info:
            print(f"Model {model_name} not found in available models")
            return False
            
        # Check if model is already loaded
        options_response = requests.get(f"{API_URL}/options")
        current_model = options_response.json().get("sd_model_checkpoint")
        
        if current_model == model_info["title"]:
            print(f"Model {model_name} is already loaded")
            return True
            
        # Load the model
        print(f"Loading model: {model_info['title']}")
        response = requests.post(
            f"{API_URL}/options", 
            json={"sd_model_checkpoint": model_info["title"]}
        )
        
        if response.status_code == 200:
            print(f"Model {model_name} loaded successfully")
            return True
        else:
            print(f"Failed to load model: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error loading model: {e}")
        return False

def handler(job):
    """Main handler function for RunPod serverless."""
    try:
        print(f"Starting handler with job input: {job.get('input', {})}")
        job_input = job["input"]
        
        # Verify WebUI API is running before proceeding
        if not check_api_status():
            return {"error": "WebUI API is not available. Please check the container logs."}
        
        # Handle model download if URL is provided
        if "model_url" in job_input:
            model_url = job_input["model_url"]
            model_name = job_input.get("model_name", get_model_name_from_url(model_url))
            model_path = os.path.join(MODEL_DIR, model_name)
            
            download_success = download_model(model_url, model_path)
            if not download_success:
                return {"error": "Failed to download model"}
        
        # Load model if specified
        if "model_name" in job_input:
            model_load_success = load_model(job_input["model_name"])
            if not model_load_success:
                return {"error": f"Failed to load model {job_input['model_name']}"}
        
        # Handle the specific endpoint requested
        endpoint = job_input.get("endpoint", "txt2img")
        payload = job_input.get("payload", {})
        
        print(f"Making API request to endpoint: {endpoint}")
        print(f"With payload: {payload}")
        
        # Make the API request with increased timeout
        response = requests.post(
            f"{API_URL}/{endpoint}", 
            json=payload,
            timeout=300  # 5 minute timeout for image generation
        )
        
        if response.status_code != 200:
            return {"error": f"API request failed with status {response.status_code}: {response.text}"}
        
        # Return the results
        return response.json()
    
    except requests.exceptions.Timeout:
        return {"error": "API request timed out. Image generation may be taking too long."}
    except requests.exceptions.ConnectionError as e:
        return {"error": f"Connection error: {str(e)}. WebUI may not be running."}
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Handler error: {e}")
        print(f"Traceback: {error_traceback}")
        return {"error": str(e), "traceback": error_traceback}

# Print system information
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")

# Check if WebUI is available
if check_api_status():
    print("WebUI API is available and ready")
else:
    print("WARNING: WebUI API not detected. Handler may not work correctly.")

# Start the RunPod handler
print("Starting RunPod handler")
runpod.serverless.start({"handler": handler})
