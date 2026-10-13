from django.urls import path

from . import views as v

urlpatterns = [
    path("", v.dashboard, name="dashboard"),

    path("products/", v.ProductList.as_view(), name="product_list"),
    path("products/add/", v.ProductCreate.as_view(), name="product_add"),
    path("products/<int:pk>/edit/", v.ProductUpdate.as_view(), name="product_edit"),
    path("products/<int:pk>/delete/", v.ProductDelete.as_view(), name="product_delete"),

    path("purchases/", v.PurchaseList.as_view(), name="purchase_list"),
    path("purchases/add/", v.PurchaseCreate.as_view(), name="purchase_add"),
    path("purchases/<int:pk>/delete/", v.PurchaseDelete.as_view(), name="purchase_delete"),

    path("sales/", v.SaleList.as_view(), name="sale_list"),
    path("sales/add/", v.SaleCreate.as_view(), name="sale_add"),
    path("sales/<int:pk>/invoice/", v.sale_invoice, name="sale_invoice"),
    path("sales/<int:pk>/delete/", v.SaleDelete.as_view(), name="sale_delete"),

    path("customers/", v.CustomerList.as_view(), name="customer_list"),
    path("customers/add/", v.CustomerCreate.as_view(), name="customer_add"),
    path("customers/<int:pk>/", v.customer_detail, name="customer_detail"),
    path("customers/<int:pk>/edit/", v.CustomerUpdate.as_view(), name="customer_edit"),

    path("expenses/", v.ExpenseList.as_view(), name="expense_list"),
    path("expenses/add/", v.ExpenseCreate.as_view(), name="expense_add"),
    path("expenses/<int:pk>/edit/", v.ExpenseUpdate.as_view(), name="expense_edit"),
    path("expenses/<int:pk>/delete/", v.ExpenseDelete.as_view(), name="expense_delete"),

    path("reports/daily/", v.report_daily, name="report_daily"),
    path("reports/monthly/", v.report_monthly, name="report_monthly"),
    path("reports/products/", v.report_products, name="report_products"),
    path("reports/stock/", v.report_stock, name="report_stock"),
]
