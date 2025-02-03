from django.contrib import admin, messages
from .models import Cart, Categories, Faq, OrderItems, Orders, Products, Subcategories, Users
from django.utils.html import format_html
from django.urls import path
from django.http import HttpResponseRedirect
import requests
import os
from pathlib import Path
import environ
from asgiref.sync import sync_to_async


BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR.parent.parent, '.env'))

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

class UsersAdmin(admin.ModelAdmin):
    list_display = ('username', 'full_name', 'registered_at')

    change_list_template = "admin/myapp/users_change_list.html"  # Укажите свой шаблон
    success = True

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('custom_action/', self.admin_site.admin_view(self.custom_action), name='custom_action'),
        ]
        return custom_urls + urls

    def custom_action(self, request):
        if request.method == 'POST':
            success = True
            message = request.POST.get('message', '')
            users = Users.objects.all()
            for user in users:
                TOKEN = env('BOT_TOKEN')
                CHAT_ID = user.user_id 
                TEXT = message

                print(TOKEN)
                print(CHAT_ID)
                print(TEXT)

                url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

                payload = {
                    "chat_id": CHAT_ID,
                    "text": TEXT,
                    "parse_mode": "Markdown"
                }

                response = requests.post(url, json=payload)

                if response.status_code == 200:
                    print("✅ Сообщение отправлено!")
                else:
                    success = False
                    print(f"❌ Ошибка отправки: {response.text}")

            if success:
                self.message_user(request, "Рассылка выполнена успешно для всех пользователей.", messages.SUCCESS)
            else:
                self.message_user(request, "Рассылка не выполнена.", messages.ERROR)
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/admin/myapp/users/'))


admin.site.register(Cart)
admin.site.register(Categories)
admin.site.register(Faq)
admin.site.register(OrderItems)
admin.site.register(Orders)
admin.site.register(Products)
admin.site.register(Subcategories)
admin.site.register(Users, UsersAdmin)