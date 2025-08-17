import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "alx_backend_graphql.settings")
django.setup()

from crm.models import Customer, Product

def seed():
    Customer.objects.create(name="Alice", email="alice@example.com", phone="+1234567890")
    Customer.objects.create(name="Bob", email="bob@example.com", phone="123-456-7890")

    Product.objects.create(name="Laptop", price=1000.00, stock=5)
    Product.objects.create(name="Phone", price=500.00, stock=10)

    print("Database seeded!")

if __name__ == "__main__":
    seed()
