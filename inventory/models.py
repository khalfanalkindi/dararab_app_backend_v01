from django.db import models
from django.conf import settings
from common.models import ListItem
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


User = get_user_model()

# 🔁 Mixin for audit fields
class AuditModel(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created_by"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_updated_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

# Author, Translator, RightsOwner, Reviewer 
class Author(AuditModel):
    name = models.CharField(max_length=255)
    bio = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Translator(AuditModel):
    name = models.CharField(max_length=255)
    bio = models.TextField(blank=True)

    def __str__(self):
        return self.name

class RightsOwner(AuditModel):
    name = models.CharField(max_length=255)
    contact_info = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Reviewer(AuditModel):
    name = models.CharField(max_length=255)
    bio = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Stakeholder(AuditModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    contact_person = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name

# Project
class Project(AuditModel):
    title_ar = models.CharField(max_length=255)
    title_original = models.CharField(max_length=255, null=True, blank=True)
    manuscript = models.TextField(blank=True)
    description = models.TextField(blank=True)
    approval_status = models.BooleanField(default=False)
    progress_status = models.ForeignKey(ListItem, on_delete=models.SET_NULL, null=True, blank=True, related_name='projects_progress')
    status = models.ForeignKey(ListItem, on_delete=models.SET_NULL, null=True, related_name='projects_status')
    type = models.ForeignKey(ListItem, on_delete=models.SET_NULL, null=True, related_name='projects_type')
    author = models.ForeignKey(Author, on_delete=models.SET_NULL, null=True, blank=True)
    translator = models.ForeignKey(Translator, on_delete=models.SET_NULL, null=True, blank=True)
    rights_owner = models.ForeignKey(RightsOwner, on_delete=models.SET_NULL, null=True, blank=True)
    reviewer = models.ForeignKey(Reviewer, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.title_ar

# 📦 Product
class Product(AuditModel):
    project= models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True)
    isbn= models.CharField(max_length=100)
    title_ar= models.CharField(max_length=255, verbose_name="Book Title (Arabic)")
    title_en= models.CharField(max_length=255, verbose_name="Book Title (English)")
    cover_design= models.ImageField(upload_to='book_covers/', null=True, blank=True)
    genre= models.ForeignKey(ListItem, on_delete=models.SET_NULL, null=True, related_name='genre')
    status= models.ForeignKey(ListItem, on_delete=models.SET_NULL, null=True, related_name='product_status')
    author= models.ForeignKey(Author,      on_delete=models.SET_NULL, null=True, blank=True)
    translator= models.ForeignKey(Translator, on_delete=models.SET_NULL, null=True, blank=True)
    rights_owner= models.ForeignKey(RightsOwner,on_delete=models.SET_NULL, null=True, blank=True)
    reviewer= models.ForeignKey(Reviewer,   on_delete=models.SET_NULL, null=True, blank=True)

    is_direct_product = models.BooleanField(default=False)

    def __str__(self):
        return self.title_ar or self.isbn
# PrintRun
class PrintRun(AuditModel):
    product= models.ForeignKey(Product, on_delete=models.CASCADE, related_name='print_runs', db_index=True)
    edition_number= models.PositiveIntegerField(verbose_name="Edition Number")
    print_cost= models.DecimalField(max_digits=10, decimal_places=2)
    price= models.DecimalField(max_digits=10, decimal_places=2)
    status= models.ForeignKey(ListItem, on_delete=models.SET_NULL, null=True, related_name='printrun_status')
    published_at= models.DateField()
    notes= models.TextField(blank=True)

    class Meta:
        ordering = ['product', 'edition_number']
        indexes = [
            models.Index(fields=['product','edition_number']),  # composite index
        ]

    def __str__(self):
        return f"{self.product} — Edition {self.edition_number}"

# 🏬 Warehouse
class Warehouse(AuditModel):
    name_en = models.CharField(max_length=255)
    name_ar = models.CharField(max_length=255)
    type = models.ForeignKey(ListItem, on_delete=models.SET_NULL, null=True, related_name='warehouse_type')
    location = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name_ar} / {self.name_en}"

# 📊 Inventory
class Inventory(AuditModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, db_index=True,)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    quantity = models.IntegerField()

    class Meta:
        unique_together = ('product', 'warehouse')
        verbose_name_plural = "Inventories"
        indexes = [
            models.Index(fields=['product']),   # explicit index
        ]

    def __str__(self):
        return f"{self.product} @ {self.warehouse}"

# 🔄 Transfer
class Transfer(AuditModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    from_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='transfer_from')
    to_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='transfer_to')
    quantity = models.IntegerField()
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2)
    transfer_date = models.DateTimeField()

    def __str__(self):
        return f"Transfer {self.quantity} of {self.product} from {self.from_warehouse} to {self.to_warehouse}"

# Contract

class Contract(AuditModel):
    title = models.CharField(max_length=255, null=True, blank=True)
    project = models.ForeignKey('Project', on_delete=models.CASCADE)
    contract_type = models.ForeignKey(ListItem, on_delete=models.SET_NULL, null=True, related_name='contract_type')
    
    # Generic Foreign Key for contracted party
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    contracted_party = GenericForeignKey('content_type', 'object_id')
    
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    fixed_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    free_copies = models.IntegerField(null=True, blank=True)
    contract_duration = models.IntegerField(help_text="The contract in months", null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    signed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='signed_contracts')
    status = models.ForeignKey(ListItem, on_delete=models.SET_NULL, null=True, related_name='contract_status')
    payment_schedule = models.TextField(blank=True)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.title or self.project} - {self.contract_type}"

    
class PrintTask(AuditModel):
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    task_type = models.ForeignKey(ListItem, on_delete=models.SET_NULL, null=True, related_name='print_tasks_type')  # مثل: طباعة، تغليف، تجهيز
    status = models.ForeignKey(ListItem, on_delete=models.SET_NULL, null=True, related_name='print_tasks_status')  # مثل: قيد التنفيذ، مكتمل
    due_date = models.DateField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.task_type} - {self.product}"
