import uvicorn
from app.api_endpoints import app  # Importing the FastAPI app instance

if __name__ == "__main__":
    # Start the Uvicorn server to run the API
    uvicorn.run(app, host="0.0.0.0", port=8000)
