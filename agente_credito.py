import os
import base64
import feedparser
import requests
import time
from google import genai
from dotenv import load_dotenv
from datetime import datetime

# 1. Carrega as configurações
load_dotenv()

client = genai.Client()

# Lista de portais (Feeds RSS oficiais de Economia e Finanças)
FONTES_NOTICIAS = [
    "https://valor.globo.com/rss/financas/",           # Valor Econômico
    "https://www.infomoney.com.br/onde-investir/feed/", # InfoMoney
    "https://g1.globo.com/rss/g1/economia/",            # G1 Globo Economia
    "https://economia.estadao.com.br/rss/",            # Estadão Economia
    "https://rss.folha.uol.com.br/mercado.xml"          # Folha de S.Paulo Mercado
]

def buscar_noticias_credito():
    print("🔄 Coletando notícias dos portais...")
    noticias_relevantes = []
    termos_chave = ['crédito', 'inadimplência', 'juros', 'banco', 'financiamento', 'rotativo', 'serasa', 'banco central', 'selic']
    
    for url in FONTES_NOTICIAS:
        try:
            feed = feedparser.parse(url)
            for noticia in feed.entries:
                titulo = noticia.title
                resumo = noticia.get('summary', '')
                texto_analise = (titulo + " " + resumo).lower()
                
                if any(termo in texto_analise for termo in termos_chave):
                    noticias_relevantes.append({
                        "titulo": titulo,
                        "link": noticia.link,
                        "resumo_original": resumo
                    })
        except Exception as e:
            print(f"⚠️ Erro ao ler o portal {url}: {e}")
                
    print(f"✅ Coleta finalizada. Encontradas {len(noticias_relevantes)} notícias sobre crédito.")
    return noticias_relevantes[:10]

def gerar_briefing_com_gemini(lista_noticias):
    if not lista_noticias:
        return "Nenhuma movimentação expressiva de crédito PF reportada hoje.", "Sem novidades relevantes."
        
    print("🧠 Gemini analisando os impactos e gerando relatórios...")
    bloco_noticias = ""
    for i, n in enumerate(lista_noticias, 1):
        bloco_noticias += f"\n[{i}] TÍTULO: {n['titulo']}\nCONTEXTO: {n['resumo_original']}\n"
        
    prompt = f"""
    Você é um Analista Sênior de Inteligência de Mercado especializado em Crédito Bancário e Varejo (PF).
    Com base nas notícias do dia, gere DUAS saídas profissionais distintas, obrigatoriamente separadas pela tag [DIVISOR].

    VERSÃO 1: Relatório Completo (HTML)
    Escreva uma análise aprofundada estruturada estritamente nestes 3 tópicos com emojis:
    🚨 PRINCIPAL MOVIMENTO:
    📊 MACRO E JUROS:
    💳 COMPORTAMENTO DO CONSUMIDOR:

    [DIVISOR]

    VERSÃO 2: Resumo de Bolso (WhatsApp)
    Escreva um resumo executivo ultra-enxuto para leitura rápida no celular. 
    Use exatamente 3 tópicos de uma linha cada, iniciados por um hífen e um marcador simples (ex: - •). 
    Seja extremamente direto e curto para respeitar os limites de caracteres de texto.
    
    Notícias do dia:
    {bloco_noticias}
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
    
    partes = response.text.split("[DIVISOR]")
    
    html_txt = partes[0].strip()
    zap_txt = partes[1].strip() if len(partes) > 1 else "Acesse o painel para conferir as atualizações."
    
    return html_txt, zap_txt

def construir_pagina_html(conteudo_ia, lista_noticias):
    print("🎨 Renderizando página HTML executiva...")
    data_hoje = datetime.now().strftime("%d/%m/%Y")
    conteudo_formatado = conteudo_ia.replace("\n", "<br>")
    
    links_html = ""
    links_vistos = set()
    for n in lista_noticias:
        if n['link'] not in links_vistos:
            links_vistos.add(n['link'])
            links_html += f"<li><a href='{n['link']}' target='_blank'>{n['titulo']}</a></li>"

    html_code = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Briefing de Crédito PF</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #f4f6f9; color: #333; margin: 0; padding: 20px; }}
        .container {{ max-width: 650px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
        .header {{ border-bottom: 2px solid #004481; padding-bottom: 15px; margin-bottom: 25px; }}
        .header h1 {{ color: #004481; margin: 0; font-size: 24px; font-weight: 700; }}
        .date {{ color: #666; font-size: 14px; margin-top: 5px; }}
        .content {{ font-size: 16px; line-height: 1.6; color: #2c3e50; }}
        .content br {{ margin-bottom: 10px; }}
        .sources {{ margin-top: 35px; padding-top: 20px; border-top: 1px solid #e1e8ed; }}
        .sources h3 {{ color: #555; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; }}
        .sources ul {{ padding-left: 20px; font-size: 14px; color: #0066cc; }}
        .sources li {{ margin-bottom: 8px; }}
        a {{ color: #004481; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Briefing: Crédito Pessoa Física</h1>
            <div class="date">📅 Atualizado em: {data_hoje} | Inteligência de Mercado</div>
        </div>
        <div class="content">
            {conteudo_formatado}
        </div>
        <div class="sources">
            <h3>Fontes Monitoradas no Dia</h3>
            <ul>
                {links_html}
            </ul>
        </div>
    </div>
</body>
</html>"""
    return html_code

def obter_dados_repositorio():
    repo_completo = os.getenv("GITHUB_REPOSITORY")
    if repo_completo:
        return repo_completo.split("/")
    return os.getenv("GITHUB_USER", "usuario"), os.getenv("GITHUB_REPO", "agente_credito_pf")

def publicar_no_github(html_conteudo):
    print("🚀 Enviando relatório para o GitHub...")
    token = os.getenv("GITHUB_TOKEN")
    user, repo = obter_dados_repositorio()
    
    if not token or not repo:
        print("❌ ERRO: Credenciais ou variáveis do GitHub ausentes.")
        return None
        
    filename = "index.html"
    url = f"https://api.github.com/repos/{user}/{repo}/contents/{filename}"
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    conteudo_bytes = html_conteudo.encode('utf-8')
    conteudo_base64 = base64.b64encode(conteudo_bytes).decode('utf-8')
    
    sha = None
    res_get = requests.get(url, headers=headers)
    if res_get.status_code == 200:
        sha = res_get.json().get("sha")
        
    dados = {
        "message": f"Atualizando briefing matinal
