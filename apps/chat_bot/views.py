from django.shortcuts import render
from django.http import JsonResponse
from .forms import ChatForm
from apps.chat_bot.chat import chatbot, QUESTIONS


INIT_MESSAGE = {
    "role": "system",
    "content": "Hello! To help you choose the right strain, please describe your preferences.\n"
               + "\n".join(QUESTIONS)
}


def chat_view(request):
    messages = request.session.get('chat_messages')
    if not messages:
        messages = [INIT_MESSAGE]
        request.session['chat_messages'] = messages

    if request.method == 'POST':
        form = ChatForm(request.POST)
        if form.is_valid():
            user_message = form.cleaned_data['message']
            messages.append({"role": "user", "content": user_message})

            bot_message = chatbot(user_message, messages)  # Передаем историю сообщений в чатбот
            messages.append({"role": "assistant", "content": bot_message})

            request.session['chat_messages'] = messages

            return JsonResponse({'message': bot_message})
    else:
        form = ChatForm()

    return render(request, 'chat_bot.html', {'form': form, 'messages': messages})
