# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Cart(models.Model):
    user_id = models.BigIntegerField()
    product = models.ForeignKey('Products', models.DO_NOTHING, blank=True, null=True)
    quantity = models.IntegerField()

    class Meta:
        db_table = 'cart'
        unique_together = (('user_id', 'product'),)


class Categories(models.Model):
    name = models.TextField()

    class Meta:
        db_table = 'categories'


class Faq(models.Model):
    question = models.TextField(unique=True)
    answer = models.TextField()

    class Meta:
        db_table = 'faq'


class OrderItems(models.Model):
    order = models.ForeignKey('Orders', models.DO_NOTHING, blank=True, null=True)
    product = models.ForeignKey('Products', models.DO_NOTHING, blank=True, null=True)
    quantity = models.IntegerField()

    class Meta:
        db_table = 'order_items'


class Orders(models.Model):
    order_id = models.AutoField(primary_key=True)
    user_id = models.BigIntegerField()
    address = models.TextField()
    phone = models.TextField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'orders'


class Products(models.Model):
    subcategory = models.ForeignKey('Subcategories', models.DO_NOTHING, blank=True, null=True)
    name = models.TextField()
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    image_url = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'products'


class Subcategories(models.Model):
    category = models.ForeignKey(Categories, models.DO_NOTHING, blank=True, null=True)
    name = models.TextField()

    class Meta:
        db_table = 'subcategories'


class Users(models.Model):
    user_id = models.BigIntegerField(primary_key=True)
    username = models.TextField(blank=True, null=True)
    full_name = models.TextField(blank=True, null=True)
    registered_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'users'
