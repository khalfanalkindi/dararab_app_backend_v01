from rest_framework import generics, viewsets
from rest_framework.permissions import IsAuthenticated
from django.db.models import ProtectedError, Sum, Count, OuterRef, Subquery
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404
from rest_framework import serializers
from inventory.pagination import StandardResultsSetPagination

from .models import (
    PrintRun, Project, Product, Stakeholder, Warehouse, Inventory, Transfer,
    Author, Translator, RightsOwner, Reviewer,
    Contract, PrintTask
)
from .serializers import (
    POSProductSummarySerializer, PrintRunSerializer, ProductSummarySerializer, ProjectSerializer, ProductSerializer, StakeholderSerializer, WarehouseSerializer,
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
    queryset = Project.objects.all().order_by('-created_at', 'id')
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

class ProjectUpdateView(generics.UpdateAPIView):
    queryset = Project.objects.all().order_by('id')
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class ProjectDeleteView(BaseDeleteView):
    queryset = Project.objects.all().order_by('id')
    serializer_class = ProjectSerializer

# ============================== Product ==============================
class ProductListCreateView(generics.ListCreateAPIView):
    queryset = Product.objects.all().order_by('-created_at', 'id')
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

class ProductUpdateView(generics.UpdateAPIView):
    queryset = Product.objects.all().order_by('id')
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class ProductDeleteView(BaseDeleteView):
    queryset = Product.objects.all().order_by('id')
    serializer_class = ProductSerializer

class ProductRetrieveView(generics.RetrieveAPIView):

    queryset = Product.objects.all().order_by('id')
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        # if your serializer needs request in context
        return {'request': self.request}

# ============================== PrintRunList ==============================


class PrintRunListCreateView(generics.ListCreateAPIView):
    queryset         = PrintRun.objects.all().order_by('-created_at', 'id')
    serializer_class = PrintRunSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        product_id = self.request.query_params.get('product_id')
        if product_id is not None:
            qs = qs.filter(product_id=product_id)
        return qs

    def create(self, request, *args, **kwargs):
        data = request.data.copy()

        # allow frontend to post { product: 1, edition_number: 2, ... }
        if 'product' in data and isinstance(data['product'], (int, str)):
            data['product_id'] = data.pop('product')

        # upsert on product_id + edition_number
        product_id     = data.get('product_id')
        edition_number = data.get('edition_number')

        if product_id and edition_number is not None:
            try:
                existing = PrintRun.objects.get(
                    product_id=product_id,
                    edition_number=edition_number
                )
                serializer = self.get_serializer(existing, data=data, partial=True)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)

            except PrintRun.DoesNotExist:
                serializer = self.get_serializer(data=data)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)
                headers = self.get_success_headers(serializer.data)
                return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # fallback: just create new
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class PrintRunUpdateView(generics.UpdateAPIView):
    queryset         = PrintRun.objects.all().order_by('id')
    serializer_class = PrintRunSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class PrintRunDeleteView(generics.DestroyAPIView):
    queryset         = PrintRun.objects.all().order_by('id')
    serializer_class = PrintRunSerializer
    permission_classes = [IsAuthenticated]


class PrintRunUpdateByProductEditionView(generics.UpdateAPIView):
    serializer_class   = PrintRunSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        product_id     = self.kwargs.get('product_id')
        edition_number = self.request.data.get('edition_number')

        if not edition_number:
            raise serializers.ValidationError({
                "edition_number": "This field is required for update."
            })
        try:
            return PrintRun.objects.get(
                product_id=product_id,
                edition_number=edition_number
            )
        except PrintRun.DoesNotExist:
            raise Http404("No PrintRun found for this product and edition.")


    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class PrintRunDeleteByProductEditionView(generics.DestroyAPIView):
    serializer_class   = PrintRunSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        product_id     = self.kwargs.get('product_id')
        edition_number = self.request.query_params.get('edition_number')
        if not edition_number:
            raise serializers.ValidationError({
                "edition_number": "This query parameter is required for delete."
            })
        try:
            return PrintRun.objects.get(
                product_id=product_id,
                edition_number=edition_number
            )
        except PrintRun.DoesNotExist:
            raise Http404("No PrintRun found for this product and edition.")

    def delete(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.delete()
            return Response({"message": "Deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            return Response({"error": "Cannot delete due to related data."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

# ============================== Warehouse ==============================
class WarehouseListCreateView(generics.ListCreateAPIView):
    queryset = Warehouse.objects.all().order_by('name_en')
    serializer_class = WarehouseSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

class WarehouseUpdateView(generics.UpdateAPIView):
    queryset = Warehouse.objects.all().order_by('id')
    serializer_class = WarehouseSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class WarehouseDeleteView(BaseDeleteView):
    queryset = Warehouse.objects.all().order_by('id')
    serializer_class = WarehouseSerializer

# ============================== Inventory ==============================
class InventoryListCreateView(generics.ListCreateAPIView):
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Inventory.objects.all().order_by('-created_at', 'id')
        product_id = self.request.query_params.get('product_id')
        warehouse_id = self.request.query_params.get('warehouse_id')

        if product_id:
            queryset = queryset.filter(product_id=product_id)
        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)
        
        return queryset
    def create(self, request, *args, **kwargs):
        # Handle frontend data format
        data = request.data.copy()
        
        # Check if data is in the format {product: 1, warehouse: 1, quantity: 54}
        if 'product' in data and isinstance(data['product'], (int, str)):
            data['product_id'] = data.pop('product')
            
        if 'warehouse' in data and isinstance(data['warehouse'], (int, str)):
            data['warehouse_id'] = data.pop('warehouse')
        
        # Check if inventory record already exists for this product and warehouse
        product_id = data.get('product_id')
        warehouse_id = data.get('warehouse_id')
        
        if product_id and warehouse_id:
            try:
                # Try to get existing inventory record
                inventory = Inventory.objects.get(product_id=product_id, warehouse_id=warehouse_id)
                
                # Update the existing record instead of creating a new one
                serializer = self.get_serializer(inventory, data=data, partial=True)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Inventory.DoesNotExist:
                # If no existing record, create a new one
                serializer = self.get_serializer(data=data)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)
                headers = self.get_success_headers(serializer.data)
                return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)
        
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class InventoryUpdateView(generics.UpdateAPIView):
    queryset = Inventory.objects.all().order_by('id')
    serializer_class = InventorySerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class InventoryDeleteView(BaseDeleteView):
    queryset = Inventory.objects.all().order_by('id')
    serializer_class = InventorySerializer

# New views for product-specific inventory operations
class InventoryUpdateByProductView(generics.UpdateAPIView):
    serializer_class = InventorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        product_id = self.kwargs.get('product_id')
        warehouse_id = self.request.data.get('warehouse_id')

        if not warehouse_id:
            raise serializers.ValidationError({"warehouse_id": "This field is required."})

        try:
            return Inventory.objects.get(product_id=product_id, warehouse_id=warehouse_id)
        except Inventory.DoesNotExist:
            raise Http404("No inventory found for this product and warehouse combination.")
        
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class InventoryDeleteByProductView(generics.DestroyAPIView):
    serializer_class = InventorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        product_id = self.kwargs.get('product_id')
        warehouse_id = self.request.query_params.get('warehouse_id')
        
        if not warehouse_id:
            raise serializers.ValidationError({"warehouse_id": "This field is required."})
            
        try:
            return Inventory.objects.get(product_id=product_id, warehouse_id=warehouse_id)
        except Inventory.DoesNotExist:
            raise Http404("No inventory found for this product and warehouse combination.")
    
    def delete(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.delete()
            return Response({"message": "Deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            return Response({"error": "Cannot delete due to related data."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

# ============================== Transfer ==============================
class TransferListCreateView(generics.ListCreateAPIView):
    queryset = Transfer.objects.all().order_by('-created_at', 'id')
    serializer_class = TransferSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

class TransferUpdateView(generics.UpdateAPIView):
    queryset = Transfer.objects.all().order_by('id')
    serializer_class = TransferSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class TransferDeleteView(BaseDeleteView):
    queryset = Transfer.objects.all().order_by('id')
    serializer_class = TransferSerializer

# ============================== People ==============================
class AuthorListCreateView(generics.ListCreateAPIView):
    queryset = Author.objects.all().order_by('name')
    serializer_class = AuthorSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

class AuthorUpdateView(generics.UpdateAPIView):
    queryset = Author.objects.all().order_by('id')
    serializer_class = AuthorSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class AuthorDeleteView(BaseDeleteView):
    queryset = Author.objects.all().order_by('id')
    serializer_class = AuthorSerializer

class TranslatorListCreateView(generics.ListCreateAPIView):
    queryset = Translator.objects.all().order_by('name')
    serializer_class = TranslatorSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

class TranslatorUpdateView(generics.UpdateAPIView):
    queryset = Translator.objects.all().order_by('id')
    serializer_class = TranslatorSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class TranslatorDeleteView(BaseDeleteView):
    queryset = Translator.objects.all().order_by('id')
    serializer_class = TranslatorSerializer

class RightsOwnerListCreateView(generics.ListCreateAPIView):
    queryset = RightsOwner.objects.all().order_by('name')
    serializer_class = RightsOwnerSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

class RightsOwnerUpdateView(generics.UpdateAPIView):
    queryset = RightsOwner.objects.all().order_by('id')
    serializer_class = RightsOwnerSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class RightsOwnerDeleteView(BaseDeleteView):
    queryset = RightsOwner.objects.all().order_by('id')
    serializer_class = RightsOwnerSerializer

class ReviewerListCreateView(generics.ListCreateAPIView):
    queryset = Reviewer.objects.all().order_by('name')
    serializer_class = ReviewerSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

class ReviewerUpdateView(generics.UpdateAPIView):
    queryset = Reviewer.objects.all().order_by('id')
    serializer_class = ReviewerSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class ReviewerDeleteView(BaseDeleteView):
    queryset = Reviewer.objects.all().order_by('id')
    serializer_class = ReviewerSerializer

class StakeholderListCreateView(generics.ListCreateAPIView):
    queryset = Stakeholder.objects.all().order_by('name')
    serializer_class = StakeholderSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

class StakeholderUpdateView(generics.UpdateAPIView):
    queryset = Stakeholder.objects.all().order_by('id')
    serializer_class = StakeholderSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class StakeholderDeleteView(generics.DestroyAPIView):
    queryset = Stakeholder.objects.all().order_by('id')
    serializer_class = StakeholderSerializer
    permission_classes = [IsAuthenticated]


# ============================== Contract ==============================

class ContractListCreateView(generics.ListCreateAPIView):
    queryset = Contract.objects.all().order_by('-created_at', 'id')
    serializer_class = ContractSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

class ContractUpdateView(generics.UpdateAPIView):
    queryset = Contract.objects.all().order_by('id')
    serializer_class = ContractSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class ContractDeleteView(generics.DestroyAPIView):
    queryset = Contract.objects.all().order_by('id')
    serializer_class = ContractSerializer
    permission_classes = [IsAuthenticated]


# ============================== PrintTask ==============================
class PrintTaskListCreateView(generics.ListCreateAPIView):
    queryset = PrintTask.objects.all().order_by('-created_at', 'id')
    serializer_class = PrintTaskSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

class PrintTaskUpdateView(generics.UpdateAPIView):
    queryset = PrintTask.objects.all().order_by('id')
    serializer_class = PrintTaskSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class PrintTaskDeleteView(BaseDeleteView):
    queryset = PrintTask.objects.all().order_by('id')
    serializer_class = PrintTaskSerializer

#----


class ProductSummaryView(generics.ListAPIView):
    serializer_class   = ProductSummarySerializer
    permission_classes = [IsAuthenticated]
    pagination_class   = StandardResultsSetPagination

    def get_queryset(self):
        latest = PrintRun.objects.filter(product=OuterRef('pk'))\
                                 .order_by('-edition_number')
        return (
            Product.objects
                   .annotate(
                       editions_count=Count('print_runs', distinct=True),
                       stock=Sum('inventory__quantity'),
                       latest_price=Subquery(latest.values('price')[:1]),
                       latest_cost=Subquery(latest.values('print_cost')[:1]),
                   )
                   .select_related('genre','status','language','author','translator')
                   .order_by('id')       # ← add this
        )
    def get_serializer_context(self):

        return { 'request': self.request }
    
class POSProductViewSet(viewsets.ModelViewSet):
    serializer_class = POSProductSummarySerializer
    
    def get_queryset(self):
        latest = PrintRun.objects.filter(product=OuterRef('pk'))\
                                 .order_by('-edition_number')
        queryset = (
            Product.objects
                   .annotate(
                       editions_count=Count('print_runs', distinct=True),
                       stock=Sum('inventory__quantity'),
                       latest_price=Subquery(latest.values('price')[:1]),
                       latest_cost=Subquery(latest.values('print_cost')[:1]),
                   )
                   .select_related('genre','status','language','author','translator')
                   .order_by('id')
        )
        
        warehouse_id = self.request.query_params.get('warehouse_id')
        if warehouse_id:
            queryset = queryset.filter(
                inventory__warehouse_id=warehouse_id,
                inventory__quantity__gt=0
            ).distinct()
            
        return queryset
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['warehouse_id'] = self.request.query_params.get('warehouse_id')
        return context

