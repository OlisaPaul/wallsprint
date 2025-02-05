import os
from djoser.email import PasswordResetEmail
from django.contrib.auth.tokens import default_token_generator
from djoser import utils
from djoser.conf import settings

from dotenv import load_dotenv

load_dotenv()


class CustomPasswordResetEmail(PasswordResetEmail):
    template_name = "email/custom_password_reset.html"

    def get_context_data(self):
        # PasswordResetEmail can be deleted
        context = super().get_context_data()

        user = context.get("user")
        context["uid"] = utils.encode_uid(user.pk)
        context["token"] = default_token_generator.make_token(user)
        
        if not user.is_staff:
            context["domain"] = os.getenv("DJOSER_DOMAIN")  
        
        context["url"] = settings.PASSWORD_RESET_CONFIRM_URL.format(**context)
        return context
