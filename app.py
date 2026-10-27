import streamlit as st
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from openai import OpenAI

st.set_page_config(page_title="Matrix V6 - Multi-Agentes", page_icon="🤖", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stButton>button { width: 100%; font-weight: bold; background-color: #007acc; color: white; border-radius: 4px; padding: 0.4rem; font-size: 14px; }
    h1 { font-size: 1.4rem !important; text-align: center; margin-bottom: 0px; }
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    </style>
""", unsafe_allow_html=True)

st.title("🤖 MATRIX V6 • MULTI-AGENTES")

# --- LEITURA DA CHAVE ---
if "OPENAI_API_KEY" in st.secrets:
    api_key_input = st.secrets["OPENAI_API_KEY"]
else:
    api_key_input = st.sidebar.text_input("Chave OpenAI (API Key)", type="password")

# --- CONFIGURAÇÕES DE RISCO ---
st.sidebar.header("⚙️ Configurações & Risco")
banca_inicial = st.sidebar.number_input("Banca Inicial (R$)", value=500.0, step=10.0)
stake = st.sidebar.number_input("Valor da Entrada (R$)", value=5.0, step=1.0)
payout = st.sidebar.number_input("Payout (%)", value=82.0, step=1.0)
meta_lucro = st.sidebar.number_input("Meta de Lucro (R$)", value=50.0, step=5.0)
stop_loss = st.sidebar.number_input("Stop Loss (R$)", value=30.0, step=5.0)

if 'banca_atual' not in st.session_state:
    st.session_state.banca_atual = banca_inicial
if 'wins' not in st.session_state:
    st.session_state.wins = 0
if 'losses' not in st.session_state:
    st.session_state.losses = 0
if 'lucro_liquido' not in st.session_state:
    st.session_state.lucro_liquido = 0.0

total_trades = st.session_state.wins + st.session_state.losses
if total_trades == 0:
    st.session_state.banca_atual = banca_inicial

ARQUIVO_MEMORIA = "agent_history.json"

def carregar_historico_15_dias():
    if not os.path.exists(ARQUIVO_MEMORIA):
        return []
    try:
        with open(ARQUIVO_MEMORIA, "r", encoding="utf-8") as f:
            dados = json.load(f)
        limite_data = datetime.now(ZoneInfo("America/Sao_Paulo")) - timedelta(days=15)
        return [item for item in dados if datetime.strptime(item["timestamp_data"], "%Y-%m-%d %H:%M:%S") >= limite_data.replace(tzinfo=None)]
    except Exception:
        return []

def salvar_memoria_historico(resultado, feedback):
    agora = datetime.now(ZoneInfo("America/Sao_Paulo"))
    novo_registro = {
        "timestamp_data": agora.strftime("%Y-%m-%d %H:%M:%S"),
        "resultado": resultado,
        "feedback_coordenador": feedback
    }
    historico = []
    if os.path.exists(ARQUIVO_MEMORIA):
        try:
            with open(ARQUIVO_MEMORIA, "r", encoding="utf-8") as f:
                historico = json.load(f)
        except Exception:
            historico = []
    historico.append(novo_registro)
    with open(ARQUING := ARQUIVO_MEMORIA) if False else open(ARQUIVO_MEMORIA, "w", encoding="utf-8") as f:
        json.dump(historico, f, indent=4, ensure_ascii=False)

def calcular_proxima_vela(agora, timeframe_str):
    minutos_tf = 5
    if "1M" in timeframe_str.upper():
        minutos_tf = 1
    elif "5M" in timeframe_str.upper():
        minutos_tf = 5
    elif "15M" in timeframe_str.upper():
        minutos_tf = 15
    
    minuto_atual = agora.minute
    resto = minuto_atual % minutos_tf
    minutos_faltantes = minutos_tf - resto
    if minutos_faltantes == 0 and agora.second == 0:
        minutos_faltantes = minutos_tf
        
    proxima = agora + timedelta(minutes=minutos_faltantes)
    return proxima.replace(second=0, microsecond=0).strftime("%H:%M:00")

# --- PAINEL COMPACTO ---
c1, c2, c3 = st.columns(3)
c1.metric("Banca", f"R${st.session_state.banca_atual:.1f}")
c2.metric("Lucro", f"R${st.session_state.lucro_liquido:+.1f}")
win_rate = (st.session_state.wins / total_trades * 100) if total_trades > 0 else 0.0
c3.metric("Win Rate", f"{win_rate:.0f}%")

st.divider()

# --- INTERFACE DE ENTRADA ---
st.subheader("🤖 Mesa de Operações (Multi-Agentes)")
agora_sp = datetime.now(ZoneInfo("America/Sao_Paulo"))
st.caption(f"🕒 Relógio SP: **{agora_sp.strftime('%H:%M:%S')}**")

ativo_escolhido = st.selectbox("Selecione o Ativo na Hezilex:", ["EUR/USD", "GBP/USD", "AUD/USD", "EUR/JPY", "USD/JPY", "CARDANO"])
arquivo_print = st.file_uploader("Envie o Print do Gráfico da Hezilex", type=["jpg", "jpeg", "png"])

if arquivo_print is not None:
    st.image(arquivo_print, caption=f"Gráfico de {ativo_escolhido} carregado", use_container_width=True)
    
    if st.button("🚀 ACIONAR COMITÊ DE AGENTES"):
        if not api_key_input:
            st.error("⚠️ Insira a Chave OpenAI.")
        else:
            with st.spinner("🔄 Agente 1 coletando cenário (Investing/Forex) -> Agentes Especialistas analisando Price Action -> Coordenador definindo ordem..."):
                try:
                    import base64
                    image_bytes = arquivo_print.getvalue()
                    base64_image = base64.b64encode(image_bytes).decode('utf-8')
                    
                    client = OpenAI(api_key=api_key_input)
                    historico_recente = carregar_historico_15_dias()

                    prompt_sistema = f"""
                    Você é o sistema Coordenador Geral da matriz multi-agentes Matrix V6.
                    Ativo selecionado: {ativo_escolhido}
                    Horário atual em São Paulo: {agora_sp.strftime('%H:%M:%S')}.
                    Histórico de Loss Loop (erros recentes para calibração): {json.dumps(historico_recente[-10:], ensure_ascii=False)}
                    
                    A matriz opera com agentes em cadeia:
                    - AGENTE 1 (Scraper/Contexto): Mapeia o cenário macroeconômico atual para o ativo {ativo_escolhido}.
                    - AGENTES ESPECIALISTAS (Price Action e Indicadores): Analisam detalhadamente o print enviado (velas, tendência, suportes e resistências).
                    - COORDENADOR: Sintetiza os pareceres, calcula confluência e nível de confiança.
                    
                    REGRA ABSOLUTA: Você DEVE escolher obrigatoriamente uma única direção clara: estritamente "COMPRA" ou estritamente "VENDA". Nunca responda em cima do muro.
                    
                    Retorne estritamente um objeto JSON com esta estrutura exata:
                    {{
                      "parecer_agente1": "Resumo do cenário macroeconômico e fluxo do ativo.",
                      "parecer_especialistas": "Análise técnica detalhada das velas e tendência no print.",
                      "direcao": "COMPRA ou VENDA",
                      "confluencia": "Ex: 8.5 / 10",
                      "confianca": "Ex: 92%",
                      "tempo_grafico": "5M",
                      "analise_final": "Conclusão definitiva do Coordenador para a operação."
                    }}
                    """
                    
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt_sistema},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{base64_image}"
                                        }
                                    }
                                ]
                            }
                        ],
                        response_format={"type": "json_object"}
                    )
                    
                    dados_ia = json.loads(response.choices[0].message.content)
                    tf = dados_ia.get("tempo_grafico", "5M")
                    dados_ia["hora_exata"] = calcular_proxima_vela(agora_sp, tf)
                    
                    st.session_state.resultado_comite = dados_ia
                except Exception as e:
                    st.error(f"Erro na execução dos agentes: {e}")

# Exibição estruturada do Comitê de Agentes
if 'resultado_comite' in st.session_state:
    res = st.session_state.resultado_comite
    direcao = res.get("direcao", "NEUTRO").upper()
    
    st.divider()
    if "COMPRA" in direcao:
        st.success(f"🎯 DECISÃO DO COMITÊ: **{direcao}**")
    else:
        st.error(f"🎯 DECISÃO DO COMITÊ: **{direcao}**")
        
    st.write(f"🕒 **Horário Exato de Entrada:** `{res.get('hora_exata')}` ({res.get('tempo_grafico')})")
    st.write(f"⭐ **Confluência:** {res.get('confluencia')}  |  🔒 **Confiança:** {res.get('confianca')}")
    
    with st.expander("🕵️ Ver Relatórios Individuais dos Agentes"):
        st.markdown(f"🌐 **Agente 1 (Cenário / Investing):**\n{res.get('parecer_agente1')}")
        st.markdown(f"📈 **Agentes Especialistas (Price Action):**\n{res.get('parecer_especialistas')}")
    
    st.info(f"💡 **Parecer Final do Coordenador:** {res.get('analise_final')}")

st.divider()

# --- PLACAR E BOTÕES ---
st.caption(f"Placar: 🟢 {st.session_state.wins} X 🔴 {st.session_state.losses}")
col_win, col_loss = st.columns(2)

if col_win.button("✅ REGISTRAR WIN"):
    lucro = stake * (payout / 100.0)
    st.session_state.banca_atual += lucro
    st.session_state.lucro_liquido += lucro
    st.session_state.wins += 1
    salvar_memoria_historico("WIN", "Vitória validada pelo comitê.")
    st.rerun()

if col_loss.button("❌ REGISTRAR LOSS"):
    st.session_state.banca_atual -= stake
    st.session_state.lucro_liquido -= stake
    st.session_state.losses += 1
    salvar_memoria_historico("LOSS", "Loss registrado. Calibração aplicada ao Loss Loop.")
    st.rerun()

if st.session_state.lucro_liquido >= meta_lucro:
    st.success("🎯 Meta de Lucro Atingida!")
elif st.session_state.lucro_liquido <= -stop_loss:
    st.error("🛑 Stop Loss Atingido!")
