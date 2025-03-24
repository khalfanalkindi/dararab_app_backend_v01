from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import ListType, ListItem
from .serializers import ListTypeSerializer, ListItemSerializer

class ListTypeListCreateView(generics.ListCreateAPIView):
    queryset = ListType.objects.all()
    serializer_class = ListTypeSerializer
    permission_classes = [IsAuthenticated]

class ListItemListCreateView(generics.ListCreateAPIView):
    queryset = ListItem.objects.all()
    serializer_class = ListItemSerializer
    permission_classes = [IsAuthenticated]

class ListItemByTypeView(generics.ListAPIView):
    serializer_class = ListItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        type_code = self.kwargs.get("code")
        return ListItem.objects.filter(list_type__code=type_code, is_active=True)
