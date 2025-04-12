from django.urls import path
from . import views

urlpatterns = [

    ### ===== Project =====
    path("projects/", views.ProjectListCreateView.as_view(), name="project-list-create"),
    path("projects/<int:pk>/", views.ProjectUpdateView.as_view(), name="project-update"),
    path("projects/<int:pk>/delete/", views.ProjectDeleteView.as_view(), name="project-delete"),

    ### ===== Product =====
    path("products/", views.ProductListCreateView.as_view(), name="product-list-create"),
    path("products/<int:pk>/", views.ProductUpdateView.as_view(), name="product-update"),
    path("products/<int:pk>/delete/", views.ProductDeleteView.as_view(), name="product-delete"),

    ### ===== Warehouse =====
    path("warehouses/", views.WarehouseListCreateView.as_view(), name="warehouse-list-create"),
    path("warehouses/<int:pk>/", views.WarehouseUpdateView.as_view(), name="warehouse-update"),
    path("warehouses/<int:pk>/delete/", views.WarehouseDeleteView.as_view(), name="warehouse-delete"),

    ### ===== Inventory =====
    path("inventory/", views.InventoryListCreateView.as_view(), name="inventory-list-create"),
    path("inventory/<int:pk>/", views.InventoryUpdateView.as_view(), name="inventory-update"),
    path("inventory/<int:pk>/delete/", views.InventoryDeleteView.as_view(), name="inventory-delete"),
    path("inventory/product/<int:product_id>/update/", views.InventoryUpdateByProductView.as_view(), name="inventory-update-by-product"),
    path("inventory/product/<int:product_id>/delete/", views.InventoryDeleteByProductView.as_view(), name="inventory-delete-by-product"),

    ### ===== Transfer =====
    path("transfers/", views.TransferListCreateView.as_view(), name="transfer-list-create"),
    path("transfers/<int:pk>/", views.TransferUpdateView.as_view(), name="transfer-update"),
    path("transfers/<int:pk>/delete/", views.TransferDeleteView.as_view(), name="transfer-delete"),

    ### ===== Authors =====
    path("authors/", views.AuthorListCreateView.as_view(), name="author-list-create"),
    path("authors/<int:pk>/", views.AuthorUpdateView.as_view(), name="author-update"),
    path("authors/<int:pk>/delete/", views.AuthorDeleteView.as_view(), name="author-delete"),

    ### ===== Translators =====
    path("translators/", views.TranslatorListCreateView.as_view(), name="translator-list-create"),
    path("translators/<int:pk>/", views.TranslatorUpdateView.as_view(), name="translator-update"),
    path("translators/<int:pk>/delete/", views.TranslatorDeleteView.as_view(), name="translator-delete"),

    ### ===== Rights Owners =====
    path("rights-owners/", views.RightsOwnerListCreateView.as_view(), name="rights-owner-list-create"),
    path("rights-owners/<int:pk>/", views.RightsOwnerUpdateView.as_view(), name="rights-owner-update"),
    path("rights-owners/<int:pk>/delete/", views.RightsOwnerDeleteView.as_view(), name="rights-owner-delete"),

    ### ===== Reviewers =====
    path("reviewers/", views.ReviewerListCreateView.as_view(), name="reviewer-list-create"),
    path("reviewers/<int:pk>/", views.ReviewerUpdateView.as_view(), name="reviewer-update"),
    path("reviewers/<int:pk>/delete/", views.ReviewerDeleteView.as_view(), name="reviewer-delete"),

     ### ===== Stakeholder =====
    path('stakeholders/', views.StakeholderListCreateView.as_view(), name='stakeholder-list-create'),
    path('stakeholders/<int:pk>/', views.StakeholderUpdateView.as_view(), name='stakeholder-update'),
    path('stakeholders/<int:pk>/delete/', views.StakeholderDeleteView.as_view(), name='stakeholder-delete'),

    ### ===== Contracts =====
    path('contracts/', views.ContractListCreateView.as_view(), name='contract-list-create'),
    path('contracts/<int:pk>/', views.ContractUpdateView.as_view(), name='contract-update'),
    path('contracts/<int:pk>/delete/', views.ContractDeleteView.as_view(), name='contract-delete'),

    ### ===== Print Tasks =====
    path("print-tasks/", views.PrintTaskListCreateView.as_view(), name="print-task-list-create"),
    path("print-tasks/<int:pk>/", views.PrintTaskUpdateView.as_view(), name="print-task-update"),
    path("print-tasks/<int:pk>/delete/", views.PrintTaskDeleteView.as_view(), name="print-task-delete"),
]
