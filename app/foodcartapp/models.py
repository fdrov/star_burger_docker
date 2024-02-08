from phonenumber_field.modelfields import PhoneNumberField

from django.core.validators import MinValueValidator

from django.db import models
from django.db.models import F, Q, Sum, Subquery, OuterRef
from django.utils import timezone

from location.models import Location


class Restaurant(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    address = models.CharField(
        'адрес',
        max_length=100,
    )
    contact_phone = models.CharField(
        'контактный телефон',
        max_length=50,
    )

    class Meta:
        verbose_name = 'ресторан'
        verbose_name_plural = 'рестораны'

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def available(self):
        products = (
            RestaurantMenuItem.objects
                .filter(availability=True)
                .values_list('product')
        )
        return self.filter(pk__in=products)


class ProductCategory(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'категории'

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    category = models.ForeignKey(
        ProductCategory,
        verbose_name='категория',
        related_name='products',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    price = models.DecimalField(
        'цена',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    image = models.ImageField(
        'картинка'
    )
    special_status = models.BooleanField(
        'спец.предложение',
        default=False,
        db_index=True,
    )
    description = models.TextField(
        'описание',
        max_length=500,
    )

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = 'товар'
        verbose_name_plural = 'товары'

    def __str__(self):
        return self.name


class RestaurantMenuItem(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        related_name='menu_items',
        verbose_name="ресторан",
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='menu_items',
        verbose_name='продукт',
    )
    availability = models.BooleanField(
        'в продаже',
        default=True,
        db_index=True,
    )

    class Meta:
        verbose_name = 'пункт меню ресторана'
        verbose_name_plural = 'пункты меню ресторана'
        unique_together = [
            ['restaurant', 'product']
        ]

    def __str__(self):
        return f"{self.restaurant.name} - {self.product.name}"


class OrderQuerySet(models.QuerySet):
    def annotate_order_cost(self):
        cost_of_product = F('ordered_items__fixed_price') * F('ordered_items__quantity')
        return self.annotate(order_cost=Sum(cost_of_product))

    def not_finished(self):
        return self.filter(~Q(status='FINISHED'))

    def restaurant_not_picked(self):
        return self.filter(restaurant_to_cook__isnull=True)

    def for_managers(self):
        return self.annotate_order_cost().not_finished().restaurant_not_picked()

    def fetch_restaurants_can_cook_order(self):
        all_ordered_products = OrderProduct.objects \
            .filter(order__status='NEW') \
            .values('order_id', 'product')

        rest_locations = Location.objects.filter(address=OuterRef('restaurant__address'))
        all_restaurants_menu = RestaurantMenuItem.objects \
            .filter(availability=True) \
            .annotate(longitude=Subquery(rest_locations.values('longitude')),
                      latitude=Subquery(rest_locations.values('latitude'))) \
            .select_related('product') \
            .select_related('restaurant')

        orders = self
        for order in orders:
            products_in_order = [p for p in all_ordered_products if p['order_id'] == order.id]
            restaurants_can_cook_order = []
            for product in products_in_order:
                restaurants_can_cook_product = set()
                for item in all_restaurants_menu:
                    if item.product_id == product['product']:
                        item.restaurant.longitude = item.longitude
                        item.restaurant.latitude = item.latitude
                        restaurants_can_cook_product.add(item.restaurant)
                restaurants_can_cook_order.append(restaurants_can_cook_product)
            order.restaurants_can_cook_order = set.intersection(*restaurants_can_cook_order)
        return orders


class Order(models.Model):

    class OrderStatuses(models.TextChoices):
        NEW = 'NEW', 'Необработанный'
        COOKING = 'COOKING', 'Готовится'
        IN_DELIVERY = 'IN_DELIVERY', 'Доставляется'
        FINISHED = 'FINISHED', 'Завершен'
        CANCELED = 'CANCELED', 'Отменен'

    class PaymentMethods(models.TextChoices):
        SPECIFY = 'SPECIFY', 'Уточнить'
        CASH = 'CASH', 'Наличные'
        CARD_ONLINE = 'CARD_ONLINE', 'Картой онлайн'
        CARD_DELIVERY = 'CARD_DELIVERY', 'Картой при получении'
        CRYPTO = 'CRYPTO', 'Криптовалютой'

    firstname = models.CharField(
        'Имя',
        max_length=250,
        db_index=True,
    )
    lastname = models.CharField(
        'Фамилия',
        max_length=250,
        db_index=True,
    )
    phonenumber = PhoneNumberField(
        'Номер телефона',
        db_index=True,
    )
    address = models.CharField(
        verbose_name='Адрес',
        max_length=250,
    )
    items = models.ManyToManyField(
        Product,
        verbose_name='Позиция в заказе',
        through='OrderProduct',
        related_name='orders',
    )
    status = models.CharField(
        'Статус заказа',
        max_length=150,
        choices=OrderStatuses.choices,
        default=OrderStatuses.NEW,
        db_index=True,
    )
    comment = models.TextField(
        'Комментарий',
        blank=True,
    )
    registered_at = models.DateTimeField(
        'Создан',
        default=timezone.now,
        db_index=True,
    )
    called_at = models.DateTimeField(
        'Позвонили',
        blank=True,
        null=True,
        db_index=True,
    )
    delivered_at = models.DateTimeField(
        'Доставлен',
        blank=True,
        null=True,
        db_index=True,
    )
    payment_method = models.CharField(
        'Способ оплаты',
        max_length=200,
        choices=PaymentMethods.choices,
        db_index=True,
        default=PaymentMethods.SPECIFY,
    )
    restaurant_to_cook = models.ForeignKey(
        Restaurant,
        verbose_name='Ресторан для готовки',
        on_delete=models.CASCADE,
        related_name='orders',
        blank=True,
        null=True,

    )

    objects = OrderQuerySet.as_manager()

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'

    def __str__(self):
        return f'{self.pk} {self.firstname}, {self.address}'


class OrderProduct(models.Model):
    product = models.ForeignKey(
        Product,
        verbose_name='Товар',
        on_delete=models.CASCADE,
        related_name='ordered_items',
    )
    order = models.ForeignKey(
        Order,
        verbose_name='Номер заказа',
        on_delete=models.CASCADE,
        related_name='ordered_items',
    )
    quantity = models.IntegerField(
        'Количество товара',
        validators=[MinValueValidator(1)],
    )
    fixed_price = models.DecimalField(
        'Цена на момент заказа',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]

    )

    class Meta:
        verbose_name = 'Позиции заказов'
        verbose_name_plural = 'Позиции заказов'

    def __str__(self):
        return f'#{self.order.pk} order: {self.product} × {self.quantity}'
