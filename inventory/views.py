from rest_framework import generics, viewsets
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.db.models import ProtectedError, Sum, Count, OuterRef, Subquery, Q
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
        return {'request': self.request}

class ProductDetailAggregatedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):
        try:
            product = (
                Product.objects.select_related(
                    "genre",
                    "status",
                    "language",
                    "author",
                    "translator",
                    "rights_owner",
                    "reviewer",
                    "project",
                )
                .prefetch_related("print_runs", "inventory__warehouse")
                .get(pk=pk)
            )
        except Product.DoesNotExist:
            raise Http404("Product not found.")

        product_data = ProductSerializer(product, context={"request": request}).data

        inventory_qs = Inventory.objects.filter(product_id=pk).select_related("warehouse")
        inventory_data = InventorySerializer(inventory_qs, many=True, context={"request": request}).data

        print_runs_qs = PrintRun.objects.filter(product_id=pk).select_related("status").order_by("edition_number")
        print_runs_data = PrintRunSerializer(print_runs_qs, many=True, context={"request": request}).data

        return Response(
            {
                "product": product_data,
                "inventory": inventory_data,
                "print_runs": print_runs_data,
            }
        )

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

class PrintRunBulkUpsertView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if not isinstance(request.data, list):
            return Response(
                {"detail": "Expected a list of print run objects."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        results = []
        with transaction.atomic():
            for index, item in enumerate(request.data):
                item_data = item.copy()
                pk = item_data.get("id")
                try:
                    if pk:
                        instance = PrintRun.objects.get(pk=pk)
                        serializer = PrintRunSerializer(
                            instance,
                            data=item_data,
                            partial=True,
                            context={"request": request},
                        )
                        serializer.is_valid(raise_exception=True)
                        serializer.save(updated_by=request.user)
                    else:
                        serializer = PrintRunSerializer(
                            data=item_data,
                            context={"request": request},
                        )
                        serializer.is_valid(raise_exception=True)
                        serializer.save(
                            created_by=request.user,
                            updated_by=request.user,
                        )
                    results.append(serializer.data)
                except PrintRun.DoesNotExist:
                    transaction.set_rollback(True)
                    return Response(
                        {
                            "detail": f"PrintRun with id {pk} not found.",
                            "index": index,
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                except serializers.ValidationError as exc:
                    transaction.set_rollback(True)
                    return Response(
                        {
                            "index": index,
                            "errors": exc.detail,
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                except Exception as exc:  # pragma: no cover - safety net
                    transaction.set_rollback(True)
                    return Response(
                        {
                            "index": index,
                            "detail": str(exc),
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        return Response(results, status=status.HTTP_200_OK)

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

class InventoryBulkUpsertView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if not isinstance(request.data, list):
            return Response(
                {"detail": "Expected a list of inventory objects."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        results = []
        with transaction.atomic():
            for index, item in enumerate(request.data):
                item_data = item.copy()
                pk = item_data.get("id")
                try:
                    if pk:
                        instance = Inventory.objects.get(pk=pk)
                        serializer = InventorySerializer(
                            instance,
                            data=item_data,
                            partial=True,
                            context={"request": request},
                        )
                        serializer.is_valid(raise_exception=True)
                        serializer.save(updated_by=request.user)
                    else:
                        serializer = InventorySerializer(
                            data=item_data,
                            context={"request": request},
                        )
                        serializer.is_valid(raise_exception=True)
                        serializer.save(
                            created_by=request.user,
                            updated_by=request.user,
                        )
                    results.append(serializer.data)
                except Inventory.DoesNotExist:
                    transaction.set_rollback(True)
                    return Response(
                        {
                            "detail": f"Inventory with id {pk} not found.",
                            "index": index,
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                except serializers.ValidationError as exc:
                    transaction.set_rollback(True)
                    return Response(
                        {"index": index, "errors": exc.detail},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                except Exception as exc:  # pragma: no cover - safety net
                    transaction.set_rollback(True)
                    return Response(
                        {"index": index, "detail": str(exc)},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        return Response(results, status=status.HTTP_200_OK)

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


class BootstrapDataView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request, *args, **kwargs):
        # Product summaries with pagination (reuse ProductSummaryView logic)
        summary_view = ProductSummaryView()
        summary_view.request = request
        queryset = summary_view.get_queryset()

        paginator = self.pagination_class()
        paginated_qs = paginator.paginate_queryset(queryset, request, view=summary_view)
        summary_serializer = ProductSummarySerializer(
            paginated_qs, many=True, context={"request": request}
        )
        paginated_summary = paginator.get_paginated_response(summary_serializer.data).data

        # List items
        genres = ListItem.objects.filter(list_type__code="genre", is_active=True).order_by("display_name_en")
        statuses = ListItem.objects.filter(list_type__code="product_status", is_active=True).order_by(
            "display_name_en"
        )
        languages = ListItem.objects.filter(list_type__code="product_language", is_active=True).order_by(
            "display_name_en"
        )
        print_run_statuses = ListItem.objects.filter(list_type__code="printrun_status", is_active=True).order_by(
            "display_name_en"
        )

        listitem_context = {"request": request}
        genres_data = ListItemSerializer(genres, many=True, context=listitem_context).data
        statuses_data = ListItemSerializer(statuses, many=True, context=listitem_context).data
        languages_data = ListItemSerializer(languages, many=True, context=listitem_context).data
        print_run_statuses_data = ListItemSerializer(
            print_run_statuses, many=True, context=listitem_context
        ).data

        # Warehouses & stakeholders
        warehouse_data = WarehouseSerializer(
            Warehouse.objects.order_by("name_en"), many=True, context={"request": request}
        ).data
        author_data = AuthorSerializer(
            Author.objects.order_by("name"), many=True, context={"request": request}
        ).data
        translator_data = TranslatorSerializer(
            Translator.objects.order_by("name"), many=True, context={"request": request}
        ).data
        rights_owner_data = RightsOwnerSerializer(
            RightsOwner.objects.order_by("name"), many=True, context={"request": request}
        ).data
        reviewer_data = ReviewerSerializer(
            Reviewer.objects.order_by("name"), many=True, context={"request": request}
        ).data

        return Response(
            {
                "product_summary": paginated_summary,
                "genres": genres_data,
                "statuses": statuses_data,
                "languages": languages_data,
                "warehouses": warehouse_data,
                "authors": author_data,
                "translators": translator_data,
                "rights_owners": rights_owner_data,
                "reviewers": reviewer_data,
                "print_run_statuses": print_run_statuses_data,
            }
        )


class ProductSummaryView(generics.ListAPIView):
    serializer_class   = ProductSummarySerializer
    permission_classes = [IsAuthenticated]
    pagination_class   = StandardResultsSetPagination

    def get_queryset(self):
        request = self.request
        params = request.query_params if request else {}
        search = params.get("search", "").strip()
        genre_id = params.get("genre_id")
        status_id = params.get("status_id")
        language_id = params.get("language_id")

        latest = PrintRun.objects.filter(product=OuterRef('pk')).order_by('-edition_number')

        queryset = (
            Product.objects.annotate(
                editions_count=Count('print_runs', distinct=True),
                stock=Sum('inventory__quantity'),
                latest_price=Subquery(latest.values('price')[:1]),
                latest_cost=Subquery(latest.values('print_cost')[:1]),
            )
            .select_related('genre', 'status', 'language', 'author', 'translator')
        )

        if search:
            queryset = queryset.filter(
                Q(isbn__icontains=search)
                | Q(title_en__icontains=search)
                | Q(title_ar__icontains=search)
                | Q(author__name__icontains=search)
                | Q(translator__name__icontains=search)
            )

        if genre_id:
            queryset = queryset.filter(genre_id=genre_id)

        if status_id:
            queryset = queryset.filter(status_id=status_id)

        if language_id:
            queryset = queryset.filter(language_id=language_id)

        return queryset.order_by('id')
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

