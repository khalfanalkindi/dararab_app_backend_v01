from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.db.models import ProtectedError
from rest_framework.response import Response
from rest_framework import status

from .models import (
    Project, Product, Stakeholder, Warehouse, Inventory, Transfer,
    Author, Translator, RightsOwner, Reviewer,
    Contract, PrintTask
)
from .serializers import (
    ProjectSerializer, ProductSerializer, StakeholderSerializer, WarehouseSerializer,
    InventorySerializer, TransferSerializer,
    AuthorSerializer, TranslatorSerializer, RightsOwnerSerializer,
    ReviewerSerializer, ContractSerializer, PrintTaskSerializer
)
### ==== Shared Delete View ====
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

# ============================== Project ==============================
class ProjectListCreateView(generics.ListCreateAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

class ProjectUpdateView(generics.UpdateAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class ProjectDeleteView(BaseDeleteView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

# ============================== Product ==============================
class ProductListCreateView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

class ProductUpdateView(generics.UpdateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class ProductDeleteView(BaseDeleteView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

# ============================== Warehouse ==============================
class WarehouseListCreateView(generics.ListCreateAPIView):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

class WarehouseUpdateView(generics.UpdateAPIView):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class WarehouseDeleteView(BaseDeleteView):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer

# ============================== Inventory ==============================
class InventoryListCreateView(generics.ListCreateAPIView):
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

class InventoryUpdateView(generics.UpdateAPIView):
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class InventoryDeleteView(BaseDeleteView):
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer

# ============================== Transfer ==============================
class TransferListCreateView(generics.ListCreateAPIView):
    queryset = Transfer.objects.all()
    serializer_class = TransferSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

class TransferUpdateView(generics.UpdateAPIView):
    queryset = Transfer.objects.all()
    serializer_class = TransferSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class TransferDeleteView(BaseDeleteView):
    queryset = Transfer.objects.all()
    serializer_class = TransferSerializer

# ============================== People ==============================
class AuthorListCreateView(generics.ListCreateAPIView):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

class AuthorUpdateView(generics.UpdateAPIView):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class AuthorDeleteView(BaseDeleteView):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer

class TranslatorListCreateView(generics.ListCreateAPIView):
    queryset = Translator.objects.all()
    serializer_class = TranslatorSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

class TranslatorUpdateView(generics.UpdateAPIView):
    queryset = Translator.objects.all()
    serializer_class = TranslatorSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class TranslatorDeleteView(BaseDeleteView):
    queryset = Translator.objects.all()
    serializer_class = TranslatorSerializer

class RightsOwnerListCreateView(generics.ListCreateAPIView):
    queryset = RightsOwner.objects.all()
    serializer_class = RightsOwnerSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

class RightsOwnerUpdateView(generics.UpdateAPIView):
    queryset = RightsOwner.objects.all()
    serializer_class = RightsOwnerSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class RightsOwnerDeleteView(BaseDeleteView):
    queryset = RightsOwner.objects.all()
    serializer_class = RightsOwnerSerializer

class ReviewerListCreateView(generics.ListCreateAPIView):
    queryset = Reviewer.objects.all()
    serializer_class = ReviewerSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

class ReviewerUpdateView(generics.UpdateAPIView):
    queryset = Reviewer.objects.all()
    serializer_class = ReviewerSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class ReviewerDeleteView(BaseDeleteView):
    queryset = Reviewer.objects.all()
    serializer_class = ReviewerSerializer

class StakeholderListCreateView(generics.ListCreateAPIView):
    queryset = Stakeholder.objects.all()
    serializer_class = StakeholderSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

class StakeholderUpdateView(generics.UpdateAPIView):
    queryset = Stakeholder.objects.all()
    serializer_class = StakeholderSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class StakeholderDeleteView(generics.DestroyAPIView):
    queryset = Stakeholder.objects.all()
    serializer_class = StakeholderSerializer
    permission_classes = [IsAuthenticated]


# ============================== Contract ==============================

class ContractListCreateView(generics.ListCreateAPIView):
    queryset = Contract.objects.all()
    serializer_class = ContractSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

class ContractUpdateView(generics.UpdateAPIView):
    queryset = Contract.objects.all()
    serializer_class = ContractSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class ContractDeleteView(generics.DestroyAPIView):
    queryset = Contract.objects.all()
    serializer_class = ContractSerializer
    permission_classes = [IsAuthenticated]


# ============================== PrintTask ==============================
class PrintTaskListCreateView(generics.ListCreateAPIView):
    queryset = PrintTask.objects.all()
    serializer_class = PrintTaskSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

class PrintTaskUpdateView(generics.UpdateAPIView):
    queryset = PrintTask.objects.all()
    serializer_class = PrintTaskSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class PrintTaskDeleteView(BaseDeleteView):
    queryset = PrintTask.objects.all()
    serializer_class = PrintTaskSerializer
