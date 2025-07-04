from django.shortcuts import render, redirect
from django.urls.base import reverse
from django.views.generic import View, TemplateView, CreateView, FormView, DetailView, ListView
from django.urls import reverse_lazy
from django.http import Http404
from django.shortcuts import get_object_or_404
from .forms import Checar_PedidoForm, ClienteRegistrarForm, ClienteEntrarForm
from .models import *
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout

class LojaMixin(object):
    def dispatch(self, request, *args, **kwargs):
        carro_id = request.session.get('carro_id')
        if carro_id:
            carro_obj = Carrinho.objects.filter(id=carro_id).first()
            if carro_obj and request.user.is_authenticated and hasattr(request.user, 'cliente'):
                carro_obj.cliente = request.user.cliente
                carro_obj.save()
        return super().dispatch(request, *args, **kwargs)

class HomeView(LojaMixin, TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_produtos = Produto.objects.all().order_by("-id")
        paginator = Paginator(all_produtos,4)
        page_number = self.request.GET.get('page')
        produto_list = paginator.get_page(page_number)
        context['produto_list'] = produto_list
        return context

class TodosProdutosView(LojaMixin, TemplateView):
    template_name = "todosprodutos.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['todoscategorias'] = Categoria.objects.all()
        return context

class ProdutoDetalheView(LojaMixin, TemplateView):
    template_name = "produtodetalhe.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        url_slug = self.kwargs['slug']
        produto = Produto.objects.get(slug=url_slug)
        produto.visualizacao += 1
        produto.save()
        context['produto'] = produto
        return context

class AddCarroView(LojaMixin, TemplateView):
    template_name = "addprocarro.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        produto_id = self.kwargs['pro_id']
        produto_obj = Produto.objects.get(id=produto_id)
        carro_id = self.request.session.get('carro_id', None)
        carro_obj = Carrinho.objects.filter(id=carro_id).first() if carro_id else None

        if carro_obj:
            produto_no_carrinho = carro_obj.carrinhoproduto_set.filter(produto=produto_obj)
            if produto_no_carrinho.exists():
                carrinhoproduto = produto_no_carrinho.last()
                carrinhoproduto.quantidade += 1
                carrinhoproduto.subtotal += produto_obj.venda
                carrinhoproduto.save()
                carro_obj.total += produto_obj.venda
                carro_obj.save()
            else:
                CarrinhoProduto.objects.create(
                    carrinho=carro_obj,
                    produto=produto_obj,
                    avaliacao=produto_obj.venda,
                    quantidade=1,
                    subtotal=produto_obj.venda
                )
                carro_obj.total += produto_obj.venda
                carro_obj.save()
        else:
            carro_obj = Carrinho.objects.create(total=0)
            self.request.session['carro_id'] = carro_obj.id
            CarrinhoProduto.objects.create(
                carrinho=carro_obj,
                produto=produto_obj,
                avaliacao=produto_obj.venda,
                quantidade=1,
                subtotal=produto_obj.venda
            )
            carro_obj.total += produto_obj.venda
            carro_obj.save()

        return context

class ManipularCarroView(LojaMixin, View):
    def get(self, request, *args, **kwargs):
        cp_id = self.kwargs['cp_id']
        acao = request.GET.get('acao')
        cp_obj = CarrinhoProduto.objects.get(id=cp_id)
        carro_obj = cp_obj.carrinho

        if acao == "inc":
            cp_obj.quantidade += 1
            cp_obj.subtotal += cp_obj.avaliacao
            cp_obj.save()
            carro_obj.total += cp_obj.avaliacao
            carro_obj.save()
        elif acao == "dcr":
            cp_obj.quantidade -= 1
            cp_obj.subtotal -= cp_obj.avaliacao
            cp_obj.save()
            carro_obj.total -= cp_obj.avaliacao
            carro_obj.save()
            if cp_obj.quantidade == 0:
                cp_obj.delete()
        elif acao == "rmv":
            carro_obj.total -= cp_obj.subtotal
            carro_obj.save()
            cp_obj.delete()

        return redirect("lojaapp:meucarro")

class LimparCarroView(LojaMixin, View):
    def get(self, request, *args, **kwargs):
        carro_id = request.session.get('carro_id', None)
        if carro_id:
            carrinho = Carrinho.objects.get(id=carro_id)
            carrinho.carrinhoproduto_set.all().delete()
            carrinho.total = 0
            carrinho.save()
        return redirect("lojaapp:meucarro")

# checkout view corrigida
class CheckoutView(LojaMixin, CreateView):
    template_name = "processar.html"
    form_class = Checar_PedidoForm
    success_url = reverse_lazy("lojaapp:home")

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_authenticated and hasattr(request.user, 'cliente')):
            return redirect("/entrar/?next=/checkout/")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        carro_id = self.request.session.get('carro_id', None)
        carrinho_obj = Carrinho.objects.filter(id=carro_id).first() if carro_id else None
        context['carrinho'] = carrinho_obj
        return context

    def form_valid(self, form):
        carrinho_id = self.request.session.get('carro_id')
        carrinho_obj = Carrinho.objects.filter(id=carrinho_id).first()
        if not carrinho_obj:
            return redirect("lojaapp:home")

        # Preenche dados do pedido
        form.instance.carrinho = carrinho_obj
        form.instance.subtotal = carrinho_obj.total
        form.instance.disconto = 0
        form.instance.total = carrinho_obj.total
        form.instance.pedido_status = "Pedido Recebido"

        # Salva o pedido
        pedido = form.save()

        # Limpa o carrinho da sessão
        if 'carro_id' in self.request.session:
            del self.request.session['carro_id']

        # Redireciona para pagamento
        pm = form.cleaned_data.get('pagamento_method')
        if pm == "Khalti":
            return redirect(reverse("lojaapp:pagamento") + "?order_id=" + str(pedido.id))
        
        return super().form_valid(form)


class PagamentoView(View):
    def get(self, request, *args, **kwargs):
        o_id = request.GET.get('order_id')
        try:
            pedido = get_object_or_404(Pedido_order, id=o_id)
        except Pedido_order.DoesNotExist:
            raise Http404("Pedido não encontrado.")
        
        context = {
            "pedido": pedido,
            "order_id": o_id,
        }
        return render(request, "pagamento.html", context)

class MeuCarroView(LojaMixin, TemplateView):
    template_name = "meucarro.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        carro_id = self.request.session.get('carro_id', None)
        carrinho = Carrinho.objects.get(id=carro_id) if carro_id else None
        context['carrinho'] = carrinho
        return context

class ClienteRegistrarView(CreateView):
    template_name = "clienteregistrar.html"
    form_class = ClienteRegistrarForm
    success_url = reverse_lazy("lojaapp:home")

    def form_valid(self, form):
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        email = form.cleaned_data.get('email')

        if User.objects.filter(username=username).exists():
            form.add_error('username', 'Este nome de usuário já está em uso.')
            return self.form_invalid(form)
        
        user = User.objects.create_user(username=username, email=email, password=password)
        form.instance.user = user

        login(self.request, user)
        return super().form_valid(form)

    def get_success_url(self):
        return self.request.GET.get("next", self.success_url)

class ClienteSairView(View):
    def get(self, request):
        logout(request)
        return redirect("lojaapp:home")

class ClienteEntrarView(FormView):
    template_name = "clienteentrar.html"
    form_class = ClienteEntrarForm
    success_url = reverse_lazy("lojaapp:home")

    def form_valid(self, form):
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        user = authenticate(username=username, password=password)
        if user is not None and Cliente.objects.filter(user=user).exists():
            login(self.request, user)
            return super().form_valid(form)
        else:
            return render(self.request, self.template_name, {
                "form": form,
                "error": "USUÁRIO E SENHA NÃO CORRESPONDEM!"
            })

    def get_success_url(self):
        return self.request.GET.get("next", self.success_url)

class SobreView(LojaMixin, TemplateView):
    template_name = "sobre.html"

class ContatoView(LojaMixin, TemplateView):
    template_name = "contato.html"

class ClientePerfilView(TemplateView):
    template_name = "clienteperfil.html"

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_authenticated and Cliente.objects.filter(user=request.user).exists()):
            return redirect("/entrar/?next=/perfil/")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cliente = self.request.user.cliente
        context['cliente'] = cliente
        pedidos = Pedido_order.objects.filter(carrinho__cliente=cliente).order_by('-id')
        context['pedidos'] = pedidos
        return context

class ClientePedidoDetalheView(DetailView):
    template_name = "clientepedidodetalhe.html"
    model = Pedido_order
    context_object_name = 'pedido_obj'

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_authenticated and Cliente.objects.filter(user=request.user).exists()):
            return redirect("/entrar/?next=/perfil/")

        pedido = self.get_object()
        if pedido.carrinho.cliente != request.user.cliente:
            return redirect("lojaapp:clienteperfil")

        return super().dispatch(request, *args, **kwargs)

class AdminLoginView(FormView):
    template_name = "admin_paginas/adminlogin.html"
    form_class = ClienteEntrarForm
    success_url = reverse_lazy("lojaapp:adminhome")

    def form_valid(self, form):
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        user = authenticate(username=username, password=password)
        if user is not None and Admin.objects.filter(user=user).exists():
            login(self.request, user)
            return super().form_valid(form)
        else:
            return render(self.request, self.template_name, {
                "form": form,
                "error": "USUÁRIO E SENHA NÃO CORRESPONDEM!"
            })

class AdminRequireMinix(object):
    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_authenticated and Admin.objects.filter(user=request.user).exists()):
            return redirect("/admin-login/")
        return super().dispatch(request, *args, **kwargs)

class AdminHomeView(AdminRequireMinix, TemplateView):
    template_name = "admin_paginas/adminhome.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['PedidosPendentes'] = Pedido_order.objects.filter(pedido_status="Pedido Recebido").order_by("-id")
        return context

class AdminPedidoDetalheView(AdminRequireMinix, DetailView):
    template_name = "admin_paginas/adminpedidodetalhe.html"
    model = Pedido_order
    context_object_name = 'pedido_obj'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["todosstatus"] = PEDIDO_STATUS
        return context

class AdminPedidoListaView(AdminRequireMinix, ListView):
    template_name = "admin_paginas/adminpedidolista.html"
    queryset = Pedido_order.objects.all().order_by("-id")
    context_object_name = 'todospedido'

class AdminPedidoMudarStatusView(AdminRequireMinix, View):
    def post(self, request, *args, **kwargs):
        pedido_id = self.kwargs['pk']
        pedido_obj = Pedido_order.objects.get(id=pedido_id)
        novo_status = request.POST.get("status")
        pedido_obj.pedido_status = novo_status
        pedido_obj.save()
        return redirect(reverse_lazy("lojaapp:adminpedidodetalhe", kwargs={'pk': pedido_id}))

class PesquisarView(TemplateView):
    template_name = "pesquisar.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        kw = self.request.GET.get("keyword", "")
        results = Produto.objects.filter(
            Q(titulo__icontains=kw) |
            Q(descricao__icontains=kw) |
            Q(return_devolucao__icontains=kw)
        )
        context["results"] = results
        return context
