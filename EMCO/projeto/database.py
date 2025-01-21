from pymongo import MongoClient
import bcrypt

# Configuração do MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["gestao_stocks"]

def inserir_produto(nome, preco, quantidade):
    produto = {
        "nome": nome,
        "preco": preco,
        "quantidade": quantidade
    }
    db.produtos.insert_one(produto)
    print(f"Produto {nome} inserido na base de dados.")

def listar_produtos():
    try:
        produtos = list(db.produtos.find())  # Verifica se a coleção existe e tem dados
        return produtos
    except Exception as e:
        print(f"Erro ao listar produtos: {e}")
        return []

def atualizar_stock(nome_produto, nova_quantidade):
    resultado = db.produtos.update_one(
        {"nome": nome_produto},  # Critério de seleção
        {"$set": {"quantidade": nova_quantidade}}  # Atualização
    )
    if resultado.matched_count == 0:
        print(f"Produto '{nome_produto}' não encontrado.")
    elif resultado.modified_count == 1:
        print(f"Stock atualizado para {nova_quantidade}.")

def remover_produto(nome_produto):
    db.produtos.delete_one({"nome": nome_produto})


def cadastrar_usuario(username, password, role="funcionario"):
    # Hash da senha
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    usuario = {
        "username": username,
        "password": hashed_password,
        "role": role
    }

    # Inserir no MongoDB
    if db.usuarios.find_one({"username": username}):
        return False, "Usuário já existe!"

    db.usuarios.insert_one(usuario)
    return True, "Usuário cadastrado com sucesso!"


def autenticar_usuario(username, password):
    usuario = db.usuarios.find_one({"username": username})
    if not usuario:
        return False, "Usuário não encontrado!"

    if bcrypt.checkpw(password.encode('utf-8'), usuario["password"]):
        return True, usuario
    else:
        return False, "Senha incorreta!"