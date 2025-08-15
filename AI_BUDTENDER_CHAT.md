# AI Budtender Chat Implementation

🌿 **Complete AI-powered cannabis strain recommendation chat widget for the Canna platform**

## 🎯 Overview

The AI Budtender Chat is a sophisticated real-time chat widget that provides personalized cannabis strain recommendations using AI technology. It integrates seamlessly with the existing Canna Django application and connects to the canagent API service for intelligent strain matching.

## 🏗 Architecture & Workflow

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Browser  │    │   Django Canna   │    │   Canagent API  │
│   (Frontend)    │───▶│   (Backend)      │───▶│   (AI Service)  │
│                 │    │                  │    │                 │
│ - Chat Widget   │    │ - Chat Proxy     │    │ - Strain AI     │
│ - Strain Cards  │    │ - Session Mgmt   │    │ - Vector Search │
│ - Real-time UI  │    │ - Analytics      │    │ - OpenAI/Mock   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Chat Workflow Process

1. **User Interaction**
   - User clicks the green 🌿 chat bubble (bottom-right corner)
   - Chat window opens with welcome message and quick actions
   - User types a question or clicks quick action button

2. **Frontend Processing** 
   - JavaScript captures user input
   - Adds CSRF token for Django security
   - Sends POST request to `/api/chat/chat/`
   - Shows typing indicator while waiting

3. **Django Middleware**
   - Validates API key (if configured)
   - Creates or retrieves chat session
   - Logs user message to database
   - Forwards request to canagent API

4. **AI Processing (Canagent)**
   - Receives user message and conversation history
   - **Intent Detection**: Automatically detects user needs (sleep/energy/focus/pain/anxiety)
   - **Structured Filtering**: Applies smart filters based on detected intent
   - **Vector Search**: Uses pgvector for semantic strain matching within filtered results
   - Generates AI response with strain recommendations using CompactStrain schema
   - Returns JSON with response text, recommended strains, detected_intent, and filters_applied

5. **Response Handling**
   - Django logs AI response and recommended strains
   - Returns response to frontend with session ID
   - JavaScript displays AI message and strain cards
   - Strain cards are clickable and link to individual strain pages

6. **Session Management**
   - Client-side conversation history stored in localStorage
   - Server-side session tracking for analytics
   - Message history sent with each request for context

## 📁 Project Structure

```
canna/
├── AI_BUDTENDER_CHAT.md          # This documentation
├── apps/chat_bot/                # Django chat bot application
│   ├── __init__.py
│   ├── admin.py                  # Django admin interface
│   ├── apps.py                   # App configuration
│   ├── models.py                 # Database models
│   ├── views.py                  # API endpoints and logic
│   ├── urls.py                   # URL routing
│   └── migrations/               # Database migrations
│       └── __init__.py
├── static/
│   ├── css/
│   │   └── ai-budtender-chat.css # Chat widget styles
│   └── js/
│       └── ai-budtender-chat.js  # Chat widget JavaScript
└── templates/
    └── base.html                 # Updated to include chat widget
```

## 🛠 Implementation Steps Taken

### 1. **Project Setup & Planning**
- ✅ Created feature branch `feature/ai-budtender-chat`
- ✅ Analyzed canagent API documentation and endpoints
- ✅ Studied chat API schema and response format
- ✅ Planned authentication and integration strategy

### 2. **Frontend Chat Widget Development**
- ✅ **CSS Styling** (`static/css/ai-budtender-chat.css`)
  - Modern, responsive design with cannabis theme
  - Fixed bottom-right corner bubble
  - Animated typing indicators and transitions
  - Mobile-optimized responsive layout
  - Strain recommendation cards with hover effects

- ✅ **JavaScript Implementation** (`static/js/ai-budtender-chat.js`)
  - ES6 class-based architecture
  - Real-time WebSocket support (configurable)
  - Client-side conversation storage
  - CSRF token handling for Django
  - Error handling and retry logic
  - Session management and persistence

### 3. **Django Backend Development**
- ✅ **Created Django App** (`apps/chat_bot/`)
  - Following existing project structure patterns
  - Proper app configuration and routing

- ✅ **Database Models** (`models.py`)
  ```python
  - ChatConfiguration: API settings and feature flags
  - APIKey: Authentication and access control
  - ChatSession: User session tracking
  - ChatMessage: Message logging and analytics
  - ChatFeedback: User satisfaction feedback
  ```

- ✅ **API Views** (`views.py`)
  ```python
  - ChatProxyView: Main chat endpoint with canagent integration
  - ChatConfigView: Frontend configuration endpoint
  - ChatFeedbackView: User feedback collection
  - Health check and statistics endpoints
  ```

- ✅ **Admin Interface** (`admin.py`)
  - Comprehensive admin panels for all models
  - Usage statistics and session management
  - API key generation and management
  - Message analytics and feedback tracking

### 4. **Django Integration**
- ✅ **Settings Configuration**
  - Added `apps.chat_bot` to `INSTALLED_APPS`
  - Maintained existing project structure

- ✅ **URL Routing**
  - Added `/api/chat/` URL pattern
  - Integrated with existing URL structure

- ✅ **Template Integration**
  - Updated `base.html` to include chat widget
  - Added CSS and JavaScript assets
  - Configured chat widget initialization

### 5. **Security & Authentication**
- ✅ **API Key System**
  - UUID-based API keys for access control
  - Origin-based access restrictions
  - Usage tracking and analytics

- ✅ **Django Security**
  - CSRF token integration
  - Proper request validation
  - IP address logging and tracking

### 6. **Error Handling & Reliability**
- ✅ **Frontend Error Handling**
  - Network connectivity issues
  - API timeout and retry logic
  - User-friendly error messages

- ✅ **Backend Error Handling**
  - Canagent API failure recovery
  - Database transaction safety
  - Comprehensive logging

## 🔧 Configuration & Setup

### 1. **Database Migration**
```bash
python manage.py makemigrations chat_bot
python manage.py migrate
```

### 2. **Django Admin Setup**
1. Access Django admin at `/admin/`
2. Navigate to "Chat Bot" section
3. Configure "Chat Configuration":
   - Set API Base URL: `http://localhost:8001`
   - Enable chat widget: ✓
   - Set rate limits and history settings
4. Optionally create API keys for authentication

### 3. **Canagent Service**
Ensure canagent is running on `localhost:8001` with:
```bash
cd ../canagent
make start
```

## 🎨 Features & Capabilities

### **User Experience**
- 🌿 Cannabis-themed green bubble icon
- 💬 Smooth slide-up animation
- 📱 Mobile-responsive design
- ⚡ Quick action buttons for common queries
- 🔄 Real-time typing indicators
- 📝 Message history persistence

### **Strain Recommendations**
- 🧬 AI-powered strain matching
- 📊 THC/CBD/CBG content display
- ⭐ Strain ratings and categories
- 🔗 Direct links to strain detail pages
- 📱 Mobile-optimized strain cards

### **Technical Features**
- 🔐 API key authentication
- 📈 Usage analytics and tracking
- 💾 Session persistence
- 🔄 Automatic retry on failure
- 🌐 WebSocket support (optional)
- 📊 Admin dashboard with statistics

## 🚀 Usage Examples

### **Quick Actions**
- "What's good for relaxation?"
- "I need something for creativity"
- "What helps with sleep?"
- "Show me energizing strains"
- "What's good for pain relief?"

### **Natural Language Queries**
- "I want something with high THC but low CBD"
- "Show me indica strains for evening use"
- "What's a good strain for focus and productivity?"
- "I need something for chronic pain relief"

## 📊 Analytics & Monitoring

The system tracks:
- **Chat Sessions**: User engagement and conversation length
- **Message Analytics**: Popular queries and response times
- **Strain Recommendations**: Most recommended strains
- **User Feedback**: Thumbs up/down ratings
- **API Performance**: Response times and error rates

Access analytics through Django Admin → Chat Bot section.

## 🔗 API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/chat/config/` | GET | Get chat configuration |
| `/api/chat/chat/` | POST | Send chat message |
| `/api/chat/feedback/` | POST | Submit user feedback |
| `/api/chat/health/` | GET | Health check status |
| `/api/chat/stats/` | GET | Usage statistics |

## 🔍 Troubleshooting

### **Common Issues**
1. **Chat bubble not appearing**
   - Check Django admin: Chat Configuration → Is Active
   - Verify JavaScript console for errors
   - Ensure `data-ai-budtender-chat` attribute in base.html

2. **API connection failures**
   - Verify canagent service is running on port 8001
   - Check Django admin: Chat Configuration → API Base URL
   - Review Django logs for proxy errors

3. **Strain links not working**
   - Ensure canagent has `CANNAMENTE_BASE_URL` configured
   - Verify strain slugs match Django URL patterns

## 🎯 Future Enhancements

- **WebSocket Integration**: Real-time bidirectional communication
- **Multi-language Support**: Spanish language interface
- **Advanced Analytics**: Conversion tracking and A/B testing
- **Voice Interface**: Speech-to-text integration
- **Personalization**: User preference learning
- **Mobile App**: React Native or Flutter implementation

## 📝 Notes

- Client-side conversation storage (localStorage)
- Django proxy handles canagent communication
- Strain URLs automatically generated by canagent
- Full admin interface for configuration
- Production-ready with comprehensive error handling
- Scalable architecture for future features

---

## 🔄 Latest Updates (v2.0 - Enhanced API Integration)

### **API Optimization (August 2025)**
- **Intent Detection**: Automatic detection of user needs (sleep/energy/focus/pain/anxiety)
- **Structured Filtering**: Smart strain filtering based on detected intent prevents conflicting recommendations
- **Compact Response Format**: Optimized `CompactStrain` schema for faster UI rendering
- **Enhanced Strain Cards**: Display effects with energy types, medical uses, and flavors
- **Improved Cannabinoid Logic**: Smart CBG/CBD display based on content levels

### **New Response Format**
```json
{
  "response": "AI response text...",
  "recommended_strains": [
    {
      "id": 42,
      "name": "Northern Lights | Variedad de cannabis",
      "thc": "18.50", "cbd": "0.10", "cbg": "1.00",
      "category": "Indica",
      "url": "http://localhost:8000/strain/northern-lights/",
      "feelings": [{"name": "Sleepy", "energy_type": "relaxing"}],
      "helps_with": [{"name": "Insomnia"}],
      "flavors": [{"name": "earthy"}]
    }
  ],
  "detected_intent": "sleep",
  "filters_applied": {
    "preferred_categories": ["Indica"],
    "required_feelings": ["Sleepy", "Relaxed"]
  }
}
```

### **UI Improvements**
- **Strain Cards**: Color-coded categories (Indica: blue, Sativa: orange, Hybrid: purple)
- **Smart Cannabinoid Display**: Shows CBG when CBD is low/null
- **Effects Visualization**: "Sleepy (relaxing)", "Creative (energizing)"
- **Medical Uses**: "Ayuda con: Insomnia, Stress"
- **Flavor Profiles**: "Sabores: earthy, pine"

### **Testing**
- ✅ Sleep Intent: Returns Indica strains with sleepy/relaxed effects
- ✅ Energy Intent: Returns Sativa/Hybrid with energetic effects  
- ✅ Pain Intent: Returns strains helping with pain/inflammation
- ✅ Focus Intent: Returns strains with focused/creative effects
- ✅ Strain Cards: Clickable with proper cannabinoid display
- ✅ Docker Integration: Works with canna + canagent containers

---

**Implementation completed on**: `master` branch  
**Total development time**: Complete enhanced implementation  
**Status**: ✅ Production ready with enhanced AI capabilities  
**API Version**: Canagent v4.1 with intent detection  
**Test Page**: `/test_chat_integration.html` for integration testing