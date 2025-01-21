from kivy.app import App
from datetime import datetime
import os
from kivy.core.window import Window
import webbrowser  # Para abrir o PDF no navegador e facilitar a impressão
from database import inserir_produto, listar_produtos
from database import db
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from kivy.uix.textinput import TextInput
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.lang import Builder
import matplotlib.pyplot as plt
from io import BytesIO
from kivy.core.image import Image as CoreImage
from kivy.uix.image import Image


class LoginScreen(Screen):
    pass
class HomeScreen(Screen):
    pass

class ProdutosScreen(Screen):
    pass

class VendasScreen(Screen):
    pass

# Carregar os ficheiros KV
Builder.load_file("views/home.kv")
Builder.load_file("views/produtos.kv")
Builder.load_file("views/vendas.kv")
Builder.load_file("views/estatisticas.kv")

class EstatisticasScreen(Screen):
    def criar_grafico_vendas(self):
        def change_screen(self, screen_name):
            self.screen_manager.current = screen_name
            if screen_name == "vendas":
                self.carregar_produtos()
        try:
            # Buscar dados do MongoDB
            vendas = db.vendas.find()  # Certifique-se de que você tenha uma coleção "vendas"

            # Processar os dados
            dados_vendas = {}
            for venda in vendas:
                produto = venda["nome_produto"]
                quantidade = venda["quantidade"]
                if produto in dados_vendas:
                    dados_vendas[produto] += quantidade
                else:
                    dados_vendas[produto] = quantidade

            # Preparar os dados para o gráfico
            produtos = list(dados_vendas.keys())
            quantidades = list(dados_vendas.values())

            # Criar gráfico com Matplotlib
            plt.figure(figsize=(5, 4))
            plt.bar(produtos, quantidades, color='skyblue')
            plt.title("Vendas por Produto")
            plt.xlabel("Produtos")
            plt.ylabel("Quantidade Vendida")
            plt.xticks(rotation=45)

            # Salvar o gráfico em um buffer
            buf = BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            plt.close()

            # Exibir o gráfico no Kivy
            imagem = CoreImage(buf, ext="png")
            grafico_widget = Image(texture=imagem.texture)
            self.ids.grafico_layout.clear_widgets()
            self.ids.grafico_layout.add_widget(grafico_widget)

        except Exception as e:
            print(f"Erro ao criar gráfico: {e}")
            self.ids.grafico_layout.clear_widgets()
            self.ids.grafico_layout.add_widget(Label(text="Erro ao carregar o gráfico."))

class StockApp(App):
    def build(self):
            # Inicializar o ScreenManager
            self.screen_manager = ScreenManager()
            self.screen_manager.add_widget(LoginScreen(name="login"))
            self.screen_manager.add_widget(HomeScreen(name="home"))
            self.screen_manager.add_widget(ProdutosScreen(name="produtos"))
            self.screen_manager.add_widget(VendasScreen(name="vendas"))
            self.screen_manager.add_widget(EstatisticasScreen(name="estatisticas"))

            # Definir a tela inicial
            self.screen_manager.current = "login"
            return self.screen_manager

    def verificar_login(self, username, password):
        # Verificar credenciais
        if username == "admin" and password == "admin123":
            # Limpar mensagem de erro
            self.screen_manager.get_screen("login").ids.mensagem.text = ""
            # Redirecionar para a tela inicial (HomeScreen)
            self.screen_manager.current = "home"
        else:
            # Mostrar mensagem de erro
            self.screen_manager.get_screen("login").ids.mensagem.text = "Usuário ou senha incorretos!"

    def change_screen(self, screen_name):
        self.screen_manager.current = screen_name
        if screen_name == "vendas":
            self.carregar_produtos()

        # Carregar os dados na tela de estatísticas
        if screen_name == "estatisticas":
            estatisticas_screen = self.screen_manager.get_screen("estatisticas")
            estatisticas_screen.criar_grafico_vendas()


    def adicionar_produto(self, nome, preco, quantidade):
        if nome and preco and quantidade:
            try:
                inserir_produto(nome, float(preco), int(quantidade))
                self.mostrar_notificacao(f"Produto {nome} adicionado com sucesso!")
            except Exception as e:
                self.mostrar_notificacao(f"Erro ao adicionar produto: {e}")
        else:
            self.mostrar_notificacao("Preencha todos os campos antes de adicionar.")

    def carregar_produtos(self):
        print("Carregando produtos...")
        produtos = listar_produtos()
        if produtos:
            print(f"Produtos encontrados: {[produto['nome'] for produto in produtos]}")
            produtos_spinner = self.screen_manager.get_screen("vendas").ids.produtos_spinner
            produtos_spinner.values = [produto["nome"] for produto in produtos]
        else:
            print("Nenhum produto encontrado.")
            self.mostrar_notificacao("Nenhum produto encontrado no estoque.")

    def registar_venda(self, nome_produto, quantidade):
        from database import atualizar_stock
        if nome_produto and quantidade:
            produto = db.produtos.find_one({"nome": nome_produto})
            if produto and int(quantidade) <= produto["quantidade"]:
                # Atualizar o stock no MongoDB
                novo_stock = produto["quantidade"] - int(quantidade)
                atualizar_stock(nome_produto, novo_stock)

                # Calcular o total da venda
                preco_unitario = produto["preco"]
                total = preco_unitario * int(quantidade)

                # Salvar a venda na coleção `vendas`
                venda = {
                    "nome_produto": nome_produto,
                    "quantidade": int(quantidade),
                    "preco_unitario": preco_unitario,
                    "total": total,
                    "data_venda": datetime.now()
                }
                db.vendas.insert_one(venda)

                # Mostrar notificação de sucesso
                self.mostrar_notificacao(
                    f"Venda registada com sucesso!\n\n"
                    f"Produto: {nome_produto}\n"
                    f"Quantidade: {quantidade}\n"
                    f"Total: {total:.2f} €"
                )

                # Atualizar a interface
                self.carregar_produtos()
                self.atualizar_informacoes_produto(nome_produto)
            else:
                self.mostrar_notificacao("Quantidade insuficiente no stock.")
        else:
            self.mostrar_notificacao("Por favor, selecione um produto e insira uma quantidade válida.")


    def mostrar_notificacao(self, mensagem):
        from textwrap import wrap
        # Dividir a mensagem em linhas de no máximo 40 caracteres
        linhas = wrap(mensagem, width=40)
        texto_formatado = "\n".join(linhas)

        # Criar a notificação com o texto formatado
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        label = Label(text=texto_formatado, size_hint=(1, 0.8), halign="center", valign="middle")
        label.text_size = (300, None)  # Define largura máxima para o texto
        botao = Button(text="Fechar", size_hint=(1, 0.2))
        layout.add_widget(label)
        layout.add_widget(botao)

        popup = Popup(title="Notificação", content=layout, size_hint=(0.6, 0.4))
        botao.bind(on_press=popup.dismiss)
        popup.open()

    def atualizar_informacoes_produto(self, nome_produto):
        try:
            if nome_produto:
                produto = db.produtos.find_one({"nome": nome_produto})
                if produto:
                    # Atualizar os campos na interface
                    self.screen_manager.get_screen(
                        "vendas").ids.preco_produto.text = f"Preço Unitário: {produto['preco']:.2f} €"
                    self.screen_manager.get_screen(
                        "vendas").ids.stock_produto.text = f"Estoque Atual: {produto['quantidade']}"
                    self.screen_manager.get_screen("vendas").ids.preco_produto_grid.text = f"{produto['preco']:.2f}"
                    self.screen_manager.get_screen("vendas").ids.stock_produto_grid.text = f"{produto['quantidade']}"
                else:
                    # Produto não encontrado
                    self.screen_manager.get_screen("vendas").ids.preco_produto.text = "Preço Unitário: 0.00 €"
                    self.screen_manager.get_screen("vendas").ids.stock_produto.text = "Estoque Atual: 0"
                    self.screen_manager.get_screen("vendas").ids.preco_produto_grid.text = "0.00"
                    self.screen_manager.get_screen("vendas").ids.stock_produto_grid.text = "0"
            else:
                # Nenhum produto selecionado
                self.screen_manager.get_screen("vendas").ids.preco_produto.text = "Preço Unitário: 0.00 €"
                self.screen_manager.get_screen("vendas").ids.stock_produto.text = "Estoque Atual: 0"
                self.screen_manager.get_screen("vendas").ids.preco_produto_grid.text = "0.00"
                self.screen_manager.get_screen("vendas").ids.stock_produto_grid.text = "0"
        except Exception as e:
            print(f"Erro ao atualizar informações do produto: {e}")

    def emitir_fatura(self, nome_produto, quantidade, contribuinte, descricao):
        if nome_produto and quantidade:
            produto = db.produtos.find_one({"nome": nome_produto})
            if produto:
                # Calcular o total da venda
                total = produto["preco"] * int(quantidade)

                # Gerar o nome do arquivo
                nome_arquivo = f"fatura_{nome_produto}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
                caminho_arquivo = os.path.join(os.getcwd(), nome_arquivo)

                # Criar o PDF
                c = canvas.Canvas(caminho_arquivo, pagesize=A4)
                largura, altura = A4

                # Título centralizado
                c.setFont("Helvetica-Bold", 20)
                c.drawCentredString(largura / 2, altura - 50, "EMCO - Sistema de Gestão de Stocks")
                c.setFont("Helvetica", 12)
                c.drawCentredString(largura / 2, altura - 70, "Fatura Oficial")

                # Informações gerais
                c.setFont("Helvetica-Bold", 12)
                c.drawString(50, altura - 100, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
                c.drawString(50, altura - 120, f"Contribuinte: {contribuinte if contribuinte else 'N/A'}")
                c.drawString(50, altura - 140, f"Descrição: {descricao if descricao else 'N/A'}")

                # Dados da venda em tabela
                data = [
                    ["Produto", "Quantidade", "Preço Unitário (€)", "Total (€)"],
                    [nome_produto, quantidade, f"{produto['preco']:.2f}", f"{total:.2f}"]
                ]

                tabela = Table(data, colWidths=[200, 100, 150, 150])
                tabela.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.black),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ]))

                tabela.wrapOn(c, largura - 100, altura - 200)
                tabela.drawOn(c, 50, altura - 200)

                # Mensagem de agradecimento
                c.setFont("Helvetica-Bold", 12)
                c.drawString(50, 100, "Obrigado por usar o EMCO!")
                c.setFont("Helvetica", 10)
                c.drawString(50, 80, "Para mais informações, visite:")
                c.drawString(50, 60, "https://github.com/Keod0")

                # Salvar o PDF
                c.save()

                # Abrir o PDF no navegador para impressão
                webbrowser.open(caminho_arquivo)

                # Notificar o utilizador
                self.mostrar_notificacao(f"Fatura gerada e pronta para impressão: {nome_arquivo}")
            else:
                self.mostrar_notificacao("Produto não encontrado.")
        else:
            self.mostrar_notificacao("Por favor, selecione um produto e insira a quantidade.")

    def abrir_popup_fatura(self, nome_produto, quantidade):
        if not nome_produto or not quantidade:
            self.mostrar_notificacao("Por favor, selecione um produto e insira a quantidade.")
            return

        # Layout do pop-up
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)

        # Campos para contribuinte e descrição
        contribuinte_input = TextInput(hint_text="Contribuinte (opcional)", multiline=False)
        descricao_input = TextInput(hint_text="Descrição (opcional)", multiline=True)

        # Botões
        botoes_layout = BoxLayout(orientation='horizontal', spacing=10)
        botao_emitir = Button(text="Emitir Fatura", size_hint=(0.5, 1))
        botao_cancelar = Button(text="Cancelar", size_hint=(0.5, 1))

        # Adicionar botões ao layout
        botoes_layout.add_widget(botao_emitir)
        botoes_layout.add_widget(botao_cancelar)

        # Adicionar widgets ao layout
        layout.add_widget(Label(text="Informações para Fatura"))
        layout.add_widget(contribuinte_input)
        layout.add_widget(descricao_input)
        layout.add_widget(botoes_layout)

        # Criar o pop-up
        popup = Popup(title="Emitir Fatura", content=layout, size_hint=(0.8, 0.6))

        # Ações dos botões
        def emitir_fatura_callback(instance):
            contribuinte = contribuinte_input.text
            descricao = descricao_input.text
            popup.dismiss()
            self.emitir_fatura(nome_produto, quantidade, contribuinte, descricao)

        botao_emitir.bind(on_press=emitir_fatura_callback)
        botao_cancelar.bind(on_press=popup.dismiss)

        # Mostrar o pop-up
        popup.open()

def ajustar_tamanho_interface(instance, width, height):
    print(f"Janela redimensionada para: {width}x{height}")

Window.bind(on_resize=ajustar_tamanho_interface)


if __name__ == "__main__":
    StockApp().run()
