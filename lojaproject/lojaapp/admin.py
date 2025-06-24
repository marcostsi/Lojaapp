from django.contrib import admin
from.models import *

admin.site.register([Admin, Cliente,Categoria,Produto,Carrinho,CarrinhoProduto,Pedido_order])
