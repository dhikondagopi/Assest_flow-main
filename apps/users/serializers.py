from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class SignupSerializer(serializers.ModelSerializer):
    """Employee self-registration — role is always EMPLOYEE, not exposed."""
    password  = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, label="Confirm password")

    class Meta:
        model  = User
        fields = ["email", "first_name", "last_name", "password", "password2"]

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password2"):
            raise serializers.ValidationError({"password2": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        # role always defaults to EMPLOYEE on self-signup
        return User.objects.create_user(**validated_data)


class UserMeSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = ["id", "email", "first_name", "last_name", "full_name", "role", "created_at"]
        read_only_fields = ["id", "email", "role", "created_at"]

    def get_full_name(self, obj):
        return obj.get_full_name()


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    token     = serializers.UUIDField()
    password  = serializers.CharField(validators=[validate_password])
    password2 = serializers.CharField(label="Confirm password")

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password2": "Passwords do not match."})
        return attrs


class PromoteEmployeeSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=User.Role.choices)
