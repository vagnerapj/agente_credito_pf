import os
import base64
import feedparser
import requests
import time
from google import genai
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
client = genai.Client()

FONTES_NOTICIAS = [
    "https://valor.globo.com/rss/financas/",
    "https://www.infomoney.com.br/onde-investir/feed/",
    "https://g1.globo.com/rss/g1/economia/",
    "https://economia.estadao.com.br/rss/",
    "https://rss.folha.uol.com.br/mercado.xml"
]

PROMPT_BASE = """
Você é um Analista Sênior de Inteligência de Mercado especializado em Crédito Bancário (PF).
Com base nas notícias fornecidas, gere duas saídas estritamente separadas pela tag [DIVISOR].
NÃO use blocos de código markdown como ```html.

VERSÃO 1: Relatório Completo (HTML)
Formate direto em parágrafos HTML (<p>). Use os tópicos exatamente assim:
<p>🚨 <b>PRINCIPAL MOVIMENTO:</b> [Análise concisa e direta do fato mais relevante do dia]</p>
<p>📊 <b>MACRO E JUROS:</b> [Impacto de juros, inflação ou decisões do BC]</p>
<p>💳 <b>COMPORTAMENTO DO CONSUMIDOR:</b> [Tomada de crédito, inadimplência e endividamento PF]</p>

[DIVISOR]

VERSÃO 2: Resumo de Bolso (WhatsApp)
Escreva um resumo ultra-executivo para celular.
Use exatamente 3 tópicos, cada um com no máximo uma linha, iniciados por "• ". Seja direto.

Notícias extraídas:
"""

def buscar_noticias_credito():
    print("🔄 Coletando notícias dos portais...")
    noticias_relevantes = []
    termos_chave = ['crédito', 'inadimplência', 'juros', 'banco', 'financiamento', 'rotativo', 'serasa', 'banco central', 'selic']
    for url in FONTES_NOTICIAS:
        try:
            feed = feedparser.parse(url)
            for noticia in feed.entries:
                texto = (noticia.title + " " + noticia.get('summary', '')).lower()
                if any(termo in texto for termo in termos_chave):
                    noticias_relevantes.append({"titulo": noticia.title, "link": noticia.link, "resumo": noticia.get('summary', '')})
        except Exception as e:
            print(f"⚠️ Erro no portal {url}: {e}")
    return noticias_relevantes[:10]

def gerar_briefing_com_gemini(lista_noticias):
    if not lista_noticias:
        return "<p>Nenhuma movimentação de crédito reportada hoje.</p>", "Sem novidades."
    
    print("🧠 Gemini analisando cenários...")
    bloco = ""
    for i, n in enumerate(lista_noticias, 1):
        bloco += f"\n[{i}] {n['titulo']}\nContexto: {n['resumo']}\n"
        
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=PROMPT_BASE + bloco,
    )
    
    texto_ia = response.text
    for sujeira in ["```html", "```HTML", "```", "**VERSÃO 1:**", "**VERSÃO 2:**"]:
        texto_ia = texto_ia.replace(sujeira, "")
        
    partes = texto_ia.split("[DIVISOR]")
    html_txt = partes[0].strip()
    zap_txt = partes[1].strip() if len(partes) > 1 else "Acesse o painel para conferir."
    return html_txt, zap_txt

def construir_pagina_html(conteudo_ia, lista_noticias):
    print("🎨 Renderizando HTML...")
    data_hoje = datetime.now().strftime("%d/%m/%Y")
    links_html = "".join(f"<li><a href='{n['link']}' target='_blank'>{n['titulo']}</a></li>" for n in lista_noticias)
    
    return f"""<!DOCTYPE html><html lang='pt-BR'><head><meta charset='UTF-8'><title>Briefing de Crédito PF</title><style>body {{ font-family: -apple-system, sans-serif; background-color: #f4f6f9; color: #333; padding: 20px; }} .container {{ max-width: 650px; margin: 20px auto; background: #fff; padding: 35px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.06); }} .header {{ border-bottom: 3px solid #004481; padding-bottom: 18px; margin-bottom: 25px; }} h1 {{ color: #004481; margin: 0; font-size: 26px; }} .content {{ font-size: 15px; line-height: 1.7; }} .sources {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #e1e8ed; font-size: 14px; }} a {{ color: #004481; text-decoration: none; }}</style></head><body><div class='container'><div class='header'><h1>Briefing Diário: Crédito Pessoa Física</h1><div>📅 {data_hoje}</div></div><div class='content'>{conteudo_ia}</div><div class='sources'><h3>Fontes Consultadas</h3><ul>{links_html}</ul></div></div></body></html>"""

def publicar_no_github(html_conteudo):
    print("🚀 Enviando para o GitHub...")
    token = os.getenv("GITHUB_TOKEN")
    repo_completo = os.getenv("GITHUB_REPOSITORY")
    if not token or not repo_completo:
        print("❌ Credenciais ausentes.")
        return None
        
    user, repo = repo_completo.split("/")
    url = f"https://api.github.com/repos/{user}/{repo}/contents/index.html"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    
    sha = None
    res_get = requests.get(url, headers=headers)
    if res_get.status_code == 200:
        sha = res_get.json().get("sha")
        
    dados = {
        "message": f"Atualizando briefing - {datetime.now().strftime('%d/%m/%Y')}",
        "content": base64.b64encode(html_conteudo.encode('utf-8')).decode('utf-8')
    }
    if sha:
        dados["sha"] = sha
        
    res_put = requests.put(url, headers=headers, json=dados)
    if res_put.status_code in [200, 201]:
        return f"https://{user}.github.io/{repo}/"
    return None

def enviar_alerta_whatsapp(link_painel, resumo_executivo):
    print("📲 Acionando Callmebot...")
    phone = os.getenv("CALLMEBOT_PHONE")
    apikey = os.getenv("CALLMEBOT_API_KEY")
    msg = f"💼 *Briefing Crédito PF*\n\n{resumo_executivo}\n\n🔗 *Painel completo:* {link_painel}"
    try:
        requests.get(f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={requests.utils.quote(msg)}&apikey={apikey}")
        print("🚀 WhatsApp enviado com sucesso!")
    except Exception as e:
        print(f"❌ Erro WhatsApp: {e}")

if __name__ == "__main__":
    noticias = buscar_noticias_credito()
    html_ia, zap_ia = gerar_briefing_com_gemini(noticias)
    pagina = construir_pagina_html(html_ia, noticias)
    link = publicar_no_github(pagina)
    if link:
        time.sleep(5)
        enviar_alerta_whatsapp(link, zap_ia)
