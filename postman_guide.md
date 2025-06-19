# SpeakSeek API - Postman Guide

## Setting Up Requests in Postman

### 1. Upload Audio Endpoint

**Endpoint:** `POST http://localhost:8000/upload-audio`

**Request Type:** `multipart/form-data`

**Required Fields:**
- `file`: The audio file to upload (must be a file, not text)
- `conversation_name`: A name for the conversation (text)

**Steps to set up in Postman:**

1. Create a new POST request to `http://localhost:8000/upload-audio`
2. Go to the "Body" tab
3. Select "form-data"
4. Add two key-value pairs:
   - Key: `file`, Value: [Select File] (Important: Click on the dropdown next to the key and select "File")
   - Key: `conversation_name`, Value: "Your Conversation Name"
5. Click "Send"

**Example Response:**
```json
{
  "conversation_id": "Your_Conversation_Name_abc12345",
  "status": "success",
  "message": "Audio uploaded, transcribed, and vectorized successfully"
}
```

### 2. Ask Question Endpoint

**Endpoint:** `POST http://localhost:8000/ask-question`

**Request Type:** `application/json`

**Required Fields:**
```json
{
  "conversation_id": "Your_Conversation_Name_abc12345",
  "question": "What was discussed about project timelines?"
}
```

**Steps to set up in Postman:**

1. Create a new POST request to `http://localhost:8000/ask-question`
2. Go to the "Body" tab
3. Select "raw" and then "JSON" from the dropdown
4. Enter the JSON body with your conversation_id and question
5. Click "Send"

## Common Errors and Solutions

### Missing File Field Error

**Error:**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "file"],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Solution:**
- Make sure you're using "form-data" (not "x-www-form-urlencoded" or "raw")
- Ensure the key for the file is exactly "file"
- Make sure you've selected "File" type for the file field (click the dropdown next to the key)
- Verify you've actually selected a file to upload

### Invalid File Format Error

**Error:**
```json
{
  "detail": "Invalid file format. Allowed formats: .mp3, .wav, .m4a, .flac, .ogg"
}
```

**Solution:**
- Make sure you're uploading an audio file with one of the supported extensions
- Check that the file isn't corrupted or empty

### Friendli API Error

**Error:**
```json
{
  "detail": "Error processing audio: Error calling Friendli API: 400 Bad Request"
}
```

**Solution:**
- Verify your Friendli API key is correct in the .env file
- Make sure the audio file is in a format supported by Friendli
- Check that the file isn't too large (try with a smaller file)
- Ensure the file contains actual audio content
