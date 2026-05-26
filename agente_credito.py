import os
import base64
import feedparser
import requests
import time  # <-- ADICIONE ESTA LINHA AQUI
from google import genai
from dotenv import load_dotenv
from datetime import datetime

# 1. Carrega as configurações
load_dotenv()

client = genai.Client()

FONTES_NOTICIAS = [
    "https://valor.globo.com/rss/financas/",
    "https://www.infomoney.com.br/onde-investir/feed/"
]

def buscar_noticias_credito():
    print("🔄 Coletando notícias dos portais...")
    noticias_relevantes = []
    termos_chave = ['crédito', 'inadimplência', 'juros', 'banco', 'financiamento', 'rotativo', 'serasa', 'banco central', 'selic']
    
    for url in FONTES_NOTICIAS:
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
                
    print(f"✅ Coleta finalizada. Encontradas {len(noticias_relevantes)} notícias sobre crédito.")
    return noticias_relevantes[:10]

def gerar_briefing_com_gemini(lista_noticias):
    if not lista_noticias:
        return "Nenhuma movimentação expressiva de crédito PF reportada nos portais hoje."
        
    print("🧠 Gemini analisando os impactos de mercado...")
    bloco_noticias = ""
    for i, n in enumerate(lista_noticias, 1):
        bloco_noticias += f"\n[{i}] TÍTULO: {n['titulo']}\nCONTEXTO: {n['resumo_original']}\n"
        
    prompt = f"""
    Você é um Analista Sênior de Inteligência de Mercado especializado em Crédito Bancário e Varejo (PF).
    Com base nas notícias do dia fornecidas abaixo, crie um briefing matinal estritamente profissional e resumido.
    
    Estrutura exigida (mantenha exatamente estes títulos com os emojis):
    🚨 PRINCIPAL MOVIMENTO:
    📊 MACRO E JUROS:
    💳 COMPORTAMENTO DO CONSUMIDOR:
    
    Seja extremamente direto, use linguagem corporativa e adicione quebras de linha entre os tópicos. Não use caracteres especiais estranhos.
    
    Notícias do dia:
    {bloco_noticias}
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
    return response.text

def construir_pagina_html(conteudo_ia, lista_noticias):
    print("🎨 Renderizando página HTML executiva...")
    data_hoje = datetime.now().strftime("%d/%m/%Y")
    conteudo_formatado = conteudo_ia.replace("\n", "<br>")
    
    links_html = ""
    for n in lista_noticias:
        links_html += f"<li><a href='{n['link']}' target='_blank'>{n['titulo']}</a></li>"

    html = f"""
    <!DOCTYPE html>
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
                <h1>Briefing Semanal: Crédito Pessoa Física</h1>
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
    </html>
    """
    return html

def publicar_no_github(html_conteudo):
    print("🚀 Enviando relatório para o GitHub...")
    token = os.getenv("GITHUB_TOKEN")
    user = os.getenv("GITHUB_USER")
    repo = os.getenv("GITHUB_REPO")
    
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
        "message": f"Atualizando briefing matinal - {datetime.now().strftime('%d/%m/%Y')}",
        "content": conteudo_base64
    }
    if sha:
        dados["sha"] = sha
        
    res_put = requests.put(url, headers=headers, json=dados)
    
    if res_put.status_code in [200, 201]:
        link_final = f"https://{user}.github.io/{repo}/"
        print(f"🌍 Sucesso! Página publicada na Web: {link_final}")
        return link_final
    else:
        print(f"❌ Erro ao enviar para o GitHub: {res_put.text}")
        return None

# --- NOVA FUNÇÃO DE ALERTA DO WHATSAPP ---
def enviar_alerta_whatsapp(link_painel):
    print("📲 Acionando o Callmebot para enviar o WhatsApp...")
    phone = os.getenv("CALLMEBOT_PHONE")
    apikey = os.getenv("CALLMEBOT_API_KEY")
    
    data_hoje = datetime.now().strftime("%d/%m/%Y")
    
    # Texto curto e elegante para o WhatsApp
    texto_mensagem = (
        f"💼 *Briefing de Crédito PF* - {data_hoje}\n\n"
        f"Olá! O seu relatório executivo matinal de inteligência de mercado já foi processado e está disponível.\n\n"
        f"🔗 *Acesse o painel completo aqui:* {link_painel}"
    )
    
    # Codifica o texto para URL padrão
    texto_url = requests.utils.quote(texto_mensagem)
    url_callmebot = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={texto_url}&apikey={apikey}"
    
    try:
        response = requests.get(url_callmebot)
        if response.status_code == 200:
            print("🚀 Notificação enviada com sucesso para o seu celular!")
        else:
            print(f"⚠️ Callmebot retornou status: {response.status_code}")
    except Exception as e:
        print(f"❌ Falha ao disparar o WhatsApp: {e}")

# --- Fluxo Executivo Completo ---
if __name__ == "__main__":
    noticias_do_dia = buscar_noticias_credito()
    briefing_txt = gerar_briefing_com_gemini(noticias_do_dia)
    pagina_html = construir_pagina_html(briefing_txt, noticias_do_dia)
    
    # Executa a publicação e captura o link público gerado
    link_da_pagina = publicar_no_github(pagina_html)

    # Se o link foi gerado, espera o GitHub Pages atualizar e dispara o Zap
    if link_da_pagina:
        print("⏳ Aguardando 10 segundos para o GitHub Pages indexar a página...")
        time.sleep(10) # <-- ADICIONE ESTA LINHA AQUI
        enviar_alerta_whatsapp(link_da_pagina)
