from rest_framework import serializers
from .models import ListType, ListItem

class ListTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListType
        exclude = ('created_by', 'updated_by')  # exclude instead of __all__

class ListItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListItem
        exclude = ('created_by', 'updated_by')  # same here
