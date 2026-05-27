import os
import base64
import feedparser
import requests
import time
from google import genai
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo

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
    print("🔄 Iniciando curadoria estrita de notícias sobre crédito e varejo bancário...")
    noticias_relevantes = []
    
    termos_chave = [
        'crédito', 'inadimplência', 'juros', 'banco', 'financiamento', 'pix', 'drex',
        'rotativo', 'serasa', 'banco central', 'selic', 'cheque especial', 'fintech',
        'consignado', 'endividamento', 'habitação', 'imobiliário', 'veículos', 'portabilidade'
    ]
    
    # Filtro cirúrgico: mantendo termos de mercado acionário e balanços para análise semântica da IA
    termos_bloqueio = [
        # 1. CLASSIFICADOS E VAREJO IMOBILIÁRIO LOCAL
        'apartamento à venda', 'apartamentos à venda', 'casa à venda', 'casas à venda', 
        'feirão de imóveis', 'feirao de imoveis', 'lançamento imobiliário', 'lancamento imobiliario',
        'aluga-se', 'aluguel de temporada', 'incorporadora lança',

        # 2. MICRO-NOTICIÁRIO DE RH E CARREIRAS
        'vagas de emprego', 'vagas de estágio', 'vagas de estagio', 'processo seletivo', 
        'trabalhe conosco',

        # 3. COMMODITIES E SETORES SEM CORRELAÇÃO DIRETA COM CRÉDITO PF
        'petrobras', 'vale', 'commodities', 'minério de ferro', 'petróleo',

        # 4. ATIVOS DIGITAIS ESPECULATIVOS E SORTEIOS
        'bitcoin', 'cripto', 'criptomoedas', 'ethereum', 'defi', 'nft',
        'mega-sena', 'megasena', 'loteria', 'concurso', 'quadra', 'quina'
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
    return noticias_relevantes[:12]

def gerar_briefing_com_gemini(lista_noticias):
    if not lista_noticias:
        return "<li>Sem movimentações de impacto registradas hoje.</li>", "<p>Dia sem novidades relevantes.</p>", "Sem novidades relevantes."
        
    print("🧠 Gemini gerando conteúdo estruturado...")
    bloco_noticias = ""
    for i, n in enumerate(lista_noticias, 1):
        bloco_noticias += f"\n[{i}] TÍTULO: {n['titulo']}\nCONTEXTO: {n['resumo_original']}\nLINK: {n['link']}\n"
        
    prompt = (
        "Você é um Analista Sênior de Inteligência de Mercado especializado em Crédito Bancário e Varejo (PF).\n"
        "Com base no clipping fornecido, gere três blocos de conteúdo estritamente delimitados pelas tags informadas.\n"
        "NÃO adicione introduções, explicações ou marcações markdown como ```html no texto.\n\n"
        
        "DIRETRIZ DE FILTRAGEM INTELIGENTE:\n"
        "Ignore o sobe-e-desce diário comum da bolsa de valores ou balanços de empresas industriais puras. "
        "Contudo, se houver oscilações drásticas baseadas em resultados trimestrais de grandes bancos, neobanks ou eventos de crédito corporativo que possam gerar efeito cascata no varejo, capture o fato e destaque o impacto no grupo adequado.\n\n"
        
        "1) Entre as tags [INICIO_SUMARIO] e [FIM_SUMARIO], gere de 3 a 4 tópicos executivos no formato <li> para o Sumário Executivo.\n"
        "Cada tópico DEVE começar obrigatoriamente com um mini-título em negrito (2 a 4 palavras) que resume o fato, seguido de dois pontos e a síntese do impacto.\n"
        "Exemplo: <li><b>Risco INSS:</b> Vazamento de dados de CPFs vivos gera alerta de fraudes...</li>\n\n"
        
        "2) Entre as tags [INICIO_CORPO] e [FIM_CORPO], distribua as análises nas 6 categorias abaixo.\n"
        "REGRA CRÍTICA DE FORMATO PARA OS 6 GRUPOS:\n"
        "Todas as notícias integradas em um grupo devem ser exibidas obrigatoriamente como tópicos de uma lista utilizando as tags <ul> e <li>.\n"
        "Cada item da lista (cada notícia individual) deve trazer um pequeno título descritivo próprio em negrito, um breve resumo analítico focado no mercado de crédito e o respectivo link de acesso.\n"
        "Se não houver movimentação para a categoria, insira apenas um parágrafo simples informando o cenário neutro, mantendo o h3 do grupo.\n\n"
        
        "SIGA EXATAMENTE ESTE PADRÃO DE TAGS PARA O CORPO:\n"
        "<h3>🏛️ REGULAÇÃO E GRANDES FATOS</h3>\n"
        "<ul>\n"
        "    <li><b>[Mini-título da Notícia]:</b> [Resumo analítico focado no impacto de crédito] <a href='[LINK]' target='_blank'>👉 Ver notícia completa</a></li>\n"
        "</ul>\n\n"
        
        "<h3>📊 MACRO E JUROS</h3>\n"
        "<ul>\n"
        "    <li><b>[Mini-título]:</b> [Resumo analítico] <a href='[LINK]' target='_blank'>👉 Ver notícia completa</a></li>\n"
        "</ul>\n\n"
        
        "<h3>💸 CRÉDITO CLEAN (SEM GARANTIA)</h3>\n"
        "<ul>\n"
        "    <li><b>[Mini-título]:</b> [Resumo analítico] <a href='[LINK]' target='_blank'>👉 Ver notícia completa</a></li>\n"
        "</ul>\n\n"
        
        "<h3>🚗 CRÉDITO COLATERALIZADO (COM GARANTIA)</h3>\n"
        "<ul>\n"
        "    <li><b>[Mini-título]:</b> [Resumo analítico] <a href='[LINK]' target='_blank'>👉 Ver notícia completa</a></li>\n"
        "</ul>\n\n"
        
        "<h3>🔄 INOVAÇÃO E MEIOS DE PAGAMENTO</h3>\n"
        "<ul>\n"
        "    <li><b>[Mini-título]:</b> [Resumo analítico] <a href='[LINK]' target='_blank'>👉 Ver notícia completa</a></li>\n"
        "</ul>\n\n"
        
        "<h3>🏁 CONCORRÊNCIA E FINTECHS</h3>\n"
        "<ul>\n"
        "    <li><b>[Mini-título]:</b> [Resumo analítico] <a href='[LINK]' target='_blank'>👉 Ver notícia completa</a></li>\n"
        "</ul>\n\n"
        
        "\n"
        "<hr style='border: 0; border-top: 1px solid #e2e8f0; margin: 40px 0;'>\n"
        "<div style='background-color: #f8fafc; border-left: 4px solid #475569; padding: 20px; border-radius: 4px;'>\n"
        "    <h4 style='margin-top: 0; color: #1e293b; font-size: 16px;'>📔 Notas Metodológicas: O que monitoramos</h4>\n"
        "    <ul style='padding-left: 20px; color: #475569; font-size: 13px; line-height: 1.6;'>\n"
        "        <li><b>Regulação e Grandes Fatos:</b> Captura novas diretrizes regulatórias (BC, CMN), alterações na legislação do sistema financeiro ou intervenções governamentais estruturais que redefinem os limites e parâmetros operacionais do mercado bancário.</li>\n"
        "        <li><b>Macro e Juros:</b> Monitora os principais indicadores macroeconômicos (Selic, IPCA, Focus), focando na dinâmica de captação de recursos, custo de capital e compressão ou expansão dos spreads financeiros.</li>\n"
        "        <li><b>Crédito Clean (Sem Garantia):</b> Concentra as análises em linhas de alto rendimento e risco de cauda elevado (Cartão, Rotativo, Cheque Especial, Consignado), avaliando o endividamento e a tendência imediata das safras de inadimplência e provisões (PDD).</li>\n"
        "        <li><b>Crédito Colateralizado (Com Garantia):</b> Isola os movimentos de linhas vinculadas a ativos reais (Imobiliário e Automotivo), onde o foco está no ciclo de vida longo, nas taxas estruturais de juros e nos indicadores de garantia de colateral (LTV).</li>\n"
        "        <li><b>Inovação e Meios de Pagamento:</b> Acompanha as transformações tecnológicas na originação e liquidação financeira (Pix, Drex), mapeando como novos ecossistemas alteram a transacionalidade e competem com os arranjos tradicionais de crédito.</li>\n"
        "        <li><b>Concorrência e Fintechs:</b> Rastreia o posicionamento estratégico dos players alternativos (neobanks, cooperativas, carteiras), antecipando pressões competitivas sobre taxas, portabilidade e perda de share de mercado.</li>\n"
        "    </ul>\n"
        "</div>\n\n"
        
        "3) Entre as tags [INICIO_ZAP] e [FIM_ZAP], gere o texto para o WhatsApp (3 a 4 tópicos com '• ' e o mini-título em negrito, idêntico ao conteúdo do sumário executivo, mas sem formatação HTML).\n\n"
        
        f"Clipping de notícias:\n{bloco_noticias}"
    )
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
    
    texto_ia = response.text
    
    # Extração limpa baseada em delimitadores estritos
    try:
        topicos_html = texto_ia.split("[INICIO_SUMARIO]")[1].split("[FIM_SUMARIO]")[0].strip()
    except:
        topicos_html = "<li>Erro na geração do sumário. Acesse as fontes completas abaixo.</li>"
        
    try:
        conteudo_corpo_html = texto_ia.split("[INICIO_CORPO]")[1].split("[FIM_CORPO]")[0].strip()
    except:
        conteudo_corpo_html = "<p>Erro na formatação do relatório.</p>"
        
    try:
        zap_txt = texto_ia.split("[INICIO_ZAP]")[1].split("[FIM_ZAP]")[0].strip()
    except:
        zap_txt = "Acesse o painel para conferir as atualizações de Crédito PF."
        
    # Limpeza final preventiva contra vazamento de tags markdown
    for tag_sujeira in ["```html", "```HTML", "```"]:
        topicos_html = topicos_html.replace(tag_sujeira, "")
        conteudo_corpo_html = conteudo_corpo_html.replace(tag_sujeira, "")
        zap_txt = zap_txt.replace(tag_sujeira, "")
        
    return topicos_html, conteudo_corpo_html, zap_txt

def construir_pagina_html(topicos_ia, conteudo_ia, lista_noticias):
    print("🎨 Renderizando painel executivo através do template...")
    data_hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y")
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
        "message": f"Filtros semanticos avançados e espelhamento executivo de layout - {datetime.now(ZoneInfo('America/Sao_Paulo')).strftime('%d/%m/%Y')}",
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
