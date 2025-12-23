from rest_framework import serializers
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
import os

from users.serializers import User, UserBasicSerializer
from .models import (PrintRun, PrintTask, Product, Stakeholder, Warehouse, Inventory, Transfer,
    Author, Translator, RightsOwner, Reviewer,
    Project, Contract
)
from common.models import ListItem
from common.serializers import ListItemSerializer
from django.contrib.contenttypes.models import ContentType


class CoverDesignSerializerField(serializers.Field):
    """
    Custom serializer field that handles both file uploads and URLs for cover design
    """
    
    def to_representation(self, value):
        if not value:
            return None
        
        # If it's a URL, return as is
        url_validator = URLValidator()
        try:
            url_validator(value)
            return value
        except ValidationError:
            # It's a file path, return the full URL
            request = self.context.get('request')
            if request and hasattr(request, 'build_absolute_uri'):
                return request.build_absolute_uri(value)
            return value
    
    def to_internal_value(self, data):
        if not data:
            return None
        
        # If it's a file object, handle the upload
        if hasattr(data, 'read'):
            # This is a file upload
            from django.core.files.storage import default_storage
            from django.core.files.base import ContentFile
            
            # Generate a unique filename
            import uuid
            file_extension = os.path.splitext(data.name)[1]
            filename = f"{uuid.uuid4()}{file_extension}"
            file_path = f"book_covers/{filename}"
            
            # Save the file
            file_content = ContentFile(data.read())
            saved_path = default_storage.save(file_path, file_content)
            return saved_path
        
        # If it's a string, validate if it's a URL or file path
        if isinstance(data, str):
            url_validator = URLValidator()
            try:
                url_validator(data)
                # It's a valid URL
                return data
            except ValidationError:
                # Check if it's a valid file path
                if data.startswith('book_covers/'):
                    return data
                else:
                    raise serializers.ValidationError(
                        "Cover design must be a valid URL or file upload"
                    )
        
        raise serializers.ValidationError(
            "Cover design must be a valid URL or file upload"
        )


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = '__all__'
        read_only_fields = ['created_by', 'updated_by', 'created_at', 'updated_at']



class TransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transfer
        fields = '__all__'
        read_only_fields = ['created_by', 'updated_by', 'created_at', 'updated_at']


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = '__all__'

class TranslatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Translator
        fields = '__all__'

class RightsOwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = RightsOwner
        fields = '__all__'

class ReviewerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reviewer
        fields = '__all__'

class StakeholderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stakeholder
        fields = '__all__'
        read_only_fields = ['created_by', 'updated_by', 'created_at', 'updated_at']

class ProjectBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'title_ar', 'title_original']

class ProductSerializer(serializers.ModelSerializer):
    # ✅ Read-only nested objects
    project= ProjectBasicSerializer(read_only=True)
    author= AuthorSerializer(read_only=True)
    translator= TranslatorSerializer(read_only=True)
    rights_owner= RightsOwnerSerializer(read_only=True)
    reviewer= ReviewerSerializer(read_only=True)
    genre= ListItemSerializer(read_only=True)
    status= ListItemSerializer(read_only=True)
    language= ListItemSerializer(read_only=True)
    
    # Custom field for cover design
    cover_design = CoverDesignSerializerField()

    # ✅ Writable IDs for creation and update
    project_id= serializers.PrimaryKeyRelatedField(
                          queryset=Product.objects.all(),  # or Project.objects
                          source='project',
                          write_only=True,
                          required=False)
    author_id= serializers.PrimaryKeyRelatedField(
                          queryset=Author.objects.all(),
                          source='author',
                          write_only=True,
                          required=False)
    translator_id= serializers.PrimaryKeyRelatedField(
                          queryset=Translator.objects.all(),
                          source='translator',
                          write_only=True,
                          required=False)
    rights_owner_id= serializers.PrimaryKeyRelatedField(
                          queryset=RightsOwner.objects.all(),
                          source='rights_owner',
                          write_only=True,
                          required=False)
    reviewer_id= serializers.PrimaryKeyRelatedField(
                          queryset=Reviewer.objects.all(),
                          source='reviewer',
                          write_only=True,
                          required=False)
    genre_id= serializers.PrimaryKeyRelatedField(
                          queryset=ListItem.objects.all(),
                          source='genre',
                          write_only=True,
                          required=True)
    status_id= serializers.PrimaryKeyRelatedField(
                          queryset=ListItem.objects.all(),
                          source='status',
                          write_only=True,
                          required=True)
    language_id= serializers.PrimaryKeyRelatedField(
                          queryset=ListItem.objects.all(),
                          source='language',
                          write_only=True,
                          required=False)

    class Meta:
        model = Product
        fields = [
            "id",
            "isbn",
            "title_ar",
            "title_en",
            "cover_design",
            

            # Nested output
            "project", "author", "translator", "rights_owner", "reviewer",
            "genre", "status", "language",

            # Writable IDs
            "project_id", "author_id", "translator_id", "rights_owner_id", "reviewer_id",
            "genre_id", "status_id", "language_id",

            "is_direct_product",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_by", "updated_by", "created_at", "updated_at"]


class PrintRunSerializer(serializers.ModelSerializer):
    product= serializers.StringRelatedField(read_only=True)
    product_id= serializers.PrimaryKeyRelatedField(
                      queryset=Product.objects.all(),
                      source='product',
                      write_only=True)
    status= ListItemSerializer(read_only=True)
    status_id= serializers.PrimaryKeyRelatedField(
                      queryset=ListItem.objects.all(),
                      source='status',
                      write_only=True
                  )

    class Meta:
        model = PrintRun
        fields = [
          'id', 'product', 'product_id',
          'edition_number', 'price_omr', 'price',
          'status', 'status_id', 'notes','published_at', 
          'created_by', 'updated_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_by', 'updated_by', 'created_at', 'updated_at']
class InventorySerializer(serializers.ModelSerializer):
    # Nested read-only representations
    product = ProductSerializer(read_only=True)
    warehouse = WarehouseSerializer(read_only=True)
    
    # Writable ID fields for dropdowns
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product', write_only=True, required=False
    )
    warehouse_id = serializers.PrimaryKeyRelatedField(
        queryset=Warehouse.objects.all(), source='warehouse', write_only=True, required=False
    )
    
    class Meta:
        model = Inventory
        fields = [
            'id', 'quantity',
            
            # Nested output
            'product', 'warehouse',
            
            # Writable input
            'product_id', 'warehouse_id',
            
            'created_by', 'updated_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_by', 'updated_by', 'created_at', 'updated_at']
        
    def validate(self, data):
        # For updates (PATCH), product and warehouse are already set on the instance
        # Only validate these fields when creating (POST) or when explicitly provided
        instance = getattr(self, 'instance', None)
        is_update = instance is not None
        
        if not is_update:
            # Creating new inventory - product and warehouse are required
            has_product = 'product' in data or 'product_id' in data
            if not has_product:
                # Check initial_data if available (for bulk operations)
                initial = getattr(self, 'initial_data', {})
                if isinstance(initial, dict):
                    has_product = 'product' in initial or 'product_id' in initial
                if not has_product:
                    raise serializers.ValidationError({"product_id": "Product is required"})
            
            has_warehouse = 'warehouse' in data or 'warehouse_id' in data
            if not has_warehouse:
                # Check initial_data if available (for bulk operations)
                initial = getattr(self, 'initial_data', {})
                if isinstance(initial, dict):
                    has_warehouse = 'warehouse' in initial or 'warehouse_id' in initial
                if not has_warehouse:
                    raise serializers.ValidationError({"warehouse_id": "Warehouse is required"})
        # For updates, if product_id or warehouse_id are provided, validate them
        # But they're not required since the instance already has them
            
        return data
    
class ProjectSerializer(serializers.ModelSerializer):
    # ✅ Read-only nested objects
    author = AuthorSerializer(read_only=True)
    translator = TranslatorSerializer(read_only=True)
    rights_owner = RightsOwnerSerializer(read_only=True)
    reviewer = ReviewerSerializer(read_only=True)
    progress_status = ListItemSerializer(read_only=True)
    status = ListItemSerializer(read_only=True)
    type = ListItemSerializer(read_only=True)
    language = ListItemSerializer(read_only=True)
    contracts = serializers.SerializerMethodField()

    # ✅ Writable IDs for creation and update
    author_id = serializers.PrimaryKeyRelatedField(
        queryset=Author.objects.all(), source='author', write_only=True, required=False
    )
    translator_id = serializers.PrimaryKeyRelatedField(
        queryset=Translator.objects.all(), source='translator', write_only=True, required=False
    )
    rights_owner_id = serializers.PrimaryKeyRelatedField(
        queryset=RightsOwner.objects.all(), source='rights_owner', write_only=True, required=False
    )
    reviewer_id = serializers.PrimaryKeyRelatedField(
        queryset=Reviewer.objects.all(), source='reviewer', write_only=True, required=False
    )
    progress_status_id = serializers.PrimaryKeyRelatedField(
        queryset=ListItem.objects.all(), source='progress_status', write_only=True, required=False
    )
    status_id = serializers.PrimaryKeyRelatedField(
        queryset=ListItem.objects.all(), source='status', write_only=True, required=False
    )
    type_id = serializers.PrimaryKeyRelatedField(
        queryset=ListItem.objects.all(), source='type', write_only=True, required=False
    )
    language_id = serializers.PrimaryKeyRelatedField(
        queryset=ListItem.objects.all(), source='language', write_only=True, required=False
    )

    def get_contracts(self, obj):
        # Only include contracts if include_contracts is True in context
        include_contracts = self.context.get('include_contracts', False)
        if include_contracts:
            # Use prefetched contracts if available
            contracts = getattr(obj, 'contract_set', None)
            if contracts is not None:
                # Return basic contract data to avoid deep nesting
                return [
                    {
                        'id': c.id,
                        'title': c.title,
                        'contract_type': {'id': c.contract_type.id, 'display_name_en': str(c.contract_type)} if c.contract_type else None,
                        'start_date': c.start_date.isoformat() if c.start_date else None,
                        'end_date': c.end_date.isoformat() if c.end_date else None,
                        'commission_percent': c.commission_percent,
                        'fixed_amount': c.fixed_amount,
                        'free_copies': c.free_copies,
                        'contract_duration': c.contract_duration,
                        'payment_schedule': c.payment_schedule,
                        'notes': c.notes,
                        'created_at': c.created_at.isoformat() if c.created_at else None,
                        'updated_at': c.updated_at.isoformat() if c.updated_at else None,
                    }
                    for c in contracts.all()
                ]
        return None
    
    has_product = serializers.SerializerMethodField()
    all_contracts_closed = serializers.SerializerMethodField()
    
    def get_has_product(self, obj):
        """Check if this project has already been converted to a product"""
        # Use annotated value if available (from queryset optimization)
        if hasattr(obj, 'has_product'):
            return obj.has_product
        # Fallback to direct query if annotation not available
        from .models import Product
        return Product.objects.filter(project=obj).exists()
    
    def get_all_contracts_closed(self, obj):
        """Check if all contracts for this project are closed"""
        # Use annotated value if available (from queryset optimization)
        if hasattr(obj, 'all_contracts_closed'):
            return obj.all_contracts_closed
        # Fallback to direct query if annotation not available
        from .models import Contract
        from common.models import ListItem
        
        contracts = Contract.objects.filter(project=obj)
        if not contracts.exists():
            return True  # No contracts means all are "closed" (none to close)
        
        closed_status = ListItem.objects.filter(
            list_type__code="contract_status",
            value__iexact="closed"
        ).first()
        
        if not closed_status:
            return False  # Can't determine if closed status exists
        
        # Check if all contracts have closed status
        open_contracts = contracts.exclude(status=closed_status)
        return not open_contracts.exists()

    class Meta:
        model = Project
        fields = [
            "id",
            "title_ar",
            "title_original",
            "manuscript",
            "description",
            "approval_status",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "contracts",
            "has_product",
            "all_contracts_closed",

            # Nested output
            "author", "translator", "rights_owner", "reviewer",
            "progress_status", "status", "type", "language",

            # Writable IDs
            "author_id", "translator_id", "rights_owner_id", "reviewer_id",
            "progress_status_id", "status_id", "type_id", "language_id",
        ]
        read_only_fields = ["created_by", "updated_by", "created_at", "updated_at", "has_product", "all_contracts_closed"]

class ContractedPartyField(serializers.Field):
    def to_representation(self, value):
        if hasattr(value, 'name'):
            return {
                'id': value.id,
                'name': value.name,
                'type': value._meta.model_name
            }
        return None

    def to_internal_value(self, data):
        try:
            model_name = data.get('type')
            model_id = data.get('id')
            
            if not model_name or not model_id:
                raise serializers.ValidationError("Both type and id are required")
            
            model_map = {
                'author': Author,
                'translator': Translator,
                'rightsowner': RightsOwner,
                'reviewer': Reviewer,
                'stakeholder': Stakeholder
            }
            
            Model = model_map.get(model_name.lower())
            if not Model:
                raise serializers.ValidationError(f"Invalid type: {model_name}")
            
            instance = Model.objects.get(id=model_id)
            return instance
        except (KeyError, Model.DoesNotExist):
            raise serializers.ValidationError("Invalid contracted party data")

class ProjectBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'title_ar', 'title_original']

class ContractSerializer(serializers.ModelSerializer):
    # Read-only nested serializers
    status = ListItemSerializer(read_only=True)
    contract_type = ListItemSerializer(read_only=True)
    royalties_type = ListItemSerializer(read_only=True)
    project = ProjectBasicSerializer(read_only=True)
    signed_by = UserBasicSerializer(read_only=True)

    status_id = serializers.SerializerMethodField()
    def get_status_id(self, obj):
        return obj.status.id if obj.status else None

    # Write-only ID fields
    status_id_write = serializers.PrimaryKeyRelatedField(
    source='status',
    queryset=ListItem.objects.all(),
    write_only=True,
    required=True
)
    # status_id = serializers.PrimaryKeyRelatedField(
    #     source='status',
    #     queryset=ListItem.objects.all(),
    #     write_only=True,
    #     required=True
    # )
    contract_type_id = serializers.SerializerMethodField()
    contract_type_id_write = serializers.PrimaryKeyRelatedField(
    source='contract_type',
    queryset=ListItem.objects.all(),
    write_only=True,
    required=True
)
    def get_contract_type_id(self, obj):
        return obj.contract_type.id if obj.contract_type else None
    
    royalties_type_id = serializers.SerializerMethodField()
    royalties_type_id_write = serializers.PrimaryKeyRelatedField(
        source='royalties_type',
        queryset=ListItem.objects.all(),
        write_only=True,
        required=False,
        allow_null=True
    )
    def get_royalties_type_id(self, obj):
        return obj.royalties_type.id if obj.royalties_type else None
    
    project_id = serializers.PrimaryKeyRelatedField(
        source='project',
        queryset=Project.objects.all(),
        write_only=True,
        required=True
    )
    signed_by_id = serializers.PrimaryKeyRelatedField(
        source='signed_by',
        queryset=User.objects.all(),
        write_only=True,
        required=False,
        allow_null=True
    )

    # Contracted party handling
    contracted_party_type = serializers.CharField(write_only=True)
    contracted_party_id = serializers.IntegerField(write_only=True)
    contracted_party_details = serializers.SerializerMethodField()

    contracted_party_type_value = serializers.SerializerMethodField()
    contracted_party_id_value = serializers.SerializerMethodField()

    def get_contracted_party_type_value(self, obj):
        return obj.contracted_party._meta.model_name if obj.contracted_party else None

    def get_contracted_party_id_value(self, obj):
        return obj.contracted_party.id if obj.contracted_party else None


    

    class Meta:
        model = Contract
        fields = [
            'id', 'title', 'project', 'project_id',
            'contract_type', 'contract_type_id','contract_type_id_write',
            'status', 'status_id','status_id_write',
            'royalties_type', 'royalties_type_id', 'royalties_type_id_write',
            'signed_by', 'signed_by_id',
            'contracted_party_type', 'contracted_party_id', 'contracted_party_details',
            'contracted_party_type_value', 'contracted_party_id_value',
            'commission_percent', 'fixed_amount', 'free_copies',
            'contract_duration', 'start_date', 'end_date',
            'payment_schedule', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']

    def validate(self, data):
        # Ensure contract type and status exist
        if not data.get('contract_type'):
            raise serializers.ValidationError({'contract_type_id': 'This field is required.'})
        if not data.get('status'):
            raise serializers.ValidationError({'status_id': 'This field is required.'})
        return data

    def get_contracted_party_details(self, obj):
        if obj.contracted_party:
            return {
                'id': obj.contracted_party.id,
                'name': obj.contracted_party.name,
                'type': obj.contracted_party._meta.model_name
            }
        return None

    def _set_contracted_party(self, validated_data, party_type, party_id):
        model_map = {
            'author': Author,
            'translator': Translator,
            'rightsowner': RightsOwner,
            'reviewer': Reviewer,
            'stakeholder': Stakeholder
        }

        Model = model_map.get(party_type.lower())
        if Model:
            try:
                contracted_party = Model.objects.get(id=party_id)
                validated_data['content_type'] = ContentType.objects.get_for_model(Model)
                validated_data['object_id'] = contracted_party.id
            except Model.DoesNotExist:
                raise serializers.ValidationError(
                    f"{party_type} with id {party_id} does not exist."
                )
        else:
            raise serializers.ValidationError(f"Invalid party type: {party_type}")

    def create(self, validated_data):
        party_type = validated_data.pop('contracted_party_type', None)
        party_id = validated_data.pop('contracted_party_id', None)

        if party_type and party_id:
            self._set_contracted_party(validated_data, party_type, party_id)

        print("🟢 Creating Contract with validated data:", validated_data)  # Debug
        return super().create(validated_data)

    def update(self, instance, validated_data):
        party_type = validated_data.pop('contracted_party_type', None)
        party_id = validated_data.pop('contracted_party_id', None)

        if party_type and party_id:
            self._set_contracted_party(validated_data, party_type, party_id)

        print("🟡 Updating Contract with validated data:", validated_data)  # Debug
        return super().update(instance, validated_data)

      
class PrintTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrintTask
        fields = '__all__'
        read_only_fields = ['created_by', 'updated_by', 'created_at', 'updated_at']

class ProductSummarySerializer(serializers.ModelSerializer):
    genre_id      = serializers.SerializerMethodField()
    status_id     = serializers.SerializerMethodField()
    language_id   = serializers.SerializerMethodField()
    
    def get_genre_id(self, obj):
        return obj.genre.id if obj.genre else None
    
    def get_status_id(self, obj):
        return obj.status.id if obj.status else None
    
    def get_language_id(self, obj):
        return obj.language.id if obj.language else None
    genre_name    = serializers.SerializerMethodField()
    status_name   = serializers.SerializerMethodField()
    language_name = serializers.SerializerMethodField()
    author_name     = serializers.SerializerMethodField()
    translator_name = serializers.SerializerMethodField()
    
    def get_genre_name(self, obj):
        return obj.genre.display_name_en if obj.genre else None
    
    def get_status_name(self, obj):
        return obj.status.display_name_en if obj.status else None
    
    def get_language_name(self, obj):
        return obj.language.display_name_en if obj.language else None
    
    def get_author_name(self, obj):
        return obj.author.name if obj.author else None
    
    def get_translator_name(self, obj):
        return obj.translator.name if obj.translator else None
    editions_count = serializers.IntegerField()
    stock          = serializers.IntegerField()
    latest_price   = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    latest_price_omr = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    cover_design_url = serializers.SerializerMethodField()

    class Meta:
        model  = Product
        fields = [
            'id', 'title_ar', 'title_en', 'isbn',
            'genre_id','status_id', 'language_id',
            'genre_name', 'status_name', 'language_name',
            'author_name', 'translator_name',
            'editions_count', 'stock',
            'latest_price', 'latest_price_omr', "cover_design_url"
        ]
    
    def get_cover_design_url(self, obj):
        if not obj.cover_design:
            return None
            
        request = self.context.get("request")
        
        # Check if it's a URL
        url_validator = URLValidator()
        try:
            url_validator(obj.cover_design)
            # It's already a URL, return as is
            return obj.cover_design
        except ValidationError:
            # It's a file path, build the full URL
            if request and hasattr(request, 'build_absolute_uri'):
                return request.build_absolute_uri(obj.cover_design)
            return obj.cover_design

class POSProductSummarySerializer(ProductSummarySerializer):
    warehouse_stock = serializers.SerializerMethodField()
    
    class Meta(ProductSummarySerializer.Meta):
        fields = ProductSummarySerializer.Meta.fields + ['warehouse_stock']
    
    def get_warehouse_stock(self, obj):
        warehouse_id = self.context.get('warehouse_id')
        if warehouse_id:
            try:
                inventory = Inventory.objects.get(product=obj, warehouse_id=warehouse_id)
                return inventory.quantity
            except Inventory.DoesNotExist:
                return 0
        return None