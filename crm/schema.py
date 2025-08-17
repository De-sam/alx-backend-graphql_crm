import graphene
from graphene_django import DjangoObjectType
from .models import Customer, Product, Order
from django.core.exceptions import ValidationError
import re

# ------------------
# GraphQL Types
# ------------------
class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer


class ProductType(DjangoObjectType):
    class Meta:
        model = Product


class OrderType(DjangoObjectType):
    class Meta:
        model = Order

# ------------------
# Mutations
# ------------------

class CreateCustomer(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        email = graphene.String(required=True)
        phone = graphene.String(required=False)

    customer = graphene.Field(CustomerType)
    message = graphene.String()

    def mutate(self, info, name, email, phone=None):
        # Email must be unique
        if Customer.objects.filter(email=email).exists():
            raise Exception("Email already exists")

        # Phone validation (optional)
        if phone and not re.match(r'^(\+?\d{10,15}|(\d{3}-\d{3}-\d{4}))$', phone):
            raise Exception("Invalid phone format")

        customer = Customer(name=name, email=email, phone=phone)
        customer.save()
        return CreateCustomer(customer=customer, message="Customer created successfully")


class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        customers = graphene.List(graphene.JSONString)

    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)

    def mutate(self, info, customers):
        created_customers = []
        errors = []

        for cust in customers:
            try:
                name = cust.get("name")
                email = cust.get("email")
                phone = cust.get("phone", None)

                if not name or not email:
                    raise Exception("Name and email required")

                if Customer.objects.filter(email=email).exists():
                    raise Exception(f"Email {email} already exists")

                if phone and not re.match(r'^(\+?\d{10,15}|(\d{3}-\d{3}-\d{4}))$', phone):
                    raise Exception(f"Invalid phone format for {email}")

                c = Customer(name=name, email=email, phone=phone)
                c.save()
                created_customers.append(c)
            except Exception as e:
                errors.append(str(e))

        return BulkCreateCustomers(customers=created_customers, errors=errors)


class CreateProduct(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        price = graphene.Float(required=True)
        stock = graphene.Int(required=False)

    product = graphene.Field(ProductType)

    def mutate(self, info, name, price, stock=0):
        if price <= 0:
            raise Exception("Price must be positive")
        if stock < 0:
            raise Exception("Stock cannot be negative")

        product = Product(name=name, price=price, stock=stock)
        product.save()
        return CreateProduct(product=product)


class CreateOrder(graphene.Mutation):
    class Arguments:
        customer_id = graphene.ID(required=True)
        product_ids = graphene.List(graphene.ID, required=True)

    order = graphene.Field(OrderType)

    def mutate(self, info, customer_id, product_ids):
        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            raise Exception("Invalid customer ID")

        if not product_ids:
            raise Exception("At least one product must be selected")

        products = Product.objects.filter(id__in=product_ids)
        if len(products) != len(product_ids):
            raise Exception("Some product IDs are invalid")

        order = Order(customer=customer)
        order.save()  # must save first
        order.products.set(products)
        order.total_amount = sum([p.price for p in products])
        order.save()

        return CreateOrder(order=order)

class Query(graphene.ObjectType):
    customers = graphene.List(CustomerType)
    products = graphene.List(ProductType)
    orders = graphene.List(OrderType)

    def resolve_customers(self, info):
        return Customer.objects.all()

    def resolve_products(self, info):
        return Product.objects.all()

    def resolve_orders(self, info):
        return Order.objects.all()


class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()
