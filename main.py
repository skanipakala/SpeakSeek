import os
import json
import shutil
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
from pydantic import BaseModel
from pathlib import Path
import weaviate
import uuid
import openai
from dotenv import load_dotenv
from typing import Optional, List
from friendli_whisper_api import FriendliWhisperAPI

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="SpeakSeek", description="Audio transcription and question answering API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Root endpoint to serve the homepage
@app.get("/")
async def read_root():
    return FileResponse("static/index.html")

# Configure OpenAI API
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize the Friendli Whisper API client
friendli_client = FriendliWhisperAPI()

# Setup data directories
UPLOAD_DIR = Path("./uploaded_audio")
TRANSCRIPTS_DIR = Path("./transcripts")

# Create directories if they don't exist
UPLOAD_DIR.mkdir(exist_ok=True)
TRANSCRIPTS_DIR.mkdir(exist_ok=True)

# Initialize Weaviate client (using embedded mode for simplicity)
client = weaviate.Client(
    embedded_options=weaviate.embedded.EmbeddedOptions()
)

# Define schema for Weaviate if it doesn't exist
def setup_weaviate_schema():
    try:
        # Check if schema exists
        schema = client.schema.get()
        if not any(cls["class"] == "AudioTranscript" for cls in schema["classes"]):
            # Create schema for audio transcripts
            class_obj = {
                "class": "AudioTranscript",
                "description": "Transcripts from audio files",
                "properties": [
                    {
                        "name": "conversation_id",
                        "dataType": ["string"],
                        "description": "Unique identifier for the conversation"
                    },
                    {
                        "name": "content",
                        "dataType": ["text"],
                        "description": "Transcribed text content"
                    },
                    {
                        "name": "timestamp",
                        "dataType": ["number"],
                        "description": "Timestamp in the audio (in seconds)"
                    }
                ],
                "vectorizer": "text2vec-openai"
            }
            client.schema.create_class(class_obj)
    except Exception as e:
        print(f"Error setting up Weaviate schema: {str(e)}")
        # Continue anyway, as we might be using an external Weaviate instance

# Call the setup function
setup_weaviate_schema()

# Models
class QuestionRequest(BaseModel):
    conversation_id: str
    question: str

class TranscriptionResponse(BaseModel):
    conversation_id: str
    status: str
    message: str

class AnswerResponse(BaseModel):
    answer: str
    relevant_contexts: List[str]

# Helper function to chunk text for vectorization
def chunk_text(text, chunk_size=500):
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0
    
    for word in words:
        if current_length + len(word) + 1 > chunk_size and current_chunk:  # +1 for space
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_length = len(word)
        else:
            current_chunk.append(word)
            current_length += len(word) + 1  # +1 for space
    
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    return chunks

# Helper function to vectorize transcript text
def vectorize_transcript(conversation_id, transcript_text):
    chunks = chunk_text(transcript_text)
    
    for i, chunk in enumerate(chunks):
        # Create a unique object with the chunk
        object_uuid = str(uuid.uuid4())
        properties = {
            "conversation_id": conversation_id,
            "content": chunk,
            "timestamp": i  # Using index as a simple timestamp for now
        }
        
        # Add object to Weaviate
        try:
            client.data_object.create(
                data_object=properties,
                class_name="AudioTranscript",
                uuid=object_uuid
            )
        except Exception as e:
            print(f"Error adding chunk to Weaviate: {str(e)}")

@app.post("/upload-audio", response_model=TranscriptionResponse)
async def upload_audio(
    file: UploadFile = File(...),
    conversation_name: str = Form(...)
):
    # Check if the file is an audio file
    allowed_extensions = [".mp3", ".wav", ".m4a", ".flac", ".ogg"]
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file format. Allowed formats: {', '.join(allowed_extensions)}"
        )
    
    # Generate a conversation ID
    conversation_id = f"{conversation_name.replace(' ', '_')}_{uuid.uuid4().hex[:8]}"
    
    # Save the uploaded file
    audio_path = UPLOAD_DIR / f"{conversation_id}{file_ext}"
    
    try:
        # Ensure directories exist
        UPLOAD_DIR.mkdir(exist_ok=True)
        TRANSCRIPTS_DIR.mkdir(exist_ok=True)
        
        # Save the uploaded file
        with open(audio_path, "wb") as buffer:
            content = await file.read()
            if not content:
                raise HTTPException(status_code=400, detail="Empty audio file")
            buffer.write(content)
        
        # Reset file position for potential future read operations
        await file.seek(0)
        
        print(f"File saved at: {audio_path}")
        print(f"File size: {os.path.getsize(audio_path)} bytes")
        
        # Transcribe using Friendli Whisper API
        transcription_result = friendli_client.transcribe_audio(str(audio_path))
        
        # Extract transcript text
        if "text" in transcription_result:
            transcript_text = transcription_result["text"]
            
            # Save transcript to file
            transcript_path = TRANSCRIPTS_DIR / f"{conversation_id}.json"
            with open(transcript_path, "w") as f:
                json.dump({
                    "conversation_id": conversation_id,
                    "transcript": transcript_text,
                    "raw_result": transcription_result
                }, f, indent=2)
                
            # Vectorize the transcript
            vectorize_transcript(conversation_id, transcript_text)
            
            return {
                "conversation_id": conversation_id,
                "status": "success",
                "message": "Audio uploaded, transcribed, and vectorized successfully"
            }
        else:
            raise HTTPException(
                status_code=500, 
                detail=f"Transcription failed: No text in result: {transcription_result}"
            )
            
    except Exception as e:
        if audio_path.exists():
            os.remove(audio_path)
        raise HTTPException(status_code=500, detail=f"Error processing audio: {str(e)}")

@app.post("/ask-question", response_model=AnswerResponse)
async def ask_question(request: QuestionRequest):
    try:
        # Search for relevant contexts in Weaviate
        query_result = client.query.get(
            "AudioTranscript", 
            ["content", "conversation_id"]
        ).with_where({
            "path": ["conversation_id"],
            "operator": "Equal",
            "valueString": request.conversation_id
        }).with_near_text({
            "concepts": [request.question]
        }).with_limit(3).do()
        
        relevant_contexts = []
        if query_result and "data" in query_result and "Get" in query_result["data"] and "AudioTranscript" in query_result["data"]["Get"]:
            relevant_contexts = [item["content"] for item in query_result["data"]["Get"]["AudioTranscript"]]
        
        if not relevant_contexts:
            # If no context found, try to load from transcript file
            transcript_path = TRANSCRIPTS_DIR / f"{request.conversation_id}.json"
            if transcript_path.exists():
                with open(transcript_path, "r") as f:
                    data = json.load(f)
                    if "transcript" in data:
                        relevant_contexts = [data["transcript"]]
        
        if not relevant_contexts:
            return {
                "answer": "I couldn't find any relevant information for your question.",
                "relevant_contexts": []
            }
        
        # Create a prompt with the retrieved contexts
        context_str = "\n".join([f"Context {i+1}: {ctx}" for i, ctx in enumerate(relevant_contexts)])
        
        prompt = f"""
        Based on the following transcription from an audio file, please answer this question:
        
        Question: {request.question}
        
        {context_str}
        
        Please provide a concise and accurate answer based only on the information provided in the contexts.
        """
        
        # Get answer from OpenAI
        response = openai.chat.completions.create(
            model="gpt-4",  # or another appropriate model
            messages=[
                {"role": "system", "content": "You are a helpful assistant that answers questions based on audio transcripts."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500
        )
        
        answer = response.choices[0].message.content
        
        return {
            "answer": answer,
            "relevant_contexts": relevant_contexts
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
