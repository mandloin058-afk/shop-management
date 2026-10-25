from django.contrib import admin

from .models import AccountEntry, Customer, Expense, Payment, Product, Purchase, Sale

for model in (Product, Purchase, Sale, Customer, Payment, Expense, AccountEntry):
    admin.site.register(model)
