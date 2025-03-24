from rest_framework import serializers
from .models import ListType, ListItem

class ListTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListType
        fields = '__all__'

class ListItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListItem
        fields = '__all__'
