from django.db import models
from django.contrib.auth.models import User

class Admin(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    nome_completo = models.CharField(max_length=200)
    image = models.ImageField(upload_to="admins")
    telefone = models.CharField(max_length=20)


    def __str__(self):
        return self.user.username


class Cliente(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    nome_completo = models.CharField(max_length=200)
    email = models.EmailField()
    endereco = models.CharField(max_length=200, null=True, blank=True)
    data_on = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return self.nome_completo



class Categoria(models.Model):
    titulo = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)


    def __str__(self):
        return self.titulo
    
class Produto(models.Model):
    titulo = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    image = models.ImageField(upload_to="produtos")
    preco_mercado = models.PositiveIntegerField()
    venda = models.PositiveIntegerField()
    descricao = models.TextField()
    garantia = models.CharField(max_length=300, null=True, blank=True)
    return_devolucao = models.CharField(max_length=300, null=True, blank=True)
    visualizacao = models.PositiveIntegerField(default=0)
    

    def __str__(self):
        return self.titulo


class Carrinho(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True,blank=True)
    total = models.PositiveIntegerField(default=0)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "Carrinho:" + str(self.id) 
    

class CarrinhoProduto(models.Model):
    carrinho = models.ForeignKey(Carrinho, on_delete=models.CASCADE)
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    avaliacao = models.PositiveIntegerField()
    quantidade = models.PositiveIntegerField()
    subtotal = models.PositiveIntegerField()

    def __str__(self):
        return "CarrinhoProduto:" + str(self.id) + "CarrinhoProduto:" + str(self.produto.id)
    

PEDIDO_STATUS = (
    ('Pedido Recebido', 'Pedido Recebido'),
    ('Pedido Processamento', 'Pedido Processamento'),
    ('Pedido Caminho', 'Pedido Caminho'),
    ('Pedido Completado', 'Pedido Completado'),
    ('Pedido Cancelado', 'Pedido Cancelado'),
)


class Pedido_order(models.Model):
    carrinho = models.OneToOneField(Carrinho, on_delete=models.CASCADE)
    ordenando_por = models.CharField(max_length=200)
    endereco_envio = models.CharField(max_length=200)
    telefone = models.CharField(max_length=10)
    email = models.EmailField(null=True, blank=True)
    endereco_envio = models.CharField(max_length=200)
    subtotal = models.PositiveIntegerField()
    disconto = models.PositiveIntegerField()
    total = models.PositiveIntegerField()
    pedido_status = models.CharField(max_length=50, choices=PEDIDO_STATUS)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "Pedido:" + str(self.id)


    
