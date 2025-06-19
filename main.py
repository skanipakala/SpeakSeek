import os
import json
import shutil
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from friendli_llm_api import FriendliLLMAPI
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
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500", "*"],  # Allow the Live Server origin
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
openai_api_key = os.getenv("OPENAI_API_KEY")
openai.api_key = openai_api_key

# Set the environment variable that Weaviate specifically looks for
os.environ["OPENAI_APIKEY"] = openai_api_key

# Initialize API clients
friendli_whisper_client = FriendliWhisperAPI()
friendli_llm_client = FriendliLLMAPI()

# Setup data directories
UPLOAD_DIR = Path("./uploaded_audio")
TRANSCRIPTS_DIR = Path("./transcripts")

# Create directories if they don't exist
UPLOAD_DIR.mkdir(exist_ok=True)
TRANSCRIPTS_DIR.mkdir(exist_ok=True)

# Initialize Weaviate client (using embedded mode for simplicity)
weaviate_headers = {}
if os.getenv("OPENAI_API_KEY"):
    weaviate_headers = {"X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY")}

client = weaviate.Client(
    embedded_options=weaviate.embedded.EmbeddedOptions(),
    additional_headers=weaviate_headers
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
                "vectorizer": "text2vec-openai",
                "moduleConfig": {
                    "text2vec-openai": {
                        "model": "ada",
                        "modelVersion": "002",
                        "type": "text"
                    }
                }
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
    added_chunks = 0
    
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
            added_chunks += 1
        except Exception as e:
            print(f"Error adding chunk to Weaviate: {str(e)}")
    
    print(f"Successfully added {added_chunks} out of {len(chunks)} chunks to Weaviate for conversation {conversation_id}")
    return added_chunks > 0

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
    
    try:
        # Create conversation ID
        conversation_id = f"{conversation_name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:8]}"
        
        # Ensure directories exist
        os.makedirs("uploaded_audio", exist_ok=True)
        os.makedirs("transcripts", exist_ok=True)
        
        # Save uploaded file
        file_path = f"uploaded_audio/{conversation_id}.{file.filename.split('.')[-1]}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Get file size
        file_size = os.path.getsize(file_path)
        print(f"File saved at: {file_path}")
        print(f"File size: {file_size} bytes")
        
        if file_size == 0:
            os.remove(file_path)
            raise HTTPException(status_code=400, detail="Empty audio file uploaded")
        
        transcript_text = ""
        try:
            # Try using the Friendli Whisper API
            whisper_api = FriendliWhisperAPI()
            transcription_result = whisper_api.transcribe_audio(file_path)
            transcript_text = transcription_result.get("text", "")
        except Exception as api_error:
            print(f"Friendli API error: {api_error}")
            print("Using fallback transcription method...")
            
            # FALLBACK: Use a demo transcript file if it exists
            if os.path.exists("transcription.txt"):
                with open("transcription.txt", "r") as f:
                    transcript_text = f.read()
                print("Used fallback transcript file")
            else:
                # Create a simple demo transcript
                transcript_text = f"This is a demo transcript for conversation {conversation_name}. "
                transcript_text += "The Friendli Whisper API endpoint has been terminated. "
                transcript_text += "This is a fallback transcript for demonstration purposes. "
                transcript_text += "You can replace this with actual transcript content in the transcription.txt file."
        
        if not transcript_text:
            raise HTTPException(status_code=500, detail="Failed to transcribe audio")
        
        # Save transcript
        transcript_path = f"transcripts/{conversation_id}.txt"
        with open(transcript_path, "w") as f:
            f.write(transcript_text)
            
        # Vectorize transcript for semantic search
        vectorize_transcript(conversation_id, transcript_text)
        
        return {
            "conversation_id": conversation_id,
            "status": "success",
            "message": "Audio uploaded and processed successfully"
        }
        
    except Exception as e:
        # Log the error
        print(f"Error: {str(e)}")
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
        
        system_prompt = "You are a helpful assistant that answers questions based on audio transcripts. Only use information from the provided contexts to answer the question."
        
        # Get answer from Friendli LLM API
        try:
            response = friendli_llm_client.generate_response(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=500,
                temperature=0.7
            )
            
            # Extract the answer from the response
            if response and "choices" in response and len(response["choices"]) > 0:
                answer = response["choices"][0]["message"]["content"]
            else:
                answer = "I couldn't generate a proper response based on the available information."
                print(f"Unexpected response structure: {response}")
        except Exception as e:
            print(f"Error calling Friendli LLM API: {str(e)}")
            # Fallback to a simple answer based on the contexts
            answer = f"Based on the transcript, I found these relevant sections but couldn't process them further:\n\n{context_str}"
        
        return {
            "answer": answer,
            "relevant_contexts": relevant_contexts
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
