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
                
    print(f"✅ Curadoria finalizada. {len(noticias_relevantes)} fontes estritamente relevantes selecionadas.")
    return noticias_relevantes[:8]

def gerar_briefing_com_gemini(lista_noticias):
    if not lista_noticias:
        return "<p>Nenhuma movimentação expressiva de crédito PF reportada hoje.</p>", "Sem novidades relevantes."
        
    print("🧠 Gemini analisando os impactos e aplicando destaques executivos...")
    bloco_noticias = ""
    for i, n in enumerate(lista_noticias, 1):
        bloco_noticias += f"\n[{i}] TÍTULO: {n['titulo']}\nCONTEXTO: {n['resumo_original']}\nLINK: {n['link']}\n"
        
    prompt = (
        "Você é um Analista Sênior de Inteligência de Mercado especializado em Crédito Bancário e Varejo (PF).\n"
        "Com base no clipping fornecido, gere duas saídas estritamente separadas pela tag [DIVISOR].\n"
        "NÃO utilize blocos de código ou marcações markdown como ```html no texto.\n\n"
        "VERSÃO 1: Relatório Completo (HTML Nativo)\n"
        "Escreva a análise formatando DIRETAMENTE em parágrafos HTML (<p>). Use exatamente estes tópicos:\n"
        "<p>🚨 <b>PRINCIPAL MOVIMENTO:</b> [Análise do fato mais relevante] <a href='[LINK DA NOTÍCIA COMPATÍVEL]' target='_blank'>👉 Leia a matéria completa</a></p>\n"
        "<p>📊 <b>MACRO E JUROS:</b> [Impacto de juros, Selic ou inflação] <a href='[LINK DA NOTÍCIA COMPATÍVEL]' target='_blank'>👉 Leia a matéria completa</a></p>\n"
        "<p>💳 <b>COMPORTAMENTO DO CONSUMIDOR:</b> [Inadimplência, endividamento ou tomada de crédito] <a href='[LINK DA NOTÍCIA COMPATÍVEL]' target='_blank'>👉 Leia a matéria completa</a></p>\n\n"
        "DIRETRIZ DE DESTAQUE ANALÍTICO (OBRIGATÓRIO):\n"
        "Dentro de cada parágrafo do relatório HTML acima, aplique a tag <b>...</b> para destacar em negrito as palavras ou expressões-chave que justificam a importância do fato para o ecossistema de crédito PF.\n"
        "Exemplos de termos para destacar: variações de taxas (ex: 'alta de 0,5 p.p.'), indicadores de risco (ex: 'alavancagem das famílias', 'inadimplência do rotativo', 'perfil de risco'), ou movimentos de mercado (ex: 'restrição de concessão', 'alongamento de prazo').\n"
        "Seja cirúrgico: destaque apenas 2 ou 3 expressões cruciais por parágrafo para manter a escaneabilidade do texto.\n"
        "Nota: Identifique qual link do clipping melhor se associa a cada tema e coloque-o no respectivo 'href'.\n\n"
        "[DIVISOR]\n\n"
        "VERSÃO 2: Resumo de Pocket (WhatsApp)\n"
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
    for tag_sujeira in ["```html", "```HTML", "```", "**VERSÃO 1:**", "**VERSÃO 2:**"]:
        texto_ia = texto_ia.replace(tag_sujeira, "")
        
    partes = texto_ia.split("[DIVISOR]")
    html_txt = partes[0].strip()
    zap_txt = partes[1].strip() if len(partes) > 1 else "Acesse o painel para conferir as atualizações do dia."
    
    return html_txt, zap_txt

def construir_pagina_html(conteudo_ia, lista_noticias):
    print("🎨 Renderizando painel executivo através do template...")
    data_hoje = datetime.now().strftime("%d/%m/%Y")
    
    links_html = "".join(f"<li><a href='{n['link']}' target='_blank'>{n['titulo']}</a></li>" for n in lista_noticias)

    with open("template.html", "r", encoding="utf-8") as f:
        template = f.read()
        
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
    print("🚀 Enviando relatório atualizado para o GitHub...")
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
        "message": f"Atualizando briefing matinal com destaques analiticos - {datetime.now().strftime('%d/%m/%Y')}",
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
    briefing_html, resumo_zap = gerar_briefing_com_gemini(noticias_do_dia)
    pagina_html = construir_pagina_html(briefing_html, noticias_do_dia)
    link_da_pagina = PUBLICAR_NO_GITHUB(pagina_html)
    
    if link_da_pagina:
        time.sleep(5)
        enviar_alerta_whatsapp(link_da_pagina, resumo_zap)
