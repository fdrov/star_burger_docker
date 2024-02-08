from geopy.distance import distance

from django import forms
from django.shortcuts import redirect, render
from django.views import View
from django.urls import reverse_lazy
from django.contrib.auth.decorators import user_passes_test

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views
from django.db.models import Subquery, OuterRef

from foodcartapp.models import Product, Restaurant, Order, OrderProduct, RestaurantMenuItem
from location.models import Location
from location.yandex_geocoder import fetch_coordinates

YANDEX_APIKEY = settings.YANDEX_APIKEY


class Login(forms.Form):
    username = forms.CharField(
        label='Логин', max_length=75, required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Укажите имя пользователя'
        })
    )
    password = forms.CharField(
        label='Пароль', max_length=75, required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите пароль'
        })
    )


class LoginView(View):
    def get(self, request, *args, **kwargs):
        form = Login()
        return render(request, "login.html", context={
            'form': form
        })

    def post(self, request):
        form = Login(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                if user.is_staff:  # FIXME replace with specific permission
                    return redirect("restaurateur:RestaurantView")
                return redirect("start_page")

        return render(request, "login.html", context={
            'form': form,
            'ivalid': True,
        })


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy('restaurateur:login')


def is_manager(user):
    return user.is_staff  # FIXME replace with specific permission


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_products(request):
    restaurants = list(Restaurant.objects.order_by('name'))
    products = list(Product.objects.prefetch_related('menu_items'))

    default_availability = {restaurant.id: False for restaurant in restaurants}
    products_with_restaurants = []
    for product in products:
        availability = {
            **default_availability,
            **{item.restaurant_id: item.availability for item in product.menu_items.all()},
        }
        orderer_availability = [availability[restaurant.id] for restaurant in restaurants]

        products_with_restaurants.append(
            (product, orderer_availability)
        )

    return render(request, template_name="products_list.html", context={
        'products_with_restaurants': products_with_restaurants,
        'restaurants': restaurants,
    })


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_restaurants(request):
    return render(request, template_name="restaurants_list.html", context={
        'restaurants': Restaurant.objects.all(),
    })


def get_or_fetch_coords(obj):
    if obj.latitude and obj.longitude:
        return obj.latitude, obj.longitude
    else:
        coords = fetch_coordinates(YANDEX_APIKEY, obj.address)
        if coords:
            Location.objects.get_or_create(
                address=obj.address,
                defaults={**dict(zip(['latitude', 'longitude'], coords))},
            )
            return coords


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_orders(request):
    sub = Location.objects.filter(address=OuterRef('address'))
    orders = Order.objects\
        .annotate(longitude=Subquery(sub.values('longitude')),
                  latitude=Subquery(sub.values('latitude')))\
        .for_managers()\
        .order_by('restaurant_to_cook', '-pk')\
        .fetch_restaurants_can_cook_order()

    for order in orders:
        order.coords = get_or_fetch_coords(order)

        order.restaurants_to_order = []
        if not order.restaurants_can_cook_order:
            continue
        for restaurant in order.restaurants_can_cook_order:
            restaurant.coords = get_or_fetch_coords(restaurant)
            distance_to_client = round(distance(order.coords, restaurant.coords).km, 3)
            if not distance_to_client:
                order.restaurants_to_order.append([0, 'Расстояние не определено'])
                continue
            order.restaurants_to_order.append([distance_to_client, f'{restaurant} - {distance_to_client}'])
        order.restaurants_to_order.sort(key=lambda distance: distance[0])

    context = {
        'orders': orders,
    }
    return render(request, template_name='order_items.html', context=context)
