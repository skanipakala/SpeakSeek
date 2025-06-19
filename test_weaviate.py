import os
import weaviate
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get OpenAI API key
openai_api_key = os.getenv("OPENAI_API_KEY")

# Set the environment variable that Weaviate specifically looks for
os.environ["OPENAI_APIKEY"] = openai_api_key

print(f"OpenAI API Key (first 4 chars): {openai_api_key[:4]}...")
print(f"Environment OPENAI_APIKEY: {os.environ.get('OPENAI_APIKEY', 'Not set')[:4]}...")

# Initialize Weaviate client
weaviate_headers = {}
if openai_api_key:
    weaviate_headers = {"X-OpenAI-Api-Key": openai_api_key}

client = weaviate.Client(
    embedded_options=weaviate.embedded.EmbeddedOptions(),
    additional_headers=weaviate_headers
)

# Define schema for Weaviate if it doesn't exist
def setup_weaviate_schema():
    try:
        # Check if schema exists
        schema = client.schema.get()
        print(f"Current schema classes: {[cls['class'] for cls in schema.get('classes', []) if 'class' in cls]}")
        
        if not any(cls.get("class") == "TestTranscript" for cls in schema.get("classes", [])):
            # Create schema for test transcripts
            class_obj = {
                "class": "TestTranscript",
                "description": "Test transcript text",
                "properties": [
                    {
                        "name": "content",
                        "dataType": ["text"],
                        "description": "Transcribed text content"
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
            print("Created TestTranscript schema")
    except Exception as e:
        print(f"Error setting up schema: {str(e)}")

# Function to add a test transcript
def add_test_transcript():
    try:
        # Read the transcription.txt file
        with open("transcription.txt", "r") as f:
            transcript_text = f.read()
        
        # Use a small sample for testing
        sample_text = transcript_text[:1000]
        
        # Create a unique object with the text
        object_uuid = str(uuid.uuid4())
        properties = {
            "content": sample_text
        }
        
        # Add object to Weaviate
        print("Adding object to Weaviate...")
        client.data_object.create(
            data_object=properties,
            class_name="TestTranscript",
            uuid=object_uuid
        )
        print(f"Successfully added object with UUID: {object_uuid}")
        return object_uuid
    except Exception as e:
        print(f"Error adding transcript to Weaviate: {str(e)}")
        return None

# Function to test search
def test_search(uuid):
    try:
        # Test a simple query
        query_result = client.query.get(
            "TestTranscript", 
            ["content"]
        ).with_near_text({
            "concepts": ["Spark"]
        }).with_limit(1).do()
        
        print("Search results:")
        print(query_result)
    except Exception as e:
        print(f"Error searching Weaviate: {str(e)}")

# Run the test
if __name__ == "__main__":
    print("Setting up Weaviate schema...")
    setup_weaviate_schema()
    
    print("\nAdding test transcript...")
    uuid = add_test_transcript()
    
    if uuid:
        print("\nTesting search...")
        test_search(uuid)
