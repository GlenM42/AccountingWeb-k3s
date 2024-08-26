"""
URL configuration for AccountingWeb project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from .views import home_view, balance_sheet_view, transaction_history_view, new_transaction_view, income_statement_view
from django.contrib.auth.views import LoginView, LogoutView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),

    path('', home_view, name='home'),
    path('balance_sheet/', balance_sheet_view, name='balance_sheet'),
    path('transaction_history/', transaction_history_view, name='transaction_history'),
    path('new_transaction/', new_transaction_view, name='new_transaction'),
    path('income_statement/', income_statement_view, name='income_statement'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
