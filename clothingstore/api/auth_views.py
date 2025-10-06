from rest_framework import status, permissions, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings

from .auth_serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserSerializer,
    UserDetailSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer
)
from django.contrib.auth import get_user_model

User = get_user_model()

class UserRegistrationAPIView(APIView):
    """
    Register a new user and return JWT tokens.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            user_data = UserSerializer(user).data
            return Response({
                #'user': user_data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'message': 'User registered successfully.'
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserLoginAPIView(APIView):
    """
    User login and token generation.
    """
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                refresh = RefreshToken.for_user(user)
                user_data = UserSerializer(user).data
                return Response({
                    #'user': user_data,
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'message': 'Login successful.'
                })
            else:
                return Response(
                    {'error': 'Unable to log in with provided credentials.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserLogoutAPIView(APIView):
    """
    Logout a user by blacklisting their refresh token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            logout(request)
            return Response({
                'message': 'Logout successful.'
            }, status=status.HTTP_205_RESET_CONTENT)
            
        except Exception as e:
            return Response({
                'message': 'Error during logout.',
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

class UserProfileAPIView(APIView):
    """
    Get or update user profile information.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        # Return detailed profile including nested profile fields and addresses
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data)
    
    def put(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetRequestAPIView(APIView):
    """
    Request a password reset. Always returns 200 to avoid email enumeration.
    Body: { "email": "user@example.com" }
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        # Initialize response data
        response_data = {
            'message': _('If an account exists with this email, a password reset link has been sent.')
        }
        
        try:
            serializer = PasswordResetRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data.get('user')

            if user is not None and user.is_active:
                # Generate reset token and UID
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)

                # Get reset URL from settings or use default
                reset_base = getattr(settings, 'FRONTEND_RESET_PASSWORD_URL', None) or \
                           getattr(settings, 'PASSWORD_RESET_CONFIRM_URL', None) or \
                           'http://localhost:8000/reset-password/confirm/'
                
                # Ensure proper URL formatting
                reset_base = reset_base.rstrip('/') + '/'  # Ensure trailing slash
                reset_link = f"{reset_base}?uid={uid}&token={token}"

                # Prepare email
                subject = 'Password Reset Request'
                message = (
                    'You are receiving this email because a password reset was requested for your account.\n\n'
                    f'Please click the link below to reset your password:\n{reset_link}\n\n'
                    'This link will expire in 24 hours.\n\n'
                    'If you did not request this change, you can safely ignore this email.'
                )
                
                from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@example.com')
                
                try:
                    # Try to send email
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=from_email,
                        recipient_list=[user.email],
                        fail_silently=False  # Always raise exceptions
                    )
                    
                    # Add debug info in development
                    if settings.DEBUG:
                        response_data['debug'] = {
                            'uid': uid,
                            'token': token,
                            'reset_link': reset_link,
                            'email_sent_to': user.email
                        }
                        
                except Exception as e:
                    # Log the error for server logs
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to send password reset email to {user.email}: {str(e)}")
                    
                    # Return a generic error message in production
                    if not settings.DEBUG:
                        return Response(
                            {'message': _('Failed to send password reset email. Please try again later.')},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR
                        )
                    # In debug mode, return the actual error
                    response_data['error'] = f"Failed to send email: {str(e)}"
                    return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    
        except Exception as e:
            # Log any unexpected errors
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in password reset request: {str(e)}", exc_info=True)
            
            if settings.DEBUG:
                response_data['error'] = str(e)
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        
        # Always return 200 to prevent email enumeration
        return Response(response_data, status=status.HTTP_200_OK)


class PasswordResetConfirmAPIView(APIView):
    """
    Confirm password reset using uid and token.
    Body: { "uid": "..", "token": "..", "new_password": "..", "re_new_password": ".." }
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        # Initialize response data
        response_data = {}
        
        try:
            serializer = PasswordResetConfirmSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # If we get here, the serializer is valid and password has been reset
            response_data['message'] = _('Your password has been reset successfully. You can now log in with your new password.')
            return Response(response_data, status=status.HTTP_200_OK)
            
        except serializers.ValidationError as e:
            # Log validation errors
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Password reset validation error: {str(e)}")
            
            # Return user-friendly error messages
            if 'token' in e.detail:
                response_data['message'] = _('Invalid or expired reset link. Please request a new password reset.')
            elif 'uid' in e.detail:
                response_data['message'] = _('Invalid reset link. Please check the link and try again.')
            elif 'new_password' in e.detail:
                response_data['message'] = _(' '.join(e.detail['new_password']))
            else:
                response_data['message'] = _('Invalid request. Please check your input and try again.')
                if settings.DEBUG:
                    response_data['errors'] = e.detail
            
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            # Log unexpected errors
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in password reset confirmation: {str(e)}", exc_info=True)
            
            response_data['message'] = _('An error occurred while processing your request. Please try again.')
            if settings.DEBUG:
                response_data['error'] = str(e)
                
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
