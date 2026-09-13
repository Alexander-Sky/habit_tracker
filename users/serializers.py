from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import User


class UserRegisterSerializer(serializers.ModelSerializer):
    """Регистрация нового пользователя.

    Пароль принимается только на запись и сохраняется хешем.
    """

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'},
        label='Пароль',
    )

    class Meta:
        model = User
        fields = ('id', 'email', 'password', 'first_name', 'phone', 'city')
        # Штатный UniqueValidator отключён ради своего сообщения
        # и проверки без учёта регистра
        extra_kwargs = {'email': {'validators': []}}

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Пользователь с таким email уже зарегистрирован.')
        return value.lower()

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    """Профиль пользователя."""

    habits_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'first_name',
            'phone',
            'city',
            'avatar',
            'telegram_chat_id',
            'habits_count',
        )
        read_only_fields = ('email',)

    def get_habits_count(self, obj: User) -> int:
        return obj.habits.count()
