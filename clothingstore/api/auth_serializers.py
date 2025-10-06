from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.password_validation import validate_password
from django.core import exceptions
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from accounts.models import UserProfile
from .serializers import AddressSerializer

User = get_user_model()

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        style={'input_type': 'password'},
        validators=[validate_password]
    )
    password2 = serializers.CharField(
        write_only=True, 
        required=True, 
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password', 'password2')
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {'required': True}
        }

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password2'):
            raise serializers.ValidationError({"password": _("Password fields didn't match.")})
        
        # Validate password
        try:
            validate_password(attrs['password'])
        except exceptions.ValidationError as e:
            raise serializers.ValidationError({'password': list(e.messages)})
            
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            password=validated_data['password']
        )
        return user

class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(
        style={'input_type': 'password'}, 
        write_only=True,
        trim_whitespace=False
    )

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if not username or not password:
            raise serializers.ValidationError(
                _('Must include "username" and "password".'),
                code='authorization'
            )
            
        user = authenticate(
            username=username,
            password=password,
            request=self.context.get('request')
        )

        if not user:
            raise serializers.ValidationError(
                _('Unable to log in with provided credentials.'),
                code='authorization'
            )
            
        if not user.is_active:
            raise serializers.ValidationError(
                _('User account is disabled.'),
                code='authorization'
            )

        attrs['user'] = user
        return attrs

class UserProfileFieldsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = (
            'phone_number',
            'date_of_birth',
            'profile_picture',
            'address_line1',
            'address_line2',
            'city',
            'state',
            'postal_code',
            'country',
        )


class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer (kept for login/register/update)."""
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')


class UserDetailSerializer(serializers.ModelSerializer):
    """Detailed profile serializer including nested profile fields and addresses."""
    profile = UserProfileFieldsSerializer(read_only=True)
    addresses = AddressSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'profile', 'addresses',
        )


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, attrs):
        email = attrs.get('email')
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            # To avoid email enumeration, do not reveal whether email exists.
            user = None
        attrs['user'] = user
        return attrs


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(write_only=True)
    token = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    re_new_password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, attrs):
        uid = attrs.get('uid')
        token = attrs.get('token')
        new_password = attrs.get('new_password')
        re_new_password = attrs.get('re_new_password')

        if new_password != re_new_password:
            raise serializers.ValidationError({'new_password': _("Password fields didn't match.")})

        try:
            user_id = urlsafe_base64_decode(uid).decode()
            user = User.objects.get(pk=user_id)
        except Exception:
            raise serializers.ValidationError({'uid': _('Invalid reset link.')})

        # Validate token
        if not default_token_generator.check_token(user, token):
            raise serializers.ValidationError({'token': _('Invalid or expired token.')})

        # Validate the new password against validators
        try:
            validate_password(new_password, user=user)
        except exceptions.ValidationError as e:
            raise serializers.ValidationError({'new_password': list(e.messages)})

        attrs['user'] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data['user']
        new_password = self.validated_data['new_password']
        user.set_password(new_password)
        user.save(update_fields=["password"]) 
        return user

