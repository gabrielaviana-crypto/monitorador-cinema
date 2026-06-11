from playwright.sync_api import sync_playwright
import pandas as pd
from datetime import datetime
import re
import unicodedata
import os

def limpar_nome(texto):
    texto = str(texto).lower().strip()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("utf-8")
    texto = re.sub(r"[^a-z0-9]+", "-", texto)
    return texto.strip("-")

def carregar_cidades_csv():
    if not os.path.exists("cidades.csv"):
        print("ERRO: O arquivo cidades.csv não foi encontrado.")
        print("Coloque o cidades.csv na mesma pasta do monitoramento.py.")
        exit()

    df = pd.read_csv("cidades.csv")

    cidades = []

    for _, row in df.iterrows():
        cidades.append({
            "estado": str(row["estado"]),
            "nome": str(row["cidade"]),
            "slug": str(row["slug"])
        })

    return cidades

def filtrar_estados(cidades, estados_texto):
    estados_usuario = [
        limpar_nome(e.strip())
        for e in estados_texto.split(",")
        if e.strip()
    ]

    return [
        c for c in cidades
        if limpar_nome(c["estado"]) in estados_usuario
    ]

def filtrar_cidades(cidades, estado_texto, cidades_texto):
    cidades_usuario = [
        limpar_nome(c.strip())
        for c in cidades_texto.split(",")
        if c.strip()
    ]

    return [
        c for c in cidades
        if limpar_nome(c["estado"]) == limpar_nome(estado_texto)
        and limpar_nome(c["nome"]) in cidades_usuario
    ]

def extrair_horarios(texto, filme, estado, cidade, fonte, site):
    linhas = [l.strip() for l in texto.split("\n") if l.strip()]
    resultados = []

    for i, linha in enumerate(linhas):
        if re.match(r"^\d{2}:\d{2}$", linha):
            horario = linha
            cinema = ""

            for j in range(i - 1, max(i - 15, 0), -1):
                linha_teste = linhas[j].lower()

                if any(p in linha_teste for p in [
                    "cinemark",
                    "kinoplex",
                    "uci",
                    "cinepolis",
                    "ponto cine",
                    "moviecom"
                ]):
                    cinema = linhas[j]
                    break

            if cinema:
                resultados.append({
                    "Filme": filme,
                    "Estado": estado,
                    "Cidade": cidade,
                    "Cinema": cinema,
                    "Horário": horario,
                    "Site": site,
                    "Fonte": fonte,
                    "Última atualização": datetime.now().strftime("%d/%m/%Y %H:%M")
                })

    return resultados

print("\n=== Monitoramento de Sessões - Ingresso.com ===")
print("1 - Brasil inteiro")
print("2 - Estados selecionados")
print("3 - Cidades específicas")

modo = input("Escolha o modo de busca (1, 2 ou 3): ").strip()
filme = input("Digite o nome do filme: ").strip()

slug_filme = limpar_nome(filme)
print(f"\nSlug gerado automaticamente: {slug_filme}\n")

todas_cidades = carregar_cidades_csv()

if modo == "1":
    cidades = todas_cidades

elif modo == "2":
    estados_escolhidos = input("Digite os estados separados por vírgula: ").strip()
    cidades = filtrar_estados(todas_cidades, estados_escolhidos)

elif modo == "3":
    estado = input("Digite o estado: ").strip()
    cidades_texto = input("Digite as cidades separadas por vírgula: ").strip()
    cidades = filtrar_cidades(todas_cidades, estado, cidades_texto)

else:
    print("Modo inválido. Encerrando o programa.")
    exit()

if len(cidades) == 0:
    print("\nNenhuma cidade encontrada para os filtros informados.")
    print("Verifique se escreveu o estado/cidade corretamente.")
    exit()

print(f"\nTotal de cidades para análise: {len(cidades)}\n")

todos_dados = []
sem_resultado = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.route(
        "*/",
        lambda route: route.abort()
        if route.request.resource_type in ["image", "font", "media"]
        else route.continue_()
    )

    for cidade in cidades:
        print(f"Analisando: {cidade['nome']} - {cidade['estado']}")

        url_ingresso = f"https://www.ingresso.com/filme/{slug_filme}?city={cidade['slug']}&partnership=home"

        try:
            page.goto(url_ingresso, timeout=90000, wait_until="domcontentloaded")

            try:
                page.wait_for_selector("text=/\\d{2}:\\d{2}/", timeout=1800)
            except:
                pass

            texto = page.inner_text("body")

            dados_ingresso = extrair_horarios(
                texto,
                filme,
                cidade["estado"],
                cidade["nome"],
                url_ingresso,
                "Ingresso.com"
            )

            if dados_ingresso:
                todos_dados.extend(dados_ingresso)
            else:
                sem_resultado.append({
                    "Filme": filme,
                    "Estado": cidade["estado"],
                    "Cidade": cidade["nome"],
                    "Site": "Ingresso.com",
                    "Status": "Nenhuma sessão encontrada"
                })

        except Exception as e:
            sem_resultado.append({
                "Filme": filme,
                "Estado": cidade["estado"],
                "Cidade": cidade["nome"],
                "Site": "Ingresso.com",
                "Status": f"Erro: {e}"
            })

    browser.close()

df_sessoes = pd.DataFrame(todos_dados)
df_sem_resultado = pd.DataFrame(sem_resultado)

nome_arquivo = f"sessoes_{slug_filme}.xlsx"

with pd.ExcelWriter(nome_arquivo, engine="openpyxl") as writer:
    df_sessoes.to_excel(writer, sheet_name="Sessoes Encontradas", index=False)
    df_sem_resultado.to_excel(writer, sheet_name="Sem Resultado", index=False)

print("\nResumo:")
print(f"Sessões encontradas: {len(df_sessoes)}")
print(f"Cidades sem resultado/erro: {len(df_sem_resultado)}")
print(f"Arquivo criado: {nome_arquivo}")