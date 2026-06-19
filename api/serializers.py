from rest_framework import serializers
from home.models import App, Category


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for the Category model."""

    class Meta:
        model = Category
        fields = ["id", "name", "my_order"]


class AppSerializer(serializers.ModelSerializer):
    """Serializer for the App model."""
    category = serializers.SlugRelatedField(
        slug_field="name", queryset=Category.objects.all()
    )

    class Meta:
        model = App
        fields = [
            "id",
            "author",
            "category",
            "changelog",
            "description",
            "fap_id",
            "icon",
            "name",
            "screenshots",
            "short_description",
            "version",
        ]
