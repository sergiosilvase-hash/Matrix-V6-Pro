import streamlit as st
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from openai import OpenAI

st.set_page_config(page_title="Matrix V6 - Cripto Pro", page_icon="🤖", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stButton>button { width: 100%; font-weight: bold; background-color: #007acc; color: white; border-radius: 4px; padding: 0.4rem; font-size: 14px; }
    h1 { font-size: 1.4rem !important; text-align: center; margin-bottom: 0px; }
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    </style>
""", unsafe_allow_html=True)

st.title("🤖 MATRIX V6 • CRIPTO PRO (HEZILEX)")

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
    with open(ARQUIVO_MEMORIA, "w", encoding="utf-8") as f:
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

# --- VARREDURA DE CRIPTOATIVOS ---
st.subheader("🔍 Varredura Top 5 Cripto (Hezilex / Binance)")
agora_sp = datetime.now(ZoneInfo("America/Sao_Paulo"))
st.caption(f"🕒 Relógio SP: **{agora_sp.strftime('%H:%M:%S')}**")

if st.button("🚀 EXECUTAR VARREDURA DOS TOP 5 CRIPTO"):
    if not api_key_input:
        st.error("⚠️ Insira a Chave OpenAI.")
    else:
        with st.spinner("🤖 Analisando o fluxo de criptoativos e cruzando com o histórico..."):
            try:
                client = OpenAI(api_key=api_key_input)
                historico_recente = carregar_historico_15_dias()

                prompt_sistema = f"""
                Você é o Coordenador Geral do sistema Matrix V6 especializado em Opções Binárias de Criptomoedas.
                O horário atual em São Paulo é {agora_sp.strftime('%H:%M:%S')}.
                Histórico de Loss Loop (calibração): {json.dumps(historico_recente[-10:], ensure_ascii=False)}
                
                Faça uma varredura considerando os principais criptoativos operados na Hezilex (como Bitcoin, Litecoin, Cardano, BNB, XRP, Ethereum, Solana, AVAX, DOGE, SUI, LINK).
                Selecione os **Top 5 ativos** que apresentam as melhores margens e tendências neste momento.
                
                Para cada ativo, defina obrigatoriamente:
                1. "paridade": Nome do ativo (Ex: "Bitcoin", "Cardano", "Solana", etc.)
                2. "tempo_grafico": "1M", "5M" ou "15M"
                3. "direcao": Estritamente "COMPRA" ou "VENDA" (proibido termos ambíguos)
                4. "confluencia": Ex: "8.5 / 10"
                5. "confianca": Ex: "92%"
                6. "motivo": Justificativa técnica baseada na volatilidade e momento do criptoativo.
                
                Retorne estritamente um objeto JSON com uma lista chamada "ativos_recomendados".
                """
                
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": prompt_sistema},
                        {"role": "user", "content": "Gere os Top 5 criptoativos com melhor margem agora."}
                    ],
                    response_format={"type": "json_object"}
                )
                
                dados_ia = json.loads(response.choices[0].message.content)
                for ativo in dados_ia.get("ativos_recomendados", []):
                    tf = ativo.get("tempo_grafico", "5M")
                    ativo["hora_exata"] = calcular_proxima_vela(agora_sp, tf)
                
                st.session_state.resultado_varredura_cripto = dados_ia
            except Exception as e:
                st.error(f"Erro na varredura: {e}")

# Exibição dos Ativos Varridos
if 'resultado_varredura_cripto' in st.session_state:
    res = st.session_state.resultado_varredura_cripto
    lista_ativos = res.get("ativos_recomendados", [])
    
    if not lista_ativos:
        st.warning("Nenhum ativo ideal no momento.")
    else:
        st.success(f"🎯 Varredura concluída! {len(lista_ativos)} criptoativos mapeados:")
        for idx, ativo in enumerate(lista_ativos, 1):
            direcao = ativo.get('direcao', 'NEUTRO').upper()
            cor_emoji = "🟢" if "COMPRA" in direcao else "🔴"
            
            with st.expander(f"#{idx} - {ativo.get('paridade')} | ⏱️ {ativo.get('tempo_grafico')} | {cor_emoji} {direcao} ({ativo.get('confianca')})"):
                st.markdown(f"🕒 **Horário Exato de Entrada:** `{ativo.get('hora_exata')}`")
                st.markdown(f"⭐ **Confluência:** {ativo.get('confluencia')}  |  🔒 **Confiança:** {ativo.get('confianca')}")
                st.markdown(f"💡 **Análise dos Agentes:** {ativo.get('motivo')}")

st.divider()

# --- PLACAR E BOTÕES ---
st.caption(f"Placar: 🟢 {st.session_state.wins} X 🔴 {st.session_state.losses}")
col_win, col_loss = st.columns(2)

if col_win.button("✅ REGISTRAR WIN"):
    lucro = stake * (payout / 100.0)
    st.session_state.banca_atual += lucro
    st.session_state.lucro_liquido += lucro
    st.session_state.wins += 1
    salvar_memoria_historico("WIN", "Vitória validada.")
    st.rerun()

if col_loss.button("❌ REGISTRAR LOSS"):
    st.session_state.banca_atual -= stake
    st.session_state.lucro_liquido -= stake
    st.session_state.losses += 1
    salvar_memoria_historico("LOSS", "Loss registrado. Calibrando agentes.")
    st.rerun()

if st.session_state.lucro_liquido >= meta_lucro:
    st.success("🎯 Meta de Lucro Atingida!")
elif st.session_state.lucro_liquido <= -stop_loss:
    st.error("🛑 Stop Loss Atingido!")
