from playwright.sync_api import sync_playwright
import pandas as pd
from datetime import datetime
import re
import unicodedata

def limpar_nome(texto):
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("utf-8")
    texto = re.sub(r"[^a-z0-9]+", "-", texto)
    return texto.strip("-")

def extrair_cidades_do_texto(texto):
    linhas = [l.strip() for l in texto.split("\n") if l.strip()]
    cidades = []
    coletando = False

    for linha in linhas:
        if linha == "Cidade":
            coletando = True
            continue

        if linha == "Trocar Cidade":
            break

        if coletando and linha not in ["Últimos Locais", "São Paulo"]:
            cidades.append(linha)

    return cidades

def coletar_cidades_ingresso(page, estados_escolhidos):
    estados = [
        "Acre", "Alagoas", "Amapá", "Amazonas", "Bahia", "Ceará",
        "Distrito Federal", "Espírito Santo", "Goiás", "Maranhão",
        "Mato Grosso", "Mato Grosso do Sul", "Minas Gerais", "Pará",
        "Paraíba", "Paraná", "Pernambuco", "Piauí", "Rio de Janeiro",
        "Rio Grande do Norte", "Rio Grande do Sul", "Rondônia", "Roraima",
        "Santa Catarina", "São Paulo", "Sergipe", "Tocantins"
    ]

    if estados_escolhidos.lower() != "todos":
        estados_usuario = [limpar_nome(e.strip()) for e in estados_escolhidos.split(",")]
        estados = [e for e in estados if limpar_nome(e) in estados_usuario]

    todas_cidades = []

    page.goto("https://www.ingresso.com/", timeout=90000)
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(1000)

    page.get_by_text("São Paulo", exact=True).click(timeout=10000)
    page.wait_for_timeout(800)

    for estado in estados:
        try:
            print(f"Coletando cidades de {estado}...")
            page.locator("select").first.select_option(label=estado)
            page.wait_for_timeout(400)

            texto = page.inner_text("body")
            cidades = extrair_cidades_do_texto(texto)

            for cidade in cidades:
                todas_cidades.append({
                    "estado": estado,
                    "nome": cidade,
                    "slug": limpar_nome(cidade)
                })

        except Exception as e:
            print(f"Erro ao coletar cidades de {estado}: {e}")

    return todas_cidades

def criar_cidades_especificas(estado, cidades_texto):
    cidades = []

    for cidade in cidades_texto.split(","):
        cidade = cidade.strip()

        if cidade:
            cidades.append({
                "estado": estado.strip(),
                "nome": cidade,
                "slug": limpar_nome(cidade)
            })

    return cidades

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
                    "cinemark", "kinoplex", "uci", "cinepolis",
                    "ponto cine", "moviecom"
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

todos_dados = []
sem_resultado = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    if modo == "1":
        cidades = coletar_cidades_ingresso(page, "todos")

    elif modo == "2":
        estados_escolhidos = input("Digite os estados separados por vírgula: ").strip()
        cidades = coletar_cidades_ingresso(page, estados_escolhidos)

    elif modo == "3":
        estado = input("Digite o estado: ").strip()
        cidades_texto = input("Digite as cidades separadas por vírgula: ").strip()
        cidades = criar_cidades_especificas(estado, cidades_texto)

    else:
        print("Modo inválido. Encerrando o programa.")
        browser.close()
        exit()

    print(f"\nTotal de cidades para análise: {len(cidades)}\n")

    for cidade in cidades:
        print(f"Analisando: {cidade['nome']} - {cidade['estado']}")

        url_ingresso = f"https://www.ingresso.com/filme/{slug_filme}?city={cidade['slug']}&partnership=home"

        try:
            page.goto(url_ingresso, timeout=90000)
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(700)

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