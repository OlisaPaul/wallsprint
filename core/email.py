import os
from djoser.email import PasswordResetEmail
from dotenv import load_dotenv

load_dotenv()


class CustomPasswordResetEmail(PasswordResetEmail):
    # template_name = 'email/custom_password_reset.html'

    def get_context_data(self):
        context = super().get_context_data()
        context['domain'] = os.getenv("DJOSER_EMAIL_DOMAIN")
        context['protocol'] = 'https'

        print(context)  # For debugging purposes
        return context
