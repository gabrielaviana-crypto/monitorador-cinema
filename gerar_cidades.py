from playwright.sync_api import sync_playwright
import pandas as pd
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

        if coletando and linha not in ["Últimos Locais"]:
            cidades.append(linha)

    return cidades

estados = [
    "Acre", "Alagoas", "Amapá", "Amazonas", "Bahia", "Ceará",
    "Distrito Federal", "Espírito Santo", "Goiás", "Maranhão",
    "Mato Grosso", "Mato Grosso do Sul", "Minas Gerais", "Pará",
    "Paraíba", "Paraná", "Pernambuco", "Piauí", "Rio de Janeiro",
    "Rio Grande do Norte", "Rio Grande do Sul", "Rondônia", "Roraima",
    "Santa Catarina", "São Paulo", "Sergipe", "Tocantins"
]

todas_cidades = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.goto("https://www.ingresso.com/", timeout=90000)
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(1000)

    page.get_by_text("São Paulo", exact=True).click(timeout=10000)
    page.wait_for_timeout(800)

    for estado in estados:
        print(f"Coletando cidades de {estado}...")

        page.locator("select").first.select_option(label=estado)
        page.wait_for_timeout(500)

        texto = page.inner_text("body")
        cidades = extrair_cidades_do_texto(texto)

        for cidade in cidades:
            todas_cidades.append({
                "estado": estado,
                "cidade": cidade,
                "slug": limpar_nome(cidade)
            })

    browser.close()

df = pd.DataFrame(todas_cidades)
df.to_csv("cidades.csv", index=False, encoding="utf-8-sig")

print(f"Arquivo cidades.csv criado com {len(df)} cidades.")