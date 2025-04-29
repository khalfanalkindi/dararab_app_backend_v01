from rest_framework import serializers

from users.serializers import User, UserBasicSerializer
from .models import (PrintRun, PrintTask, Product, Stakeholder, Warehouse, Inventory, Transfer,
    Author, Translator, RightsOwner, Reviewer,
    Project, Contract
)
from common.models import ListItem
from common.serializers import ListItemSerializer
from django.contrib.contenttypes.models import ContentType



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
            "genre", "status",

            # Writable IDs
            "project_id", "author_id", "translator_id", "rights_owner_id", "reviewer_id",
            "genre_id", "status_id",

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
          'edition_number', 'print_cost', 'price',
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
        # Check if we have either product_id or product
        if 'product' not in data and 'product_id' not in self.initial_data:
            raise serializers.ValidationError({"product": "Product is required"})
            
        # Check if we have either warehouse_id or warehouse
        if 'warehouse' not in data and 'warehouse_id' not in self.initial_data:
            raise serializers.ValidationError({"warehouse": "Warehouse is required"})
            
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

            # Nested output
            "author", "translator", "rights_owner", "reviewer",
            "progress_status", "status", "type",

            # Writable IDs
            "author_id", "translator_id", "rights_owner_id", "reviewer_id",
            "progress_status_id", "status_id", "type_id",
        ]
        read_only_fields = ["created_by", "updated_by", "created_at", "updated_at"]

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
    genre_id      = serializers.IntegerField()    # new
    status_id     = serializers.IntegerField()  # new
    genre_name    = serializers.CharField(source='genre.display_name_en')
    status_name   = serializers.CharField(source='status.display_name_en')
    author_name     = serializers.CharField(source='author.name',    default=None)
    translator_name = serializers.CharField(source='translator.name', default=None)
    editions_count = serializers.IntegerField()
    stock          = serializers.IntegerField()
    latest_price   = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    latest_cost    = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    cover_design_url = serializers.SerializerMethodField()

    class Meta:
        model  = Product
        fields = [
            'id', 'title_ar', 'title_en', 'isbn',
            'genre_id','status_id',
            'genre_name', 'status_name',
            'author_name', 'translator_name',
            'editions_count', 'stock',
            'latest_price', 'latest_cost', "cover_design_url"
        ]
    def get_cover_design_url(self, obj):
        request = self.context.get("request")
        if obj.cover_design and hasattr(obj.cover_design, "url"):
            return request.build_absolute_uri(obj.cover_design.url)
        return None

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