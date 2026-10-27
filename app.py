import streamlit as st
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from openai import OpenAI

st.set_page_config(page_title="Matrix V6 - Vision Pro", page_icon="🤖", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stButton>button { width: 100%; font-weight: bold; background-color: #007acc; color: white; border-radius: 4px; padding: 0.4rem; font-size: 14px; }
    h1 { font-size: 1.4rem !important; text-align: center; margin-bottom: 0px; }
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    </style>
""", unsafe_allow_html=True)

st.title("🤖 MATRIX V6 • VISION PRO")

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

# --- PAINEL COMPACTO ---
c1, c2, c3 = st.columns(3)
c1.metric("Banca", f"R${st.session_state.banca_atual:.1f}")
c2.metric("Lucro", f"R${st.session_state.lucro_liquido:+.1f}")
win_rate = (st.session_state.wins / total_trades * 100) if total_trades > 0 else 0.0
c3.metric("Win Rate", f"{win_rate:.0f}%")

st.divider()

# --- UPLOAD DE PRINT (ANÁLISE REAL DO GRÁFICO DA HEZILEX) ---
st.subheader("📸 Envie o Print do Gráfico")
st.caption("Tire o print na Hezilex e envie aqui. O GPT-4o Vision analisará a tendência real (Price Action).")

arquivo_print = st.file_uploader("Escolha a imagem do gráfico", type=["jpg", "jpeg", "png"])

agora_sp = datetime.now(ZoneInfo("America/Sao_Paulo"))

if arquivo_print is not None:
    st.image(arquivo_print, caption="Gráfico enviado para análise", use_container_width=True)
    
    if st.button("🔍 ANALISAR PRINT COM OS AGENTES"):
        if not api_key_input:
            st.error("⚠️ Insira a Chave OpenAI.")
        else:
            with st.spinner("Os agentes estão lendo a Price Action e o Loss Loop..."):
                try:
                    import base64
                    image_bytes = arquivo_print.getvalue()
                    base64_image = base64.b64encode(image_bytes).decode('utf-8')
                    
                    client = OpenAI(api_key=api_key_input)
                    historico_recente = carregar_historico_15_dias()

                    prompt_sistema = f"""
                    Você é o Coordenador Geral do sistema Matrix V6 de Opções Binárias.
                    O horário atual em São Paulo é {agora_sp.strftime('%H:%M:%S')}.
                    Histórico de erros recentes (Loss Loop para calibragem e correção): {json.dumps(historico_recente[-10:], ensure_ascii=False)}
                    
                    Analise rigorosamente a imagem do gráfico da Hezilex enviada pelo usuário. Identifique a tendência atual (baixa, alta ou consolidação), suporte/resistência e velas recentes.
                    Retorne estritamente um JSON com a seguinte estrutura:
                    {{
                      "direcao": "COMPRA ou VENDA",
                      "confianca": "Ex: 95%",
                      "tempo_grafico": "Ex: 5M",
                      "analise": "Explicação técnica detalhada baseada no que você vê na imagem (ex: forte tendência de baixa com rejeição em resistência)."
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
                    
                    st.session_state.resultado_visao = json.loads(response.choices[0].message.content)
                except Exception as e:
                    st.error(f"Erro na análise de visão: {e}")

# Exibição do Resultado da Análise Visual
if 'resultado_visao' in st.session_state:
    res = st.session_state.resultado_visao
    direcao = res.get("direcao", "NEUTRO")
    cor_box = "green" if direcao == "COMPRA" else "red"
    
    st.markdown(f"### 🎯 Recomendação: `{direcao}` ({res.get('confianca')})")
    st.info(f"⏱️ **Timeframe sugerido:** {res.get('tempo_grafico')}")
    st.warning(f"💡 **Parecer Técnico dos Agentes:** {res.get('analise')}")

st.divider()

# --- PLACAR E BOTÕES ---
st.caption(f"Placar: 🟢 {st.session_state.wins} X 🔴 {st.session_state.losses}")
col_win, col_loss = st.columns(2)

if col_win.button("✅ REGISTRAR WIN"):
    lucro = stake * (payout / 100.0)
    st.session_state.banca_atual += lucro
    st.session_state.lucro_liquido += lucro
    st.session_state.wins += 1
    salvar_memoria_historico("WIN", "Vitória validada com sucesso.")
    st.rerun()

if col_loss.button("❌ REGISTRAR LOSS"):
    st.session_state.banca_atual -= stake
    st.session_state.lucro_liquido -= stake
    st.session_state.losses += 1
    salvar_memoria_historico("LOSS", "Loss registrado. Matriz ajustada para evitar repetição.")
    st.rerun()

if st.session_state.lucro_liquido >= meta_lucro:
    st.success("🎯 Meta de Lucro Atingida!")
elif st.session_state.lucro_liquido <= -stop_loss:
    st.error("🛑 Stop Loss Atingido!")
