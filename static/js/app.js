// Global variables
let currentConversationId = null;
let currentConversationName = null;

// DOM elements
const dropArea = document.getElementById('drop-area');
const uploadForm = document.getElementById('upload-form');
const uploadButton = document.getElementById('upload-button');
const uploadStatus = document.getElementById('upload-status');
const uploadProgress = document.getElementById('upload-progress');
const uploadProgressBar = uploadProgress.querySelector('.progress-bar');
const audioFileInput = document.getElementById('audio-file');
const conversationNameInput = document.getElementById('conversation-name');

const uploadSection = document.getElementById('upload-section');
const chatSection = document.getElementById('chat-section');
const conversationTitle = document.getElementById('conversation-title');
const chatMessages = document.getElementById('chat-messages');
const questionForm = document.getElementById('question-form');
const questionInput = document.getElementById('question-input');
const newUploadBtn = document.getElementById('new-upload-btn');

// API endpoints - using absolute URLs with port 8000 for FastAPI
const API_BASE_URL = 'http://127.0.0.1:8001';
const UPLOAD_ENDPOINT = `${API_BASE_URL}/upload-audio`;
const QUESTION_ENDPOINT = `${API_BASE_URL}/ask-question`;

// Add debug logging for development
const DEBUG = true;
function logDebug(message, data) {
    if (DEBUG) {
        console.log(`[DEBUG] ${message}`, data || '');
    }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    initDragAndDrop();
    initFormSubmission();
    initChatFunctionality();
    initNewUploadButton();
});

// Set up drag and drop functionality
function initDragAndDrop() {
    // Prevent default behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });

    // Highlight drop area when dragging over it
    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });

    // Handle dropped files
    dropArea.addEventListener('drop', handleDrop, false);

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function highlight() {
        dropArea.classList.add('highlight');
    }

    function unhighlight() {
        dropArea.classList.remove('highlight');
    }

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length > 0) {
            audioFileInput.files = files;
            // Display the selected filename
            const fileName = files[0].name;
            if (fileName) {
                const fileLabel = document.createElement('div');
                fileLabel.textContent = `Selected file: ${fileName}`;
                fileLabel.className = 'mt-2';
                dropArea.appendChild(fileLabel);
            }
        }
    }
}

// Handle form submission for audio upload
function initFormSubmission() {
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const file = audioFileInput.files[0];
        const conversationName = conversationNameInput.value;
        
        if (!file) {
            showUploadStatus('Please select an audio file', 'danger');
            return;
        }
        
        if (!conversationName) {
            showUploadStatus('Please enter a conversation name', 'danger');
            return;
        }
        
        // Check file extension
        const allowedExtensions = ['.mp3', '.wav', '.m4a', '.flac', '.ogg'];
        const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
        
        if (!allowedExtensions.includes(fileExtension)) {
            showUploadStatus(`Invalid file format. Allowed formats: ${allowedExtensions.join(', ')}`, 'danger');
            return;
        }
        
        await uploadAudio(file, conversationName);
    });
}

// Upload audio file to the server
async function uploadAudio(file, conversationName) {
    // Show progress bar and disable button
    uploadProgress.style.display = 'flex';
    uploadProgressBar.style.width = '0%';
    uploadButton.disabled = true;
    uploadButton.innerHTML = '<span class="spinner"></span> Processing...';
    
    logDebug('Starting upload with file:', file.name);
    logDebug('Conversation name:', conversationName);
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('conversation_name', conversationName);
        
        // Simulating upload progress
        const progressInterval = simulateProgress();
        
        logDebug('Sending request to:', UPLOAD_ENDPOINT);
        
        const response = await fetch(UPLOAD_ENDPOINT, {
            method: 'POST',
            body: formData,
            // Don't set Content-Type here, browser will set it with boundary for form-data
        });
        
        // Clear progress simulation
        clearInterval(progressInterval);
        uploadProgressBar.style.width = '100%';
        
        logDebug('Response status:', response.status);
        logDebug('Response headers:', response.headers);
        
        // Check response status and try to parse response
        if (!response.ok) {
            let errorMessage = `Error ${response.status}: ${response.statusText}`;
            try {
                const errorData = await response.json();
                errorMessage = errorData.detail || errorMessage;
            } catch (parseError) {
                // If JSON parsing fails, try to get text
                try {
                    const errorText = await response.text();
                    if (errorText) {
                        errorMessage += ` - ${errorText}`;
                    }
                } catch (textError) {
                    // Ignore text parsing error
                }
            }
            throw new Error(errorMessage);
        }
        
        // Try to parse JSON response
        let data;
        try {
            const responseText = await response.text();
            logDebug('Response text:', responseText);
            data = JSON.parse(responseText);
        } catch (e) {
            throw new Error(`Error parsing response: ${e.message}`);
        }
        
        logDebug('Response data:', data);
        
        if (data && data.conversation_id) {
            currentConversationId = data.conversation_id;
            currentConversationName = conversationName;
        } else {
            throw new Error('Invalid response format: missing conversation_id');
        }
        
        // Show success message
        showUploadStatus('Audio processed successfully!', 'success');
        
        // Switch to chat interface
        setTimeout(() => {
            uploadSection.style.display = 'none';
            chatSection.style.display = 'block';
            conversationTitle.textContent = conversationName;
            
            // Reset upload form
            uploadForm.reset();
            uploadProgress.style.display = 'none';
            uploadButton.disabled = false;
            uploadButton.innerHTML = 'Upload & Process';
            uploadStatus.style.display = 'none';
        }, 1500);
        
    } catch (error) {
        console.error('Upload error:', error);
        showUploadStatus(`Error: ${error.message}`, 'danger');
        uploadProgressBar.style.width = '0%';
        uploadButton.disabled = false;
        uploadButton.innerHTML = 'Upload & Process';
    }
}

// Show upload status message
function showUploadStatus(message, type) {
    uploadStatus.textContent = message;
    uploadStatus.className = `alert mt-3 alert-${type}`;
    uploadStatus.style.display = 'block';
}

// Simulate progress for better user experience
function simulateProgress() {
    let progress = 0;
    
    return setInterval(() => {
        // Increase progress, but never reach 100% (that happens when complete)
        if (progress < 90) {
            progress += Math.random() * 10;
            uploadProgressBar.style.width = `${progress}%`;
        }
    }, 500);
}

// Handle chat functionality
function initChatFunctionality() {
    questionForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const question = questionInput.value.trim();
        
        if (!question || !currentConversationId) {
            return;
        }
        
        logDebug('Sending question:', question);
        logDebug('For conversation ID:', currentConversationId);
        
        // Add user message to chat
        addMessage(question, 'user');
        
        // Clear input
        questionInput.value = '';
        
        // Show typing indicator
        const typingIndicator = addTypingIndicator();
        
        try {
            const requestBody = {
                conversation_id: currentConversationId,
                question: question
            };
            
            logDebug('Request body:', requestBody);
            
            const response = await fetch(QUESTION_ENDPOINT, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });
            
            logDebug('Question response status:', response.status);
            logDebug('Question response headers:', response.headers);
            
            if (!response.ok) {
                let errorMessage = `Error ${response.status}: ${response.statusText}`;
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.detail || errorMessage;
                } catch (parseError) {
                    // If JSON parsing fails, try to get text
                    try {
                        const errorText = await response.text();
                        if (errorText) {
                            errorMessage += ` - ${errorText}`;
                        }
                    } catch (textError) {
                        // Ignore text parsing error
                    }
                }
                throw new Error(errorMessage);
            }
            
            // Try to parse JSON response
            let data;
            try {
                const responseText = await response.text();
                logDebug('Question response text:', responseText);
                data = JSON.parse(responseText);
            } catch (e) {
                throw new Error(`Error parsing response: ${e.message}`);
            }
            
            logDebug('Question response data:', data);
            
            // Remove typing indicator
            typingIndicator.remove();
            
            // Add bot response with relevant contexts
            if (data && data.answer) {
                addMessage(data.answer, 'bot', data.relevant_contexts || []);
            } else {
                throw new Error('Invalid response format: missing answer');
            }
            
        } catch (error) {
            console.error('Question error:', error);
            
            // Remove typing indicator
            typingIndicator.remove();
            
            // Add error message
            const errorMsg = `Sorry, I couldn't process your question: ${error.message}`;
            addMessage(errorMsg, 'bot');
        }
    });
}

// Add a message to the chat
function addMessage(content, type, contexts = []) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}-message`;
    messageDiv.textContent = content;
    
    // Add context toggle for bot messages
    if (type === 'bot' && contexts.length > 0) {
        const contextToggle = document.createElement('div');
        contextToggle.className = 'context-toggle';
        contextToggle.innerHTML = '<i class="fas fa-info-circle"></i> Show source context';
        messageDiv.appendChild(contextToggle);
        
        const contextContent = document.createElement('div');
        contextContent.className = 'context-content';
        contextContent.textContent = contexts.join('\n\n');
        messageDiv.appendChild(contextContent);
        
        // Toggle context visibility
        contextToggle.addEventListener('click', () => {
            const isShowing = contextContent.style.display === 'block';
            contextContent.style.display = isShowing ? 'none' : 'block';
            contextToggle.innerHTML = isShowing ? 
                '<i class="fas fa-info-circle"></i> Show source context' : 
                '<i class="fas fa-times-circle"></i> Hide source context';
        });
    }
    
    chatMessages.appendChild(messageDiv);
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Add typing indicator
function addTypingIndicator() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message bot-message typing-indicator';
    typingDiv.innerHTML = '<span class="spinner"></span> Thinking...';
    chatMessages.appendChild(typingDiv);
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return typingDiv;
}

// Handle new upload button
function initNewUploadButton() {
    newUploadBtn.addEventListener('click', () => {
        // Reset state
        currentConversationId = null;
        currentConversationName = null;
        
        // Switch back to upload interface
        chatSection.style.display = 'none';
        uploadSection.style.display = 'block';
        
        // Clear chat messages except for the system greeting
        while (chatMessages.children.length > 1) {
            chatMessages.removeChild(chatMessages.lastChild);
        }
    });
}
