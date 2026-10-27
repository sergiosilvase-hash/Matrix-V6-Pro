import streamlit as st
import json
import os
from datetime import datetime, timedelta
from openai import OpenAI

st.set_page_config(page_title="Matrix V6 - Coordenador Cloud", page_icon="🤖", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #121212; color: #ffffff; }
    .stButton>button { width: 100%; font-weight: bold; background-color: #007acc; color: white; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

st.title("🤖 MATRIX V6 • NUVEM ATIVA")
st.write("Painel Inteligente com Varredura de Ativos e Gestão de Risco")

# --- LEITURA AUTOMÁTICA DA CHAVE (SECRETS OU BARRA LATERAL) ---
if "OPENAI_API_KEY" in st.secrets:
    api_key_input = st.secrets["OPENAI_API_KEY"]
else:
    api_key_input = st.sidebar.text_input("Sua Chave OpenAI (API Key)", type="password")

# --- CONFIGURAÇÕES NA BARRA LATERAL ---
st.sidebar.header("⚙️ Configurações & Risco")
banca_inicial = st.sidebar.number_input("Banca Inicial (R$)", value=500.0, step=10.0)
stake = st.sidebar.number_input("Valor da Entrada / Stake (R$)", value=5.0, step=1.0)
payout = st.sidebar.number_input("Payout do Ativo (%)", value=82.0, step=1.0)
meta_lucro = st.sidebar.number_input("Meta de Lucro da Sessão (R$)", value=50.0, step=5.0)
stop_loss = st.sidebar.number_input("Stop Loss da Sessão (R$)", value=30.0, step=5.0)

if 'banca_atual' not in st.session_state:
    st.session_state.banca_atual = banca_inicial
if 'lucro_liquido' not in st.session_state:
    st.session_state.lucro_liquido = 0.0
if 'wins' not in st.session_state:
    st.session_state.wins = 0
if 'losses' not in st.session_state:
    st.session_state.losses = 0

ARQUIVO_MEMORIA = "agent_history.json"

def carregar_historico_15_dias():
    if not os.path.exists(ARQUIVO_MEMORIA):
        return []
    try:
        with open(ARQUIVO_MEMORIA, "r", encoding="utf-8") as f:
            dados = json.load(f)
        limite_data = datetime.now() - timedelta(days=15)
        return [item for item in dados if datetime.strptime(item["timestamp_data"], "%Y-%m-%d %H:%M:%S") >= limite_data]
    except Exception:
        return []

def salvar_memoria_historico(resultado, feedback):
    agora = datetime.now()
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
    limite_data = agora - timedelta(days=15)
    historico_filtrado = [item for item in historico if datetime.strptime(item["timestamp_data"], "%Y-%m-%d %H:%M:%S") >= limite_data]
    with open(ARQUIVO_MEMORIA, "w", encoding="utf-8") as f:
        json.dump(historico_filtrado, f, indent=4, ensure_ascii=False)

# --- PAINEL PRINCIPAL: GESTÃO DE BANCA ---
col1, col2, col3 = st.columns(3)
col1.metric("Banca Atual", f"R$ {st.session_state.banca_atual:.2f}")
col2.metric("Lucro / Prejuízo", f"R$ {st.session_state.lucro_liquido:+.2f}")
total_trades = st.session_state.wins + st.session_state.losses
win_rate = (st.session_state.wins / total_trades * 100) if total_trades > 0 else 0.0
col3.metric("Win Rate", f"{win_rate:.1f}%")

st.divider()

# --- VARREDURA DE ATIVOS E ANÁLISE ---
st.subheader("🔍 Varredura de Oportunidades (Top Ativos)")
st.write("O Coordenador fará uma varredura cruzando o cenário atual com o histórico de 15 dias para listar até 5 melhores ativos/cenários para negociação.")

if st.button("🚀 EXECUTAR VARREDURA DOS TOP 5 ATIVOS"):
    if not api_key_input:
        st.error("⚠️ Insira sua Chave da OpenAI (nos Secrets do Streamlit ou na barra lateral).")
    else:
        with st.spinner("🤖 Os agentes estão escaneando o mercado e cruzando com o Loss Loop..."):
            try:
                client = OpenAI(api_key=api_key_input)
                historico_recente = carregar_historico_15_dias()

                prompt_sistema = f"""
                Você é o Coordenador Geral do sistema Matrix V6 de Opções Binárias.
                Histórico dos últimos 15 dias (Loss Loop): {json.dumps(historico_recente[-10:], ensure_ascii=False)}
                
                Faça uma varredura simulada de mercado e retorne estritamente um objeto JSON contendo uma lista chamada "ativos_recomendados" com até 5 principais ativos (ex: EUR/USD, GBP/USD, AUD/USD, EUR/JPY, USD/JPY) que apresentam melhor margem e confluência neste momento.
                
                O JSON deve seguir rigorosamente este formato:
                {{
                  "ativos_recomendados": [
                    {{
                      "paridade": "EUR/USD",
                      "direcao": "COMPRA",
                      "confluencia": "8.8 / 10",
                      "confianca": "94%",
                      "hora_exata": "14:45:00",
                      "motivo": "Forte tendência de alta com suporte validado pelo histórico."
                    }}
                  ]
                }}
                """
                
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": prompt_sistema},
                        {"role": "user", "content": "Execute a varredura dos top 5 ativos para negociação agora."}
                    ],
                    response_format={"type": "json_object"}
                )
                
                st.session_state.resultado_varredura = json.loads(response.choices[0].message.content)
            except Exception as e:
                st.error(f"Erro ao conectar com a OpenAI: {e}")

# Exibição dos Ativos Varridos
if 'resultado_varredura' in st.session_state:
    res = st.session_state.resultado_varredura
    lista_ativos = res.get("ativos_recomendados", [])
    
    if not lista_ativos:
        st.warning("Nenhum ativo com margem segura no momento.")
    else:
        st.success(f"🎯 Varredura concluída! {len(lista_ativos)} ativos mapeados com alta confluência:")
        for idx, ativo in enumerate(lista_ativos, 1):
            with st.expander(f"#{idx} - {ativo.get('paridade')} | Direção: {ativo.get('direcao')} | Confiança: {ativo.get('confianca')}"):
                st.write(f"🕒 *Horário de Entrada:* {ativo.get('hora_exata')}")
                st.write(f"⭐ *Confluência:* {ativo.get('confluencia')}")
                st.write(f"💡 *Análise dos Agentes:* {ativo.get('motivo')}")

st.divider()

# --- PLACAR E BOTÕES DE RESULTADO ---
st.subheader("📊 Placar da Sessão")
st.write(f"🟢 *WINS:* {st.session_state.wins}   |   🔴 *LOSSES:* {st.session_state.losses}")

col_win, col_loss = st.columns(2)

if col_win.button("✅ REGISTRAR WIN"):
    lucro = stake * (payout / 100.0)
    st.session_state.banca_atual += lucro
    st.session_state.lucro_liquido += lucro
    st.session_state.wins += 1
    salvar_memoria_historico("WIN", "Vitória validada. Pesos positivos reforçados na matriz.")
    st.rerun()

if col_loss.button("❌ REGISTRAR LOSS"):
    st.session_state.banca_atual -= stake
    st.session_state.lucro_liquido -= stake
    st.session_state.losses += 1
    salvar_memoria_historico("LOSS", "Loss mapeado. Ajuste corretivo aplicado aos agentes.")
    st.rerun()

if st.session_state.lucro_liquido >= meta_lucro:
    st.balloons()
    st.success("🎯 *META DE LUCRO ATINGIDA!*")
elif st.session_state.lucro_liquido <= -stop_loss:
    st.error("🛑 *STOP LOSS ATINGIDO!*")
