"""
Celery tasks for account management.
"""
from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse

User = get_user_model()


@shared_task
def send_invitation_email(user_id):
    """
    Send invitation email to a newly created user.

    Args:
        user_id: The ID of the user to send the invitation to
    """
    try:
        user = User.objects.get(pk=user_id)

        # Generate password reset link (user can set their password)
        # In a real implementation, you'd generate a token here
        subject = f'Welcome to Friday - You have been invited'

        message = f"""
Hello {user.full_name},

You have been invited to join Friday, our project management platform.

To get started, please visit the following link to set your password:
{settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000'}/accounts/password-reset/

Your username is: {user.username}
Your email is: {user.email}

If you have any questions, please contact your system administrator.

Best regards,
The Friday Team
        """

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@friday.local',
            recipient_list=[user.email],
            fail_silently=False,
        )

        return f"Invitation email sent to {user.email}"

    except User.DoesNotExist:
        return f"User with ID {user_id} not found"
    except Exception as e:
        return f"Error sending invitation email: {str(e)}"
