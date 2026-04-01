from django.db import models


class Category(models.Model):
    id        = models.CharField(max_length=50, primary_key=True)
    name      = models.CharField(max_length=100)
    icon      = models.CharField(max_length=10, default='')
    image_url = models.URLField(blank=True, default='')
    class Meta:
        db_table = 'categories'
        verbose_name_plural = 'Categories'
    def __str__(self): return f"{self.icon} {self.name}"


class Product(models.Model):
    id               = models.CharField(max_length=20, primary_key=True)
    name             = models.CharField(max_length=200)
    description      = models.TextField(blank=True, default='')
    price            = models.FloatField()
    original_price   = models.FloatField()
    discount_percent = models.IntegerField(default=0)
    category         = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, db_column='category')
    brand            = models.CharField(max_length=100, blank=True, default='')
    rating           = models.FloatField(default=0.0)
    review_count     = models.IntegerField(default=0)
    sold_count       = models.IntegerField(default=0)
    stock            = models.IntegerField(default=0)
    image_url        = models.URLField(blank=True, default='')
    images           = models.JSONField(default=list, blank=True)
    tags             = models.JSONField(default=list, blank=True)
    is_featured      = models.BooleanField(default=False)
    free_delivery    = models.BooleanField(default=False)
    assured          = models.BooleanField(default=False)
    class Meta:
        db_table = 'products'
        ordering = ['-sold_count']
    def __str__(self): return self.name


class User(models.Model):
    id         = models.CharField(max_length=50, primary_key=True)
    name       = models.CharField(max_length=150)
    email      = models.EmailField(unique=True)
    phone      = models.CharField(max_length=15, blank=True, default='')
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField()
    class Meta:
        db_table = 'users'
        ordering = ['-created_at']
    def __str__(self): return f"{self.name} ({self.email})"


class Order(models.Model):
    STATUS_CHOICES = [
        ('Confirmed','Confirmed'),('Processing','Processing'),
        ('Shipped','Shipped'),('Delivered','Delivered'),('Cancelled','Cancelled'),
    ]
    id                = models.CharField(max_length=20, primary_key=True)
    user              = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, db_column='user_id')
    session_id        = models.CharField(max_length=100)
    items             = models.JSONField(default=list)
    address           = models.JSONField(default=dict)
    payment_method    = models.CharField(max_length=50, default='cod')
    payment_id        = models.CharField(max_length=100, blank=True, default='')
    payment_status    = models.CharField(max_length=50, default='pending')
    status            = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Confirmed')
    total_amount      = models.FloatField(default=0.0)
    created_at        = models.DateTimeField()
    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']
    def __str__(self): return f"Order #{self.id}"
    def customer(self): return self.address.get('name','Guest')
    def city(self): return self.address.get('city','')
