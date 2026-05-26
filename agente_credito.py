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
        return "<p>Nenhuma movimentação expressiva de crédito PF reportada hoje.</p>", "Sem novidades relevantes."
        
    print("🧠 Gemini analisando os impactos...")
    bloco_noticias = ""
    for i, n in enumerate(lista_noticias, 1):
        bloco_noticias += f"\n[{i}] TÍTULO: {n['titulo']}\nCONTEXTO: {n['resumo_original']}\n"
        
    prompt = (
        "Você é um Analista Sênior de Inteligência de Mercado especializado em Crédito Bancário e Varejo (PF).\n"
        "Com base nas notícias fornecidas, forneça uma análise macro-executiva condensada e analítica.\n"
        "NÃO use marcações de bloco de código como ```html ou cercados de markdown no texto.\n"
        "Gere DUAS saídas profissionais distintas, separadas estritamente pela tag [DIVISOR].\n\n"
        "VERSÃO 1: Relatório Completo (HTML Nativo)\n"
        "Escreva a análise formatando DIRETAMENTE em parágrafos HTML (<p>). Use exatamente estes tópicos:\n"
        "<p>🚨 <b>PRINCIPAL MOVIMENTO:</b> [Resumo ultra-condensado do fato mais relevante do dia]</p>\n"
        "<p>📊 <b>MACRO E JUROS:</b> [Impacto de indicadores, Selic, inflação ou decisões do BC]</p>\n"
        "<p>💳 <b>COMPORTAMENTO DO CONSUMIDOR:</b> [Tomada de crédito, endividamento ou inadimplência da PF]</p>\n\n"
        "[DIVISOR]\n\n"
        "VERSÃO 2: Resumo de Pocket (WhatsApp)\n"
        "Escreva um resumo executivo focado em leitura rápida para celular.\n"
        "Crie exatamente 3 tópicos de no máximo uma linha cada, usando o marcador simples '• '.\n\n"
        f"Notícias extraídas do clipping:\n{bloco_noticias}"
    )
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
    
    texto_ia = response.text
    for tag_sujeira in ["```html", "```HTML", "```", "**VERSÃO 1:**", "**VERSÃO 2:**"]:
        texto_ia = texto_ia.replace(tag_sujeira, "")
        
    partes = texto_ia.split("[DIVISOR]")
    html_txt = partes[0].strip()
    zap_txt = partes[1].strip() if len(partes) > 1 else "Acesse o painel para conferir as atualizações."
    
    return html_txt, zap_txt

def construir_pagina_html(conteudo_ia, lista_noticias):
    print("🎨 Renderizando painel executivo através do template...")
    data_hoje = datetime.now().strftime("%d/%m/%Y")
    
    links_html = ""
    links_vistos = set()
    for n in lista_noticias:
        if n['link'] not in links_vistos:
            links_vistos.add(n['link'])
            links_html += f"<li><a href='{n['link']}' target='_blank'>{n['titulo']}</a></li>"

    # Carrega a estrutura isolada criada no Passo 1
    with open("template.html", "r", encoding="utf-8") as f:
        template = f.read()
        
    # Substitui as variáveis dentro do HTML de forma segura
    html_final = template.replace("{{DATA_HOJE}}", data_hoje)
    html_final = html_final.replace("{{CONTEUDO_IA}}", conteudo_ia)
    html_final = html_final.replace("{{LINKS_FONTES}}", links_html)
    
    return html_final

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
        print("❌ ERRO: Credenciais ausentes.")
        return None
        
    filename = "index.html"
    url = f"https://api.github.com/repos/{user}/{repo}/contents/{filename}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    
    sha = None
    res_get = requests.get(url, headers=headers)
    if res_get.status_code == 200:
        sha = res_get.json().get("sha")
        
    dados = {
        "message": f"Atualizando briefing matinal - {datetime.now().strftime('%d/%m/%Y')}",
        "content": base64.b64encode(html_conteudo.encode('utf-8')).decode('utf-8')
    }
    if sha:
        dados["sha"] = sha
        
    res_put = requests.put(url, headers=headers, json=dados)
    if res_put.status_code in [200, 201]:
        return f"https://{user}.github.io/{repo}/"
    return None

def enviar_alerta_whatsapp(link_painel, resumo_executivo):
    print("📲 Acionando o Callmebot...")
    phone = os.getenv("CALLMEBOT_PHONE")
    apikey = os.getenv("CALLMEBOT_API_KEY")
    
    texto_mensagem = f"💼 *Briefing Crédito PF*\n\n{resumo_executivo}\n\n🔗 *Painel completo:* {link_painel}"
    url_callmebot = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={requests.utils.quote(texto_mensagem)}&apikey={apikey}"
    
    try:
        requests.get(url_callmebot)
        print("🚀 Processo de notificação concluído!")
    except Exception as e:
        print(f"❌ Falha ao disparar o WhatsApp: {e}")

if __name__ == "__main__":
    noticias_do_dia = buscar_noticias_credito()
    briefing_html, resumo_zap = gerar_briefing_com_gemini(noticias_do_dia)
    pagina_html = construir_pagina_html(briefing_html, noticias_do_dia)
    link_da_pagina = publicar_no_github(pagina_html)
    
    if link_da_pagina:
        time.sleep(5)
        enviar_alerta_whatsapp(link_da_pagina, resumo_zap)
