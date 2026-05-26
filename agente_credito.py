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
    print("🔄 Iniciando curadoria estrita de notícias sobre crédito...")
    noticias_relevantes = []
    
    termos_chave = [
        'crédito', 'inadimplência', 'juros', 'banco', 'financiamento', 
        'rotativo', 'serasa', 'banco central', 'selic', 'cheque especial', 
        'consignado', 'endividamento', 'tomada de crédito', 'carteira de crédito'
    ]
    
    termos_bloqueio = [
        'mega-sena', 'megasena', 'loteria', 'concurso', 'imóveis em joão pessoa', 
        'vagas de emprego', 'bolsa de valores', 'petrobras', 'vale', 'cripto', 
        'bitcoin', 'dividendos', 'ações caem', 'ações sobem', 'resultado trimestral'
    ]
    
    for url in FONTES_NOTICIAS:
        try:
            feed = feedparser.parse(url)
            for noticia in feed.entries:
                titulo = noticia.title
                resumo = noticia.get('summary', '')
                texto_analise = (titulo + " " + resumo).lower()
                
                if any(bloqueio in texto_analise for bloqueio in termos_bloqueio):
                    continue
                    
                if any(termo in texto_analise for termo in termos_chave):
                    if not any(n['link'] == noticia.link for n in noticias_relevantes):
                        noticias_relevantes.append({
                            "titulo": titulo,
                            "link": noticia.link,
                            "resumo_original": resumo
                        })
        except Exception as e:
            print(f"⚠️ Erro ao ler o portal {url}: {e}")
                
    print(f"✅ Curadoria finalizada. {len(noticias_relevantes)} fontes relevantes selecionadas.")
    return noticias_relevantes[:8]

def gerar_briefing_com_gemini(lista_noticias):
    if not lista_noticias:
        return "<li>Sem movimentações de impacto registradas hoje.</li>", "<p>Dia sem novidades relevantes.</p>", "Sem novidades relevantes."
        
    print("🧠 Gemini analisando cenários e gerando impactos individuais por notícia...")
    bloco_noticias = ""
    for i, n in enumerate(lista_noticias, 1):
        bloco_noticias += f"\n[{i}] TÍTULO: {n['titulo']}\nCONTEXTO: {n['resumo_original']}\nLINK: {n['link']}\n"
        
    prompt = (
        "Você é um Analista Sênior de Inteligência de Mercado especializado em Crédito Bancário e Varejo (PF).\n"
        "Com base no clipping fornecido, gere TRÊS saídas profissionais distintas, separadas estritamente pela tag [DIVISOR].\n"
        "NÃO utilize blocos de código ou marcações markdown como ```html no texto.\n\n"
        
        "SAÍDA 1: Tópicos Rápidos (HTML para o Sumário Executivo)\n"
        "Gere exatamente de 3 a 5 tópicos analíticos e ultra-concisos (massa de 1 linha cada), formatando-os direto com a tag <li>.\n"
        "Foque estritamente em fatos de impacto direto e imediato para o varejo financeiro de crédito.\n\n"
        
        "[DIVISOR]\n\n"
        
        "SAÍDA 2: Análise Profunda (HTML para o Corpo do Relatório)\n"
        "Gere a análise estruturada em exatamente três blocos temáticos fixos na ordem abaixo. "
        "Para CADA um dos três temas, escreva o parágrafo de contexto, inclua o link correspondente e, OBRIGATORIAMENTE, "
        "adicione o quadro '<div class='why-it-matters'>' adaptado especificamente para aquele tema.\n\n"
        
        "Siga rigorosamente esta estrutura de tags HTML:\n\n"
        
        "<h3>🚨 PRINCIPAL MOVIMENTO</h3>\n"
        "<p>[Análise condensada do fato mais relevante do dia] <a href='[LINK NOTÍCIA]' target='_blank'>👉 Leia matéria</a></p>\n"
        "<div class='why-it-matters'>\n"
        "    <h4>Por que importa para o Crédito PF:</h4>\n"
        "    <p>[Impacto estratégico e de negócios específico desse movimento, usando destaques em <b>negrito</b> para termos críticos]</p>\n"
        "</div>\n\n"
        
        "<h3>📊 MACRO E JUROS</h3>\n"
        "<p>[Impacto de juros, Selic, inflação ou decisões recentes do BC] <a href='[LINK NOTÍCIA]' target='_blank'>👉 Leia matéria</a></p>\n"
        "<div class='why-it-matters'>\n"
        "    <h4>Por que importa para o Crédito PF:</h4>\n"
        "    <p>[Impacto estratégico específico da macroeconomia na concessão/precificação, usando destaques em <b>negrito</b> para métricas/indicadores]</p>\n"
        "</div>\n\n"
        
        "<h3>💳 COMPORTAMENTO DO CONSUMIDOR</h3>\n"
        "<p>[Análise sobre tomada de crédito, níveis de inadimplência PF ou endividamento das famílias] <a href='[LINK NOTÍCIA]' target='_blank'>👉 Leia matéria</a></p>\n"
        "<div class='why-it-matters'>\n"
        "    <h4>Por que importa para o Crédito PF:</h4>\n"
        "    <p>[Impacto estratégico específico sobre o risco de carteira, PDD ou comportamento do tomador, usando destaques em <b>negrito</b>]</p>\n"
        "</div>\n\n"
        
        "[DIVISOR]\n\n"
        
        "SAÍDA 3: Resumo de Pocket (WhatsApp)\n"
        "Escreva um resumo ultra-executivo para celular com exatamente 3 tópicos de no máximo uma linha cada.\n"
        "Cada linha DEVE começar obrigatoriamente com o marcador '• ', seguido de um breve título em negrito representativo da notícia (2 a 4 palavras) e a síntese do fato.\n"
        "Exemplo de formato:\n"
        "• 💳 *Juros do Rotativo:* Banco Central estuda novas travas para conter inadimplência.\n\n"
        
        f"Clipping de notícias:\n{bloco_noticias}"
    )
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
    
    texto_ia = response.text
    for tag_sujeira in ["```html", "```HTML", "```", "**SAÍDA 1:**", "**SAÍDA 2:**", "**SAÍDA 3:**"]:
        texto_ia = texto_ia.replace(tag_sujeira, "")
        
    partes = texto_ia.split("[DIVISOR]")
    
    topicos_html = partes[0].strip()
    conteudo_corpo_html = partes[1].strip() if len(partes) > 1 else ""
    zap_txt = partes[2].strip() if len(partes) > 2 else "Acesse o painel para conferir as atualizações."
    
    return topicos_html, conteudo_corpo_html, zap_txt

def construir_pagina_html(topicos_ia, conteudo_ia, lista_noticias):
    print("🎨 Renderizando painel executivo através do template...")
    data_hoje = datetime.now().strftime("%d/%m/%Y")
    
    links_html = "".join(f"<li><a href='{n['link']}' target='_blank'>{n['titulo']}</a></li>" for n in lista_noticias)

    with open("template.html", "r", encoding="utf-8") as f:
        template = f.read()
        
    html_final = template.replace("{{DATA_HOJE}}", data_hoje)
    html_final = html_final.replace("{{TOPICOS_SUMARIO}}", topicos_ia)
    html_final = html_final.replace("{{CONTEUDO_IA}}", conteudo_ia)
    html_final = html_final.replace("{{LINKS_FONTES}}", links_html)
    
    return html_final

def obter_dados_repositorio():
    repo_completo = os.getenv("GITHUB_REPOSITORY")
    if repo_completo:
        return repo_completo.split("/")
    return os.getenv("GITHUB_USER", "usuario"), os.getenv("GITHUB_REPO", "agente_credito_pf")

def publicar_no_github(html_conteudo):
    print("🚀 Enviando relatório atualizado para o GitHub Pages...")
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
        "message": f"Atualizando briefing matinal com Por Que Importa individuais - {datetime.now().strftime('%d/%m/%Y')}",
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
        print("🚀 WhatsApp enviado com sucesso!")
    except Exception as e:
        print(f"❌ Falha ao disparar o WhatsApp: {e}")

if __name__ == "__main__":
    noticias_do_dia = buscar_noticias_credito()
    sumario_html, briefing_corpo, resumo_zap = gerar_briefing_com_gemini(noticias_do_dia)
    pagina_html = construir_pagina_html(sumario_html, briefing_corpo, noticias_do_dia)
    link_da_pagina = publicar_no_github(pagina_html)
    
    if link_da_pagina:
        time.sleep(5)
        enviar_alerta_whatsapp(link_da_pagina, resumo_zap)
