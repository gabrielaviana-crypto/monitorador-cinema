from playwright.sync_api import sync_playwright
import re
import unicodedata

def limpar_nome(texto):
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("utf-8")
    texto = re.sub(r"[^a-z0-9]+", "-", texto)
    return texto.strip("-")

estados = [
    "Acre",
    "Alagoas",
    "Amapá",
    "Amazonas",
    "Bahia",
    "Ceará",
    "Distrito Federal",
    "Espírito Santo",
    "Goiás",
    "Maranhão",
    "Mato Grosso",
    "Mato Grosso do Sul",
    "Minas Gerais",
    "Pará",
    "Paraíba",
    "Paraná",
    "Pernambuco",
    "Piauí",
    "Rio de Janeiro",
    "Rio Grande do Norte",
    "Rio Grande do Sul",
    "Rondônia",
    "Roraima",
    "Santa Catarina",
    "São Paulo",
    "Sergipe",
    "Tocantins"
]

def extrair_cidades_do_texto(texto):
    linhas = [l.strip() for l in texto.split("\n") if l.strip()]

    cidades = []
    coletando = False

    for linha in linhas:
        if linha == "Cidade":
            coletando = True
            continue

        if linha == "Trocar Cidade":
            coletando = False
            break

        if coletando:
            if linha not in ["Últimos Locais", "São Paulo"]:
                cidades.append(linha)

    return cidades

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    page.goto("https://www.ingresso.com/", timeout=90000)
    page.wait_for_timeout(5000)

    # abrir menu de cidade
    page.get_by_text("São Paulo", exact=True).click(timeout=10000)
    page.wait_for_timeout(3000)

    todas_cidades = []

    for estado in estados:
        try:
            print(f"Coletando cidades de {estado}...")

            page.locator("select").first.select_option(label=estado)
            page.wait_for_timeout(2000)

            texto = page.inner_text("body")
            cidades = extrair_cidades_do_texto(texto)

            for cidade in cidades:
                todas_cidades.append({
                    "estado": estado,
                    "nome": cidade,
                    "slug": limpar_nome(cidade)
                })

        except Exception as e:
            print(f"Erro ao coletar {estado}: {e}")

    browser.close()

print("\nCIDADES ENCONTRADAS:")
for item in todas_cidades:
    print(item)

print(f"\nTotal de cidades encontradas: {len(todas_cidades)}")