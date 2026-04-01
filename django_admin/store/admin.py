from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product, Order, User


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('icon','id','name','product_count')
    search_fields = ('name',)
    def product_count(self, obj):
        c = Product.objects.filter(category=obj).count()
        return format_html('<b style="color:#2874f0">{}</b>', c)
    product_count.short_description = 'Products'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display  = ('thumb','id','name','brand','category','price_disp','stock_disp','rating','is_featured','assured')
    list_filter   = ('category','is_featured','assured','free_delivery','brand')
    search_fields = ('name','brand','id')
    list_per_page = 20
    list_editable = ('is_featured','assured')
    fieldsets = (
        ('Basic', {'fields':('id','name','description','brand','category','tags')}),
        ('Pricing', {'fields':('price','original_price','discount_percent')}),
        ('Inventory', {'fields':('stock','sold_count','review_count','rating')}),
        ('Media', {'fields':('image_url','images')}),
        ('Flags', {'fields':('is_featured','free_delivery','assured')}),
    )
    readonly_fields = ('sold_count','review_count')
    def thumb(self, obj):
        if obj.image_url:
            return format_html('<img src="{}" style="width:48px;height:48px;object-fit:contain;background:#f5f5f5;border-radius:4px"/>',obj.image_url)
        return '-'
    thumb.short_description = ''
    def price_disp(self, obj):
        return format_html('<b>Rs.{:,}</b> <s style="color:#aaa;font-size:11px">Rs.{:,}</s>',int(obj.price),int(obj.original_price))
    price_disp.short_description = 'Price'
    def stock_disp(self, obj):
        color = '#388e3c' if obj.stock > 50 else '#ff9f00' if obj.stock > 0 else '#e23f40'
        return format_html('<b style="color:{}">{}</b>', color, obj.stock)
    stock_disp.short_description = 'Stock'


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display  = ('name','email','phone','is_active','order_count','created_at')
    search_fields = ('name','email','phone')
    list_filter   = ('is_active',)
    readonly_fields = ('id','created_at')
    def order_count(self, obj):
        c = Order.objects.filter(user=obj).count()
        return format_html('<b style="color:#2874f0">{}</b>', c)
    order_count.short_description = 'Orders'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display  = ('id','customer_name','city_name','item_count','total_disp','payment_disp','status','created_at')
    list_filter   = ('status','payment_method','payment_status')
    search_fields = ('id','session_id')
    list_per_page = 25
    list_editable = ('status',)
    readonly_fields = ('id','session_id','created_at','items_display','address_display')
    fieldsets = (
        ('Order', {'fields':('id','status','payment_method','payment_status','payment_id','total_amount','created_at')}),
        ('Customer', {'fields':('user','session_id','address_display')}),
        ('Items', {'fields':('items_display',)}),
    )
    def customer_name(self, obj): return obj.address.get('name','Guest')
    customer_name.short_description = 'Customer'
    def city_name(self, obj): return obj.address.get('city','-')
    city_name.short_description = 'City'
    def item_count(self, obj): return format_html('<b>{}</b>', len(obj.items))
    item_count.short_description = 'Items'
    def total_disp(self, obj): return format_html('<b>Rs.{:,.0f}</b>', obj.total_amount)
    total_disp.short_description = 'Total'
    def payment_disp(self, obj):
        colors = {'paid':'#388e3c','pending':'#e65100','failed':'#c62828'}
        return format_html('<span style="color:{};font-weight:700;text-transform:uppercase">{}</span>',
            colors.get(obj.payment_status,'#333'), obj.payment_method + ' / ' + obj.payment_status)
    payment_disp.short_description = 'Payment'
    def status_badge(self, obj):
        colors = {'Confirmed':'#388e3c','Processing':'#1565c0','Shipped':'#6a1b9a','Delivered':'#2e7d32','Cancelled':'#c62828'}
        return format_html('<span style="background:{};color:#fff;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:700">{}</span>',
            colors.get(obj.status,'#333'), obj.status)
    status_badge.short_description = 'Status'
    def address_display(self, obj):
        a = obj.address
        return format_html('<b>{}</b><br/>{}, {}, {} - {}<br/>Ph: {}',
            a.get('name',''), a.get('street',''), a.get('city',''),
            a.get('state',''), a.get('pincode',''), a.get('phone',''))
    address_display.short_description = 'Address'
    def items_display(self, obj):
        rows = ''.join([format_html('<tr><td style="padding:4px 8px">{}</td><td style="padding:4px 8px">x{}</td></tr>',
            i.get('product_id',''), i.get('quantity',1)) for i in obj.items])
        return format_html('<table style="font-size:13px"><tr style="background:#f5f5f5"><th style="padding:4px 8px">Product ID</th><th>Qty</th></tr>{}</table>', rows)
    items_display.short_description = 'Items'
