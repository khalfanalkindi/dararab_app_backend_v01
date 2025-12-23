from rest_framework import generics, viewsets, filters
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db import transaction, models
from django.db.models import ProtectedError, Sum, Count, OuterRef, Subquery, Q, Value, F, Case, When, Exists
from django.db.models.functions import Coalesce
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
from common.models import ListItem
from common.serializers import ListItemSerializer
from users.serializers import UserBasicSerializer
from django.contrib.auth import get_user_model

User = get_user_model()
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
    queryset = Project.objects.select_related(
        'progress_status',
        'status',
        'type',
        'author',
        'translator',
        'rights_owner',
        'reviewer'
    ).prefetch_related('contract_set').order_by('-created_at', 'id')
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['title_ar', 'title_original', 'approval_status', 'created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        from .models import Product
        from common.models import ListItem
        
        queryset = super().get_queryset()
        
        # Search filter - search in title_ar and title_original
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title_ar__icontains=search) | 
                Q(title_original__icontains=search)
            )
        
        # Approval status filter
        approval_status = self.request.query_params.get('approval_status')
        if approval_status is not None:
            queryset = queryset.filter(approval_status=approval_status.lower() == 'true')
        
        # Progress status filter
        progress_status_id = self.request.query_params.get('progress_status_id')
        if progress_status_id:
            try:
                queryset = queryset.filter(progress_status_id=int(progress_status_id))
            except (ValueError, TypeError):
                pass  # Ignore invalid progress_status_id
        
        # Status filter
        status_id = self.request.query_params.get('status_id')
        if status_id:
            try:
                queryset = queryset.filter(status_id=int(status_id))
            except (ValueError, TypeError):
                pass  # Ignore invalid status_id
        
        # Type filter
        type_id = self.request.query_params.get('type_id')
        if type_id:
            try:
                queryset = queryset.filter(type_id=int(type_id))
            except (ValueError, TypeError):
                pass  # Ignore invalid type_id
        
        # Check if contracts should be included
        include_contracts = self.request.query_params.get('include_contracts', 'false').lower() == 'true'
        
        # Note: has_product and all_contracts_closed are calculated in the serializer
        # to avoid complex annotation issues. The serializer methods handle this efficiently.
        
        # Note: Ordering is handled by OrderingFilter, so we don't need to call order_by here
        # The default ordering is set via the 'ordering' attribute
        # Ensure select_related and prefetch_related are maintained
        queryset = queryset.select_related(
            'progress_status',
            'status',
            'type',
            'author',
            'translator',
            'rights_owner',
            'reviewer'
        )
        
        # Only prefetch contracts if requested (to avoid unnecessary queries)
        if include_contracts:
            queryset = queryset.prefetch_related('contract_set')
        
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Pass include_contracts flag to serializer context
        context['include_contracts'] = self.request.query_params.get('include_contracts', 'false').lower() == 'true'
        return context

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

class ProjectToProductView(APIView):
    """
    Convert a project to a product.
    Only allowed when:
    - All contracts are closed
    - Project status is finalized
    - Progress status is completed
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, project_id):
        try:
            project = Project.objects.select_related(
                'progress_status', 'status', 'type', 'language',
                'author', 'translator', 'rights_owner', 'reviewer'
            ).prefetch_related('contract_set').get(id=project_id)
        except Project.DoesNotExist:
            return Response(
                {"error": "Project not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if project already has a product
        if Product.objects.filter(project=project).exists():
            return Response(
                {"error": "This project has already been converted to a product"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check conditions: all contracts closed, status finalized, progress completed
        contracts = project.contract_set.all()
        
        # Check if all contracts are closed
        closed_status = ListItem.objects.filter(
            list_type__code="contract_status",
            value__iexact="closed"
        ).first()
        
        if closed_status:
            open_contracts = contracts.exclude(status=closed_status)
            if open_contracts.exists():
                return Response(
                    {"error": "All contracts must be closed before converting to product"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Check if project status is finalized
        finalized_status = ListItem.objects.filter(
            list_type__code="projects_status",
            value__iexact="finalized"
        ).first()
        
        if finalized_status and project.status != finalized_status:
            return Response(
                {"error": "Project status must be finalized before converting to product"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if progress status is completed
        completed_status = ListItem.objects.filter(
            list_type__code="progress_status",
            value__iexact="completed"
        ).first()
        
        if completed_status and project.progress_status != completed_status:
            return Response(
                {"error": "Progress status must be completed before converting to product"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get available status for product
        available_status = ListItem.objects.filter(
            list_type__code="product_status",
            value__iexact="available"
        ).first()
        
        if not available_status:
            return Response(
                {"error": "Available status not found in product_status list"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Extract contract parties by type
        author_id = None
        translator_id = None
        rights_owner_id = None
        reviewer_id = None
        
        for contract in contracts:
            contract_type_name = contract.contract_type.value.lower() if contract.contract_type else ""
            if 'author' in contract_type_name and contract.contracted_party:
                # Get the author ID from the generic foreign key
                if contract.content_type.model == 'author':
                    author_id = contract.object_id
            elif 'translator' in contract_type_name and contract.contracted_party:
                if contract.content_type.model == 'translator':
                    translator_id = contract.object_id
            elif 'rights' in contract_type_name and contract.contracted_party:
                if contract.content_type.model == 'rightsowner':
                    rights_owner_id = contract.object_id
            elif 'reviewer' in contract_type_name and contract.contracted_party:
                if contract.content_type.model == 'reviewer':
                    reviewer_id = contract.object_id
        
        # Fallback to project's assigned parties if not found in contracts
        if not author_id and project.author:
            author_id = project.author.id
        if not translator_id and project.translator:
            translator_id = project.translator.id
        if not rights_owner_id and project.rights_owner:
            rights_owner_id = project.rights_owner.id
        if not reviewer_id and project.reviewer:
            reviewer_id = project.reviewer.id
        
        # Get default genre and language
        default_genre = ListItem.objects.filter(id=9).first()
        default_language = ListItem.objects.filter(id=50).first()
        
        # Use project's language if available, otherwise use default
        product_language = project.language if project.language else default_language
        
        # Create product with transaction
        with transaction.atomic():
            product = Product.objects.create(
                project=project,
                isbn="000-000",  # Default ISBN
                title_ar=project.title_ar,
                title_en=project.title_original or project.title_ar,
                cover_design="https://dararab.co.uk/wp-content/uploads/2022/07/dararab-logo-1.png",
                genre=default_genre,  # Default genre_id=9
                status=available_status,
                language=product_language,  # Use project language or default (50)
                author_id=author_id,
                translator_id=translator_id,
                rights_owner_id=rights_owner_id,
                reviewer_id=reviewer_id,
                is_direct_product=True,
                created_by=request.user,
                updated_by=request.user
            )
        
        # Serialize and return the created product
        serializer = ProductSerializer(product)
        return Response(
            {
                "message": "Project successfully converted to product",
                "product": serializer.data
            },
            status=status.HTTP_201_CREATED
        )

class ProjectsBootstrapView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Bootstrap endpoint for projects page.
        Returns all static data needed for the projects page in a single request.
        """
        # List items for projects
        progress_statuses = ListItem.objects.filter(
            list_type__code="progress_status", 
            is_active=True
        ).order_by("display_name_en")
        
        projects_statuses = ListItem.objects.filter(
            list_type__code="projects_status", 
            is_active=True
        ).order_by("display_name_en")
        
        projects_types = ListItem.objects.filter(
            list_type__code="projects_type", 
            is_active=True
        ).order_by("display_name_en")
        
        listitem_context = {"request": request}
        progress_statuses_data = ListItemSerializer(
            progress_statuses, many=True, context=listitem_context
        ).data
        projects_statuses_data = ListItemSerializer(
            projects_statuses, many=True, context=listitem_context
        ).data
        projects_types_data = ListItemSerializer(
            projects_types, many=True, context=listitem_context
        ).data
        
        # People data
        authors_data = AuthorSerializer(
            Author.objects.order_by("name"), many=True, context={"request": request}
        ).data
        translators_data = TranslatorSerializer(
            Translator.objects.order_by("name"), many=True, context={"request": request}
        ).data
        rights_owners_data = RightsOwnerSerializer(
            RightsOwner.objects.order_by("name"), many=True, context={"request": request}
        ).data
        reviewers_data = ReviewerSerializer(
            Reviewer.objects.order_by("name"), many=True, context={"request": request}
        ).data
        
        return Response({
            "progress_options": progress_statuses_data,
            "status_options": projects_statuses_data,
            "type_options": projects_types_data,
            "authors": authors_data,
            "translators": translators_data,
            "rights_owners": rights_owners_data,
            "reviewers": reviewers_data,
        })


class ContractsBootstrapView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Bootstrap endpoint for contracts page.
        Returns all static data needed for the contracts page in a single request.
        Note: Projects are fetched separately with pagination.
        """
        # Contract types
        contract_types = ListItem.objects.filter(
            list_type__code="contract_type",
            is_active=True
        ).order_by("id")
        
        # Contract statuses
        contract_statuses = ListItem.objects.filter(
            list_type__code="contract_status",
            is_active=True
        ).order_by("id")
        
        # Royalties types
        royalties_types = ListItem.objects.filter(
            list_type__code="royalties_type",
            is_active=True
        ).order_by("id")
        
        listitem_context = {"request": request}
        contract_types_data = ListItemSerializer(
            contract_types, many=True, context=listitem_context
        ).data
        contract_statuses_data = ListItemSerializer(
            contract_statuses, many=True, context=listitem_context
        ).data
        royalties_types_data = ListItemSerializer(
            royalties_types, many=True, context=listitem_context
        ).data
        
        # Signatories (users)
        signatories_data = UserBasicSerializer(
            User.objects.filter(is_active=True).order_by("username"),
            many=True,
            context={"request": request}
        ).data
        
        # People data
        authors_data = AuthorSerializer(
            Author.objects.order_by("name"), many=True, context={"request": request}
        ).data
        translators_data = TranslatorSerializer(
            Translator.objects.order_by("name"), many=True, context={"request": request}
        ).data
        rights_owners_data = RightsOwnerSerializer(
            RightsOwner.objects.order_by("name"), many=True, context={"request": request}
        ).data
        reviewers_data = ReviewerSerializer(
            Reviewer.objects.order_by("name"), many=True, context={"request": request}
        ).data
        
        return Response({
            "contract_types": contract_types_data,
            "contract_statuses": contract_statuses_data,
            "royalties_types": royalties_types_data,
            "signatories": signatories_data,
            "authors": authors_data,
            "translators": translators_data,
            "rights_owners": rights_owners_data,
            "reviewers": reviewers_data,
        })

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
                .prefetch_related("print_runs")
                .get(pk=pk)
            )
        except Product.DoesNotExist:
            raise Http404("Product not found.")
        except Exception as e:
            return Response(
                {"detail": f"Error fetching product: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            product_data = ProductSerializer(product, context={"request": request}).data
        except Exception as e:
            return Response(
                {"detail": f"Error serializing product: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            inventory_qs = Inventory.objects.filter(product_id=pk).select_related("warehouse")
            inventory_data = InventorySerializer(inventory_qs, many=True, context={"request": request}).data
        except Exception as e:
            return Response(
                {"detail": f"Error serializing inventory: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            print_runs_qs = PrintRun.objects.filter(product_id=pk).select_related("status").order_by("edition_number")
            print_runs_data = PrintRunSerializer(print_runs_qs, many=True, context={"request": request}).data
        except Exception as e:
            return Response(
                {"detail": f"Error serializing print runs: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['product', 'warehouse', 'quantity', 'updated_at', 'created_at']
    ordering = ['-created_at', 'id']  # Default ordering

    def get_queryset(self):
        queryset = Inventory.objects.select_related('product', 'warehouse')
        product_id = self.request.query_params.get('product_id')
        warehouse_id = self.request.query_params.get('warehouse_id')

        if product_id:
            queryset = queryset.filter(product_id=product_id)
        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)
        
        # Note: Ordering is handled by OrderingFilter, so we don't need to call order_by here
        # The default ordering is set via the 'ordering' attribute
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

class InventoryBulkDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        """
        Bulk delete inventory items.
        Expects a list of inventory IDs in the request body: {"ids": [1, 2, 3]}
        Returns detailed results including which items were deleted and which failed.
        """
        if not isinstance(request.data, dict) or 'ids' not in request.data:
            return Response(
                {"detail": "Expected a dictionary with 'ids' key containing a list of inventory IDs."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ids = request.data.get('ids', [])
        if not isinstance(ids, list) or len(ids) == 0:
            return Response(
                {"detail": "Empty list provided. At least one inventory ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate all IDs are integers
        try:
            ids = [int(id) for id in ids]
        except (ValueError, TypeError):
            return Response(
                {"detail": "All IDs must be integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get all inventory items that exist
        inventories = Inventory.objects.filter(id__in=ids)
        existing_ids = set(inventories.values_list('id', flat=True))
        missing_ids = set(ids) - existing_ids

        # Track results
        deleted_ids = []
        failed_ids = []
        errors = []

        # Delete each inventory item
        for inventory in inventories:
            try:
                inventory_id = inventory.id
                inventory.delete()
                deleted_ids.append(inventory_id)
            except ProtectedError as e:
                failed_ids.append(inventory.id)
                errors.append({
                    "id": inventory.id,
                    "error": "Cannot delete due to related data.",
                    "detail": str(e)
                })
            except Exception as e:
                failed_ids.append(inventory.id)
                errors.append({
                    "id": inventory.id,
                    "error": str(e)
                })

        # Add missing IDs to failed list
        for missing_id in missing_ids:
            failed_ids.append(missing_id)
            errors.append({
                "id": missing_id,
                "error": "Inventory item not found."
            })

        # Prepare response
        response_data = {
            "deleted_count": len(deleted_ids),
            "failed_count": len(failed_ids),
            "total_requested": len(ids),
            "deleted_ids": deleted_ids,
            "failed_ids": failed_ids,
            "errors": errors
        }

        # Return appropriate status code
        if len(failed_ids) == 0:
            # All succeeded
            return Response(response_data, status=status.HTTP_200_OK)
        elif len(deleted_ids) == 0:
            # All failed
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Partial success
            return Response(response_data, status=status.HTTP_207_MULTI_STATUS)

class InventoryBulkUpsertView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if not isinstance(request.data, list):
            return Response(
                {"detail": "Expected a list of inventory objects."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(request.data) == 0:
            return Response(
                {"detail": "Empty list provided. At least one inventory item is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        results = []
        errors = []
        
        # Validate all items first before processing
        validated_data = []
        for index, item in enumerate(request.data):
            if not isinstance(item, dict):
                return Response(
                    {"detail": f"Item at index {index} must be a dictionary."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # If item has an id, it's an update - only quantity is required
            # If item doesn't have an id, it's a create - product_id, warehouse_id, and quantity are required
            pk = item.get("id")
            
            if pk:
                # Update: only quantity is required
                if "quantity" not in item:
                    return Response(
                        {"detail": f"Item at index {index} is missing 'quantity'."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                # Create: product_id, warehouse_id, and quantity are required
                if "product_id" not in item:
                    return Response(
                        {"detail": f"Item at index {index} is missing 'product_id'."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if "warehouse_id" not in item:
                    return Response(
                        {"detail": f"Item at index {index} is missing 'warehouse_id'."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if "quantity" not in item:
                    return Response(
                        {"detail": f"Item at index {index} is missing 'quantity'."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            
            validated_data.append(item)

        # Process all items in a single transaction
        try:
            with transaction.atomic():
                for index, item_data in enumerate(validated_data):
                    pk = item_data.get("id")
                    
                    if pk:
                        # Update existing inventory
                        try:
                            instance = Inventory.objects.get(pk=pk)
                            serializer = InventorySerializer(
                                instance,
                                data=item_data,
                                partial=True,
                                context={"request": request},
                            )
                            serializer.is_valid(raise_exception=True)
                            serializer.save(updated_by=request.user)
                            results.append(serializer.data)
                        except Inventory.DoesNotExist:
                            raise serializers.ValidationError(
                                {f"index_{index}": f"Inventory with id {pk} not found."}
                            )
                    else:
                        # Create new inventory or update existing (handles unique_together constraint)
                        product_id = item_data.get("product_id")
                        warehouse_id = item_data.get("warehouse_id")
                        quantity = item_data.get("quantity", 0)
                        
                        # Check if inventory already exists for this product+warehouse combination
                        # Due to unique_together constraint, only one inventory per product+warehouse
                        existing = Inventory.objects.filter(
                            product_id=product_id,
                            warehouse_id=warehouse_id
                        ).first()
                        
                        if existing:
                            # Update existing inventory - replace quantity with new value
                            # This ensures one inventory record per product+warehouse combination
                            old_quantity = existing.quantity
                            serializer = InventorySerializer(
                                existing,
                                data=item_data,
                                partial=True,
                                context={"request": request},
                            )
                            serializer.is_valid(raise_exception=True)
                            serializer.save(updated_by=request.user)
                            result_data = serializer.data
                            result_data['_action'] = 'updated'
                            result_data['_old_quantity'] = old_quantity
                            results.append(result_data)
                        else:
                            # Create new inventory
                            serializer = InventorySerializer(
                                data=item_data,
                                context={"request": request},
                            )
                            serializer.is_valid(raise_exception=True)
                            serializer.save(
                                created_by=request.user,
                                updated_by=request.user,
                            )
                            result_data = serializer.data
                            result_data['_action'] = 'created'
                            results.append(result_data)

            return Response(
                {
                    "detail": f"Successfully processed {len(results)} inventory item(s).",
                    "results": results,
                    "count": len(results),
                },
                status=status.HTTP_200_OK,
            )
            
        except serializers.ValidationError as exc:
            return Response(
                {"detail": "Validation failed", "errors": exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            return Response(
                {"detail": f"Error processing bulk inventory: {str(exc)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
    queryset = Contract.objects.select_related(
        'project',
        'contract_type',
        'signed_by',
        'status'
    ).order_by('-created_at', 'id')
    serializer_class = ContractSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by project_id if provided
        project_id = self.request.query_params.get('project_id')
        if project_id:
            try:
                queryset = queryset.filter(project_id=int(project_id))
            except (ValueError, TypeError):
                pass  # Ignore invalid project_id
        
        # Ensure select_related is maintained
        return queryset.select_related(
            'project',
            'contract_type',
            'signed_by',
            'status'
        ).order_by('-created_at', 'id')

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
    filter_backends    = [filters.OrderingFilter]
    ordering_fields    = ['id', 'title_en', 'title_ar', 'isbn', 'latest_price', 'status_id', 'created_at']
    ordering           = ['id']  # Default ordering

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
                stock=Coalesce(Sum('inventory__quantity'), Value(0)),
                latest_price=Subquery(latest.values('price')[:1]),
                latest_price_omr=Subquery(latest.values('price_omr')[:1]),
            )
            .select_related('genre', 'status', 'language', 'author', 'translator')
            .prefetch_related('print_runs')
        )

        if search:
            queryset = queryset.filter(
                Q(isbn__icontains=search)
                | Q(title_en__icontains=search)
                | Q(title_ar__icontains=search)
                | Q(author__isnull=False, author__name__icontains=search)
                | Q(translator__isnull=False, translator__name__icontains=search)
            )

        if genre_id:
            queryset = queryset.filter(genre_id=genre_id)

        if status_id:
            queryset = queryset.filter(status_id=status_id)

        if language_id:
            queryset = queryset.filter(language_id=language_id)

        # Note: Ordering is handled by OrderingFilter, so we don't need to call order_by here
        return queryset
    def get_serializer_context(self):

        return { 'request': self.request }
    
class POSProductViewSet(viewsets.ModelViewSet):
    serializer_class = POSProductSummarySerializer
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        latest = PrintRun.objects.filter(product=OuterRef('pk'))\
                                 .order_by('-edition_number')
        queryset = (
            Product.objects
                   .annotate(
                       editions_count=Count('print_runs', distinct=True),
                       stock=Sum('inventory__quantity'),
                       latest_price=Subquery(latest.values('price')[:1]),
                       latest_price_omr=Subquery(latest.values('price_omr')[:1]),
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
        
        # Server-side search filtering
        search = self.request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(title_en__icontains=search) |
                Q(title_ar__icontains=search) |
                Q(isbn__icontains=search)
            )
        
        # Server-side genre filtering
        genre_id = self.request.query_params.get('genre_id')
        if genre_id:
            try:
                genre_id_int = int(genre_id)
                queryset = queryset.filter(genre_id=genre_id_int)
            except (ValueError, TypeError):
                pass  # Ignore invalid genre_id
            
        return queryset
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['warehouse_id'] = self.request.query_params.get('warehouse_id')
        return context

