"""
AI Budtender Chat Views

STORAGE ARCHITECTURE:
- Chat messages: Stored in both browser localStorage (UX) and database (analysis)
- Session metadata: Stored in database for analytics (user count, message count, response times)
- Message content: Logged to ChatMessage for LLM-driven quality analysis and JSONL export
"""

from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.contrib.admin.views.decorators import staff_member_required
from django.views import View
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import ChatConfiguration, APIKey, ChatSession, ChatMessage
from .rate_limiter import check_rate_limit, RateLimitExceeded
import json
import requests
import time
import logging

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        x_real_ip = request.META.get('HTTP_X_REAL_IP')
        if x_real_ip:
            ip = x_real_ip
        else:
            ip = request.META.get('REMOTE_ADDR')
    return ip


def authenticate_api_key(request):
    """Authenticate API key from request headers"""
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    
    if auth_header.startswith('Bearer '):
        api_key_value = auth_header[7:]  # Remove 'Bearer ' prefix
        try:
            api_key = APIKey.objects.get(key=api_key_value, is_active=True)
            api_key.mark_used()
            return api_key
        except APIKey.DoesNotExist:
            pass
    
    return None


@method_decorator(csrf_exempt, name='dispatch')
class ChatConfigView(View):
    """Get current chat configuration for frontend"""
    
    def get(self, request):
        config = ChatConfiguration.get_config()
        
        # Don't expose sensitive data to frontend
        return JsonResponse({
            'api_base_url': config.api_base_url,
            'max_history': config.max_history,
            'is_active': config.is_active,
            'websocket_url': config.websocket_url,
        })


@method_decorator(csrf_exempt, name='dispatch')
class ChatProxyView(View):
    """Proxy chat requests to canagent API with authentication and logging"""
    
    def post(self, request):
        try:
            # Get configuration
            config = ChatConfiguration.get_config()
            if not config.is_active:
                return JsonResponse({
                    'error': 'Chat service is currently disabled'
                }, status=503)

            # Check rate limit by IP address
            client_ip = get_client_ip(request)
            try:
                check_rate_limit(client_ip)
            except RateLimitExceeded as e:
                response = JsonResponse({
                    'error': 'Rate limit exceeded. Please try again later.',
                    'retry_after_seconds': e.retry_after_seconds
                }, status=429)
                # Standard hint for clients that don't parse JSON
                response['Retry-After'] = str(e.retry_after_seconds)
                return response

            # Authenticate API key if required
            api_key = None
            if config.api_key:
                api_key = authenticate_api_key(request)
                if not api_key:
                    return JsonResponse({
                        'error': 'Invalid or missing API key'
                    }, status=401)
            
            # Parse request data
            try:
                data = json.loads(request.body)
                message = data.get('message', '').strip()
                history = data.get('history', [])
                session_id = data.get('session_id')
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON data'}, status=400)
            
            if not message:
                return JsonResponse({'error': 'Message is required'}, status=400)

            max_length = getattr(settings, 'CHAT_MAX_MESSAGE_LENGTH', 2000)
            if len(message) > max_length:
                return JsonResponse({
                    'error': f'Message too long. Maximum {max_length} characters.'
                }, status=400)

            # Get or create chat session (client_ip already retrieved for rate limiting)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            if session_id:
                try:
                    session = ChatSession.objects.get(session_id=session_id, is_active=True)
                except (ChatSession.DoesNotExist, ValidationError):
                    session = None
            else:
                session = None

            if not session:
                session = ChatSession.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    ip_address=client_ip,
                    user_agent=user_agent,
                    api_key=api_key
                )
            
            # Log user message
            ChatMessage.objects.create(
                session=session,
                message_type='user',
                content=message,
                ip_address=client_ip
            )
            
            # Forward request to canagent API
            api_start_time = time.time()
            
            canagent_url = f"{config.api_base_url}/api/v1/chat/ask/"
            headers = {'Content-Type': 'application/json'}
            
            # Add API key if configured
            if config.api_key:
                headers['Authorization'] = f'Bearer {config.api_key}'
            
            # Determine language for API request
            client_language = data.get('language')
            request_language = getattr(request, 'LANGUAGE_CODE', 'es')
            final_language = client_language or request_language

            payload = {
                'message': message,
                'history': history[-config.max_history:],  # Limit history
                'session_id': str(session.session_id),  # Use Django session_id, not client's
                'source_platform': 'cannamente',  # Platform identification
                'language': final_language  # Language preference
            }
            
            try:
                response = requests.post(
                    canagent_url,
                    json=payload,
                    headers=headers,
                    timeout=30
                )
                
                api_response_time = int((time.time() - api_start_time) * 1000)
                
                if response.status_code == 200:
                    response_data = response.json()
                    
                    # Context-Aware Architecture v2.0 - Handle session_id from canagent
                    canagent_session_id = response_data.get('session_id')
                    if canagent_session_id and canagent_session_id != str(session.session_id):
                        # Update our session ID to match canagent's session ID
                        session.session_id = canagent_session_id
                        session.save(update_fields=['session_id'])
                    
                    # Log AI response with analysis metadata
                    ChatMessage.objects.create(
                        session=session,
                        message_type='ai',
                        content=response_data.get('response', ''),
                        recommended_strains=response_data.get('recommended_strains', []),
                        api_response_time_ms=api_response_time,
                        query_type=response_data.get('query_type', 'unknown'),
                        detected_intent=response_data.get('detected_intent'),
                        confidence_score=response_data.get('confidence'),
                        ip_address=client_ip
                    )
                    
                    # Update session with Context-Aware metadata
                    session.message_count += 2  # User message + AI response
                    if response_data.get('language'):
                        session.language = response_data.get('language')
                    session.save(update_fields=['message_count', 'last_activity_at', 'language'])
                    
                    # Ensure session ID is included in response (use canagent's session ID)
                    response_data['session_id'] = canagent_session_id or str(session.session_id)
                    
                    return JsonResponse(response_data)
                
                else:
                    error_msg = f"API request failed: {response.status_code}"
                    ChatMessage.objects.create(
                        session=session,
                        message_type='error',
                        content=error_msg,
                        api_response_time_ms=api_response_time,
                        ip_address=client_ip
                    )
                    return JsonResponse({'error': error_msg}, status=response.status_code)
                    
            except requests.exceptions.RequestException as e:
                error_msg = f"Failed to connect to AI service: {str(e)}"
                ChatMessage.objects.create(
                    session=session,
                    message_type='error',
                    content=error_msg,
                    ip_address=client_ip
                )
                return JsonResponse({'error': error_msg}, status=502)
                
        except Exception as e:
            return JsonResponse({'error': 'Internal server error'}, status=500)



@method_decorator(csrf_exempt, name='dispatch')
class ChatStreamView(View):
    """
    SSE streaming proxy: forwards /api/v1/chat/ask/stream from canagent to the browser.

    Protocol (matches canagent SSE format):
      data: {"type": "metadata", "data": {...strains, session_id, ...}}
      data: {"type": "response_chunk", "text": "..."}
      data: {"type": "done"}
    """

    def post(self, request):
        try:
            config = ChatConfiguration.get_config()
            if not config.is_active:
                def _disabled():
                    yield f'data: {json.dumps({"type": "error", "message": "Chat service is currently disabled"})}\n\n'
                return StreamingHttpResponse(_disabled(), content_type='text/event-stream', status=503)

            client_ip = get_client_ip(request)
            try:
                check_rate_limit(client_ip)
            except RateLimitExceeded as e:
                retry_after = e.retry_after_seconds  # capture before Python 3 deletes 'e'
                def _rate_limited():
                    yield f'data: {json.dumps({"type": "error", "message": "Rate limit exceeded", "retry_after": retry_after})}\n\n'
                resp = StreamingHttpResponse(_rate_limited(), content_type='text/event-stream', status=429)
                resp['Retry-After'] = str(retry_after)
                return resp

            try:
                data = json.loads(request.body)
                message = data.get('message', '').strip()
                session_id = data.get('session_id')
            except json.JSONDecodeError:
                def _bad_json():
                    yield f'data: {json.dumps({"type": "error", "message": "Invalid JSON"})}\n\n'
                return StreamingHttpResponse(_bad_json(), content_type='text/event-stream', status=400)

            if not message:
                def _no_message():
                    yield f'data: {json.dumps({"type": "error", "message": "Message is required"})}\n\n'
                return StreamingHttpResponse(_no_message(), content_type='text/event-stream', status=400)

            # Create / retrieve Django session for analytics
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            if session_id:
                try:
                    django_session = ChatSession.objects.get(session_id=session_id, is_active=True)
                except (ChatSession.DoesNotExist, ValidationError):
                    django_session = None
            else:
                django_session = None

            if not django_session:
                django_session = ChatSession.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    ip_address=client_ip,
                    user_agent=user_agent,
                )

            canagent_url = f"{config.api_base_url}/api/v1/chat/ask/stream"
            headers = {'Content-Type': 'application/json'}
            if config.api_key:
                headers['Authorization'] = f'Bearer {config.api_key}'

            client_language = data.get('language')
            final_language = client_language or getattr(request, 'LANGUAGE_CODE', 'es')

            payload = {
                'message': message,
                'session_id': str(django_session.session_id),
                'language': final_language,
                'source_platform': 'cannamente',
            }

            api_start_time = time.time()

            def event_stream():
                # Accumulators for message logging
                response_chunks = []
                metadata = {}

                try:
                    with requests.post(
                        canagent_url,
                        json=payload,
                        headers=headers,
                        timeout=60,
                        stream=True,
                    ) as r:
                        for raw_line in r.iter_lines(decode_unicode=True):
                            if raw_line and raw_line.startswith('data: '):
                                try:
                                    chunk = json.loads(raw_line[6:])
                                except (json.JSONDecodeError, ValueError):
                                    yield f"{raw_line}\n\n"
                                    continue

                                chunk_type = chunk.get('type')

                                if chunk_type == 'metadata':
                                    meta = chunk.get('data', {})
                                    metadata.update(meta)
                                    canagent_sid = meta.get('session_id')
                                    if canagent_sid and str(django_session.session_id) != canagent_sid:
                                        django_session.session_id = canagent_sid
                                    django_session.message_count += 2
                                    if meta.get('language'):
                                        django_session.language = meta.get('language')
                                    django_session.save(update_fields=[
                                        'session_id', 'message_count', 'last_activity_at', 'language'
                                    ])

                                elif chunk_type == 'response_chunk':
                                    text = chunk.get('text', '')
                                    if text:
                                        response_chunks.append(text)

                                elif chunk_type == 'done':
                                    # Write ChatMessage records before yielding done
                                    api_response_time = int((time.time() - api_start_time) * 1000)
                                    try:
                                        ChatMessage.objects.create(
                                            session=django_session,
                                            message_type='user',
                                            content=message,
                                            ip_address=client_ip
                                        )
                                        ChatMessage.objects.create(
                                            session=django_session,
                                            message_type='ai',
                                            content=''.join(response_chunks),
                                            recommended_strains=metadata.get('recommended_strains'),
                                            api_response_time_ms=api_response_time,
                                            query_type=metadata.get('query_type', 'unknown'),
                                            detected_intent=metadata.get('detected_intent'),
                                            confidence_score=metadata.get('confidence'),
                                            ip_address=client_ip
                                        )
                                    except Exception:
                                        logger.exception("Failed to save chat messages for stream")

                                yield f"{raw_line}\n\n"

                            elif raw_line:
                                yield f"{raw_line}\n\n"
                except requests.exceptions.RequestException as e:
                    yield f'data: {json.dumps({"type": "error", "message": f"AI service unavailable: {str(e)}"})}\n\n'

            response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'
            response['Access-Control-Allow-Origin'] = '*'
            return response

        except Exception as e:
            logger.exception("ChatStreamView error")
            def _err():
                yield f'data: {json.dumps({"type": "error", "message": "Internal server error"})}\n\n'
            return StreamingHttpResponse(_err(), content_type='text/event-stream', status=500)


@require_http_methods(["GET"])
def chat_health(request):
    """Health check endpoint for chat service"""
    config = ChatConfiguration.get_config()
    
    # Test canagent API connectivity
    canagent_status = 'unknown'
    try:
        response = requests.get(f"{config.api_base_url}/api/v1/ping/", timeout=5)
        canagent_status = 'healthy' if response.status_code == 200 else 'unhealthy'
    except:
        canagent_status = 'unreachable'
    
    return JsonResponse({
        'status': 'healthy' if config.is_active else 'disabled',
        'chat_active': config.is_active,
        'canagent_api': canagent_status,
        'timestamp': timezone.now().isoformat()
    })


@staff_member_required
@require_http_methods(["GET"])
def chat_stats(request):
    """Get basic chat statistics (staff only)"""
    active_sessions = ChatSession.objects.filter(is_active=True).count()
    total_messages = ChatMessage.objects.count()
    total_sessions = ChatSession.objects.count()
    
    return JsonResponse({
        'active_sessions': active_sessions,
        'total_messages': total_messages,
        'total_sessions': total_sessions
    })
