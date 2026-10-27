import streamlit as st
import json
import os
from datetime import datetime, timedelta
from openai import OpenAI

st.set_page_config(page_title="Matrix V6 - Coordenador Cloud", page_icon="🤖", layout="centered")

# Estilo Trader Profissional
st.markdown("""
    <style>
    .main { background-color: #121212; color: #ffffff; }
    .stButton>button { width: 100%; font-weight: bold; background-color: #007acc; color: white; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

st.title("🤖 MATRIX V6 • NUVEM ATIVA")
st.write("Painel Inteligente e Seguro (Modelo Lado a Lado / Upload de Print)")

# --- CONFIGURAÇÕES NA BARRA LATERAL ---
st.sidebar.header("⚙️ Configurações & Risco")
api_key_input = st.sidebar.text_input("Sua Chave OpenAI (API Key)", type="password")

banca_inicial = st.sidebar.number_input("Banca Inicial (R$)", value=500.0, step=10.0)
stake = st.sidebar.number_input("Valor da Entrada / Stake (R$)", value=5.0, step=1.0)
payout = st.sidebar.number_input("Payout do Ativo (%)", value=82.0, step=1.0)
meta_lucro = st.sidebar.number_input("Meta de Lucro da Sessão (R$)", value=50.0, step=5.0)
stop_loss = st.sidebar.number_input("Stop Loss da Sessão (R$)", value=30.0, step=5.0)

# Inicializa o estado da sessão no navegador
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

# --- UPLOAD DO PRINT DO GRÁFICO (PC ou Celular) ---
st.subheader("📷 Envie o Print do Gráfico (Hezilex)")
uploaded_file = st.file_uploader("Cole o print rápido do PC ou envie a foto do celular", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    st.image(uploaded_file, caption="Gráfico em análise", use_column_width=True)
    
    if st.button("🚀 EXECUTAR ANÁLISE COM OS AGENTES (IA)"):
        if not api_key_input:
            st.error("⚠️ Por favor, insira sua Chave da OpenAI na barra lateral esquerda.")
        else:
            with st.spinner("🤖 Os 4 agentes e o Coordenador estão cruzando os dados com o histórico de 15 dias..."):
                try:
                    client = OpenAI(api_key=api_key_input)
                    import base64
                    bytes_data = uploaded_file.getvalue()
                    imagem_base64 = base64.b64encode(bytes_data).decode("utf-8")
                    
                    historico_recente = carregar_historico_15_dias()

                    prompt_sistema = f"""
                    Você é o Coordenador Geral do sistema Matrix V6 (Agente Fundamentalista, TrendAgent, VolatilityAgent, MathAgent).
                    Aqui está o histórico acumulado dos últimos 15 dias de operações para aprendizado contínuo (Loss Loop):
                    {json.dumps(historico_recente[-10:], ensure_ascii=False)} 
                    
                    Analise o print do gráfico fornecido considerando este histórico de acertos e erros passados.
                    
                    DIRETRIZES:
                    1. Verifique se há oportunidade clara para a próxima vela.
                    2. Se o mercado estiver perigoso ou sem padrão, retorne "operacao_possivel": false.
                    3. Se houver operação, retorne "operacao_possivel": true e preencha rigidamente:
                       - "hora_exata": Hora exata sugerida para a entrada no nascimento da próxima vela (ex: "14:35:00").
                       - "direcao": Apenas "COMPRA" ou "VENDA" (Proibido neutro).
                       - "confluencia": Número de 0 a 10 (ex: 8.5).
                       - "confianca": Porcentagem (ex: "92%").
                    Retorne estritamente em JSON.
                    """
                    
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": prompt_sistema},
                            {"role": "user", "content": [{"type": "text", "text": "Analise este gráfico."}, {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{imagem_base64}"}}]}
                        ],
                        response_format={"type": "json_object"}
                    )
                    
                    res_json = json.loads(response.choices[0].message.content)
                    st.session_state.ultima_analise = res_json
                except Exception as e:
                    st.error(f"Erro ao conectar com a OpenAI: {e}")

# --- OS 4 QUADRANTES DE DECISÃO ---
st.subheader("🔲 Quadrantes de Decisão (Matrix V6)")
if 'ultima_analise' in st.session_state:
    res = st.session_state.ultima_analise
    if not res.get("operacao_possivel", False):
        st.warning("⚠️ O mercado está sem padrão claro ou perigoso. *Nenhuma operação recomendada no momento.*")
    else:
        q1, q2 = st.columns(2)
        q1.info(f"*Q1 [ Hora Exata ]*\n\n🕒 {res.get('hora_exata')} (Próxima Vela)")
        q2.success(f"*Q2 [ Direção ]*\n\n📈 {res.get('direcao')}")
        
        q3, q4 = st.columns(2)
        q3.warning(f"*Q3 [ Confluência ]*\n\n⭐ {res.get('confluencia')} / 10")
        q4.error(f"*Q4 [ Confiança ]*\n\n🎯 {res.get('confianca')}")
else:
    st.info("Aguardando envio do gráfico para preencher os quadrantes...")

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
    st.success("🎯 *META DE LUCRO ATINGIDA!* Feche o dia com lucro!")
elif st.session_state.lucro_liquido <= -stop_loss:
    st.error("🛑 *STOP LOSS ATINGIDO!* Proteja sua banca e encerre por hoje.")
