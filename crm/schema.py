import re
import graphene
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from .models import Customer, Product, Order
from .filters import CustomerFilter, ProductFilter, OrderFilter
from django.db import transaction
from django.utils import timezone


# ========== Types with Filters ==========
class CustomerNode(DjangoObjectType):
    class Meta:
        model = Customer
        filterset_class = CustomerFilter
        interfaces = (graphene.relay.Node,)
        fields = ("id", "name", "email", "phone", "created_at")


class ProductNode(DjangoObjectType):
    class Meta:
        model = Product
        filterset_class = ProductFilter
        interfaces = (graphene.relay.Node,)
        fields = ("id", "name", "price", "stock")


class OrderNode(DjangoObjectType):
    class Meta:
        model = Order
        filterset_class = OrderFilter
        interfaces = (graphene.relay.Node,)
        fields = ("id", "customer", "products", "total_amount", "order_date")


# ========== Mutations ==========
class CreateCustomer(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        email = graphene.String(required=True)
        phone = graphene.String()

    customer = graphene.Field(CustomerNode)
    message = graphene.String()

    def mutate(self, info, name, email, phone=None):
        if Customer.objects.filter(email=email).exists():
            raise Exception("Email already exists")

        if phone and not re.match(r'^(\+?\d{7,15}|\d{3}-\d{3}-\d{4})$', phone):
            raise Exception("Invalid phone format")

        customer = Customer.objects.create(name=name, email=email, phone=phone)
        return CreateCustomer(customer=customer, message="Customer created successfully")


class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        customers = graphene.List(
            graphene.NonNull(graphene.InputObjectType(
                "CustomerInput",
                name=graphene.String(required=True),
                email=graphene.String(required=True),
                phone=graphene.String()
            ))
        )

    customers = graphene.List(CustomerNode)
    errors = graphene.List(graphene.String)

    @transaction.atomic
    def mutate(self, info, customers):
        created = []
        errors = []

        for c in customers:
            try:
                if Customer.objects.filter(email=c.email).exists():
                    errors.append(f"Email {c.email} already exists")
                    continue
                cust = Customer.objects.create(name=c.name, email=c.email, phone=c.phone)
                created.append(cust)
            except Exception as e:
                errors.append(str(e))

        return BulkCreateCustomers(customers=created, errors=errors)


class CreateProduct(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        price = graphene.Float(required=True)
        stock = graphene.Int()

    product = graphene.Field(ProductNode)

    def mutate(self, info, name, price, stock=0):
        if price <= 0:
            raise Exception("Price must be positive")
        if stock < 0:
            raise Exception("Stock cannot be negative")

        product = Product.objects.create(name=name, price=price, stock=stock)
        return CreateProduct(product=product)


class CreateOrder(graphene.Mutation):
    class Arguments:
        customer_id = graphene.ID(required=True)
        product_ids = graphene.List(graphene.ID, required=True)
        order_date = graphene.DateTime()

    order = graphene.Field(OrderNode)

    def mutate(self, info, customer_id, product_ids, order_date=None):
        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            raise Exception("Invalid customer ID")

        if not product_ids:
            raise Exception("At least one product must be selected")

        products = Product.objects.filter(id__in=product_ids)
        if not products.exists():
            raise Exception("Invalid product IDs")

        order = Order.objects.create(
            customer=customer,
            order_date=order_date or timezone.now()
        )
        order.products.set(products)
        order.calculate_total()
        order.save()

        return CreateOrder(order=order)


# ========== Root Query ==========
class Query(graphene.ObjectType):
    customer = graphene.relay.Node.Field(CustomerNode)
    all_customers = DjangoFilterConnectionField(CustomerNode, order_by=graphene.List(of_type=graphene.String))

    product = graphene.relay.Node.Field(ProductNode)
    all_products = DjangoFilterConnectionField(ProductNode, order_by=graphene.List(of_type=graphene.String))

    order = graphene.relay.Node.Field(OrderNode)
    all_orders = DjangoFilterConnectionField(OrderNode, order_by=graphene.List(of_type=graphene.String))

    def resolve_all_customers(self, info, order_by=None, **kwargs):
        qs = Customer.objects.all()
        if order_by:
            qs = qs.order_by(*order_by)
        return qs

    def resolve_all_products(self, info, order_by=None, **kwargs):
        qs = Product.objects.all()
        if order_by:
            qs = qs.order_by(*order_by)
        return qs

    def resolve_all_orders(self, info, order_by=None, **kwargs):
        qs = Order.objects.all()
        if order_by:
            qs = qs.order_by(*order_by)
        return qs


# ========== Root Mutation ==========
class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
