from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import ProtectedError

from .models import ListType, ListItem
from .serializers import ListTypeSerializer, ListItemSerializer

# === Shared Base Delete View ===
class BaseDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.delete()
            return Response({"message": "Deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            return Response({"error": "Cannot delete due to related data."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# === ListTypes ===
class ListTypeListCreateView(generics.ListCreateAPIView):
    queryset = ListType.objects.all()
    serializer_class = ListTypeSerializer
    permission_classes = [IsAuthenticated]

class ListTypeUpdateView(generics.UpdateAPIView):
    queryset = ListType.objects.all()
    serializer_class = ListTypeSerializer
    permission_classes = [IsAuthenticated]

class ListTypeDeleteView(BaseDeleteView):
    queryset = ListType.objects.all()
    serializer_class = ListTypeSerializer


# === ListItems ===
class ListItemListCreateView(generics.ListCreateAPIView):
    queryset = ListItem.objects.all()
    serializer_class = ListItemSerializer
    permission_classes = [IsAuthenticated]

class ListItemUpdateView(generics.UpdateAPIView):
    queryset = ListItem.objects.all()
    serializer_class = ListItemSerializer
    permission_classes = [IsAuthenticated]

class ListItemDeleteView(BaseDeleteView):
    queryset = ListItem.objects.all()
    serializer_class = ListItemSerializer

class ListItemByTypeView(generics.ListAPIView):
    serializer_class = ListItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        type_code = self.kwargs.get("code")
        return ListItem.objects.filter(list_type__code=type_code, is_active=True)
