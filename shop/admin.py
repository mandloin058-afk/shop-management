from django.contrib import admin

from .models import Customer, Expense, Payment, Product, Purchase, Sale

for model in (Product, Purchase, Sale, Customer, Payment, Expense):
    admin.site.register(model)
