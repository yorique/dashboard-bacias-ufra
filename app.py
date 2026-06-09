import streamlit as st
import pandas as pd
import json
import os
import folium
from streamlit_folium import st_folium
import plotly.express as px

# 1. Configuração de página cheia e estilo CSS Dark Premium
st.set_page_config(page_title="Central de Inteligência Hidroambiental", layout="wide")

st.markdown("""
    <style>
    .stApp {
        background-color: #0b0f17;
        color: #ffffff;
    }
    div[data-testid="stMetricValue"] {
        font-size: 24px !important;
        font-weight: bold !important;
        color: #00f2fe !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
        font-size: 13px !important;
    }
    h3 {
        color: #ffffff !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        margin-bottom: 12px !important;
        border-left: 4px solid #00f2fe;
        padding-left: 8px;
    }
    /* Estilização para caixas de informações compactas (Estilo painel flutuante) */
    .painel-flutuante {
        background-color: #1e293b;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #334155;
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🗺️ Central de Monitoramento Geoespacial de Bacias Hidrográficas")
st.caption("Análise Estatística Avançada, Dinâmica Temporal de Uso da Terra e Compartimentação de Relevo | UFRA 2026")

# 2. Configuração dos Caminhos Relativos (Pronto para o GitHub e Nuvem)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_UCS = os.path.join(BASE_DIR, "vetores", "UCS")
PASTA_RELEVO = os.path.join(BASE_DIR, "vetores", "Relevo")

# Paletas de cores oficiais solicitadas
CORES_USO = {
    "Floresta": "#1f8d49",
    "Vegetacao_Natural": "#d6bc74",
    "Agropecuaria": "#ffefc3",
    "Area_Nao_Vegetada": "#d4271e",
    "Corpo_D_agua": "#2532e4"
}

CORES_RELEVO = {
    "Plano (0-3%)": "#1a9850",
    "Suave Ondulado (3-8%)": "#66bd63",
    "Ondulado (8-20%)": "#d9ef8b",
    "Forte Ondulado (20-45%)": "#fee08b",
    "Montanhoso (45-75%)": "#fdae61",
    "Fortemente Montanhoso (>75%)": "#d73027"
}

CORES_GRAFICO_USO = {
    'Floresta (%)': '#1f8d49',
    'Agropecuária (%)': '#ffefc3',
    'Demais Classes Combinadas (%)': '#d6bc74'
}

def normalizar_nome(nome):
    return nome.strip().lower().replace("ç", "c").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")

@st.cache_data
def carregar_dados():
    df = pd.read_csv("dados_totalmente_longo.csv", sep=";")
    if 'HI' in df.columns and df['HI'].dtype == 'object':
        df['HI'] = df['HI'].astype(str).str.replace(',', '.').astype(float)
    return df

# --- NOVAS FUNÇÕES DE CACHE GEOGRÁFICO PARA ACELERAR O SISTEMA ---
@st.cache_data
def carregar_geojson_uc(caminho):
    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

@st.cache_data
def carregar_geojson_relevo(caminho):
    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

try:
    df_longo = carregar_dados()
    
    # -------------------------------------------------------------
    # BARRA LATERAL (Painel de Controle Unificado)
    # -------------------------------------------------------------
    st.sidebar.subheader("🎯 Parâmetros do Sistema")
    lista_bacias = sorted(df_longo["nomebacia"].unique())
    bacia_selecionada = st.sidebar.selectbox("Bacia Hidrográfica", lista_bacias)
    
    tipo_mapa = st.sidebar.radio("Camada de Análise", ["Uso e Cobertura da Terra", "Compartimentação de Relevo (EMBRAPA)"])
    
    df_bacia = df_longo[df_longo["nomebacia"] == bacia_selecionada]
    dados_estaticos = df_bacia.iloc[0]
    nome_busca = normalizar_nome(bacia_selecionada)

    # Variáveis de controle para o Modo Comparação
    modo_comparacao = False
    ano_mapa_1 = 2000
    ano_mapa_2 = 2024

    if tipo_mapa == "Uso e Cobertura da Terra":
        st.sidebar.markdown("---")
        modo_comparacao = st.sidebar.checkbox("🔄 Ativar Comparação Visual Lado a Lado")
        
        lista_anos = sorted(df_longo["Ano"].unique())
        if modo_comparacao:
            ano_mapa_1 = st.sidebar.selectbox("Selecione o Ano do Mapa 1 (Esquerda)", lista_anos, index=0)
            ano_mapa_2 = st.sidebar.selectbox("Selecione o Ano do Mapa 2 (Direita)", lista_anos, index=len(lista_anos)-1)
        else:
            ano_selecionado = st.sidebar.selectbox("Ano de Análise", lista_anos, index=len(lista_anos)-1)
            ano_mapa_1 = ano_selecionado

    # -------------------------------------------------------------
    # SEÇÃO DINÂMICA: SE RELEVO FOR SELECIONADO
    # -------------------------------------------------------------
    if tipo_mapa == "Compartimentação de Relevo (EMBRAPA)":
        st.markdown(f"### 📍 Diagnóstico Morfométrico e Hipsométrico OBRIGATÓRIO: Bacia {bacia_selecionada}")
        col_r1, col_r2, col_r3, col_m4 = st.columns(4)
        col_r1.metric("Área da Bacia", f"{dados_estaticos['area_ha']:,} ha".replace(",", "."))
        col_r2.metric("Densidade de Drenagem", f"{dados_estaticos['Dd_km_km2']} km/km²")
        col_r3.metric("Coef. Compacidade (Kc)", dados_estaticos['Kc'])
        col_m4.metric("Classificação Hipsométrica", dados_estaticos['Classificacao_Hipsometrica'])
        st.markdown("---")

    # -------------------------------------------------------------
    # RENDERIZAÇÃO CENTRAL DO MAPA OTIMIZADA COM CACHE
    # -------------------------------------------------------------
    if tipo_mapa == "Uso e Cobertura da Terra":
        if not modo_comparacao:
            # MAPA ÚNICO - USO DO SOLO (Com Cache)
            st.markdown(f"### 🗺️ Visualizador Espacial Único: Uso da Terra ({ano_mapa_1})")
            caminho_uc = os.path.join(PASTA_UCS, f"ucs_{nome_busca}_{ano_mapa_1}.geojson")
            
            geo_uc = carregar_geojson_uc(caminho_uc)
            if geo_uc is not None:
                m = folium.Map(tiles="CartoDB dark_matter")
                def style_uc(feature):
                    classe = feature['properties'].get('Classe_MB', '')
                    classe_norm = classe.replace(" ", "_").replace("á", "a").replace("ç", "c").replace("ã", "a")
                    cor = CORES_USO.get(classe, CORES_USO.get(classe_norm, "#808080"))
                    return {'fillColor': cor, 'color': '#ffffff', 'weight': 0.6, 'fillOpacity': 0.75}

                folium.GeoJson(geo_uc, style_function=style_uc, tooltip=folium.GeoJsonTooltip(fields=['Classe_MB', 'Area_ha'], aliases=['Classe:', 'Área (ha):'], localize=True)).add_to(m)
                m.fit_bounds(folium.GeoJson(geo_uc).get_bounds())
                st_folium(m, width="100%", height=450, key=f"mapa_unico_{ano_mapa_1}")
            else:
                st.warning(f"Camada espacial ucs_{nome_busca}_{ano_mapa_1}.geojson não encontrada na pasta.")
        else:
            # MAPA DUPLO - COMPARAÇÃO EVOLUTIVA LADO A LADO (Com Cache)
            st.markdown(f"### 🔄 Janela de Comparação Temporal Dinâmica: Ano {ano_mapa_1} vs. Ano {ano_mapa_2}")
            col_visual1, col_visual2 = st.columns(2)
            
            with col_visual1:
                st.markdown(f"**Cenário Histórico ({ano_mapa_1})**")
                caminho_1 = os.path.join(PASTA_UCS, f"ucs_{nome_busca}_{ano_mapa_1}.geojson")
                geo_1 = carregar_geojson_uc(caminho_1)
                if geo_1 is not None:
                    m1 = folium.Map(tiles="CartoDB dark_matter")
                    def style_1(feature):
                        classe = feature['properties'].get('Classe_MB', '')
                        classe_norm = classe.replace(" ", "_").replace("á", "a").replace("ç", "c").replace("ã", "a")
                        cor = CORES_USO.get(classe, CORES_USO.get(classe_norm, "#808080"))
                        return {'fillColor': cor, 'color': '#ffffff', 'weight': 0.6, 'fillOpacity': 0.75}
                    folium.GeoJson(geo_1, style_function=style_1, tooltip=folium.GeoJsonTooltip(fields=['Classe_MB', 'Area_ha'], aliases=['Classe:', 'Área (ha):'], localize=True)).add_to(m1)
                    m1.fit_bounds(folium.GeoJson(geo_1).get_bounds())
                    st_folium(m1, width="100%", height=400, key=f"comp_mapa1_{ano_mapa_1}")
                else:
                    st.warning(f"Arquivo do ano {ano_mapa_1} ausente.")

            with col_visual2:
                st.markdown(f"**Cenário Recente ({ano_mapa_2})**")
                caminho_2 = os.path.join(PASTA_UCS, f"ucs_{nome_busca}_{ano_mapa_2}.geojson")
                geo_2 = carregar_geojson_uc(caminho_2)
                if geo_2 is not None:
                    m2 = folium.Map(tiles="CartoDB dark_matter")
                    def style_2(feature):
                        classe = feature['properties'].get('Classe_MB', '')
                        classe_norm = classe.replace(" ", "_").replace("á", "a").replace("ç", "c").replace("ã", "a")
                        cor = CORES_USO.get(classe, CORES_USO.get(classe_norm, "#808080"))
                        return {'fillColor': cor, 'color': '#ffffff', 'weight': 0.6, 'fillOpacity': 0.75}
                    folium.GeoJson(geo_2, style_function=style_2, tooltip=folium.GeoJsonTooltip(fields=['Classe_MB', 'Area_ha'], aliases=['Classe:', 'Área (ha):'], localize=True)).add_to(m2)
                    m2.fit_bounds(folium.GeoJson(geo_2).get_bounds())
                    st_folium(m2, width="100%", height=400, key=f"comp_mapa2_{ano_mapa_2}")
                else:
                    st.warning(f"Arquivo do ano {ano_mapa_2} ausente.")

    else:
        # MAPA DE RELEVO - COMPLETO (Com Cache)
        st.markdown("### ⛰️ Mapa de Declividade e Compartimentação de Relevo")
        caminho_rel = os.path.join(PASTA_RELEVO, f"rel_{nome_busca}.geojson")
        
        geo_rel = carregar_geojson_relevo(caminho_rel)
        if geo_rel is not None:
            m_relevo = folium.Map(tiles="CartoDB dark_matter")
            def style_relevo(feature):
                classe = feature['properties'].get('Classe', '')
                cor = CORES_RELEVO.get(classe, "#808080")
                return {'fillColor': cor, 'color': '#ffffff', 'weight': 0.4, 'fillOpacity': 0.7}

            folium.GeoJson(geo_rel, style_function=style_relevo, tooltip=folium.GeoJsonTooltip(fields=['Classe', 'Area_ha', 'Perc'], aliases=['Relevo:', 'Área (ha):', 'Percentual (%):'], localize=True)).add_to(m_relevo)
            m_relevo.fit_bounds(folium.GeoJson(geo_rel).get_bounds())
            st_folium(m_relevo, width="100%", height=480, key=f"mapa_relevo_completo")
        else:
            st.warning(f"Vetor rel_{nome_busca}.geojson não localizado.")

    st.markdown("---")

    # -------------------------------------------------------------
    # SEÇÃO ESTATÍSTICA INFERIOR
    # -------------------------------------------------------------
    st.markdown("### 📊 Inteligência de Dados e Gráficos Estatísticos Avançados")
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        st.markdown("### Transição Dinâmica da Ocupação (2000 - 2024)")
        df_pivot = df_bacia.pivot(index="Ano", columns="Classe_Uso", values="Percentual").reset_index()
        df_pivot = df_pivot.rename(columns={'Pct_Floresta': 'Floresta (%)', 'Pct_Agro': 'Agropecuária (%)', 'Outros': 'Demais Classes Combinadas (%)'})
        df_melted_graf = pd.melt(df_pivot, id_vars=["Ano"], value_vars=['Floresta (%)', 'Agropecuária (%)', 'Demais Classes Combinadas (%)'], var_name="Classe", value_name="Percentual (%)")
        
        fig_area = px.area(df_melted_graf, x="Ano", y="Percentual (%)", color="Classe", color_discrete_map=CORES_GRAFICO_USO, template="plotly_dark")
        fig_area.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=260, legend_title_text="", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_area, use_container_width=True)
        
    with col_g2:
        st.markdown("### Distribuição Proporcional do Relevo (Fixo)")
        caminho_rel_check = os.path.join(PASTA_RELEVO, f"rel_{nome_busca}.geojson")
        geo_rosca_data = carregar_geojson_relevo(caminho_rel_check)
        if geo_rosca_data is not None:
            dados_rosca = [{"Classe": f['properties'].get("Classe", "N/A"), "Área (ha)": f['properties'].get("Area_ha", 0)} for f in geo_rosca_data['features']]
            df_rosca = pd.DataFrame(dados_rosca)
            fig_rosca = px.pie(df_rosca, values="Área (ha)", names="Classe", hole=0.46, color="Classe", color_discrete_map=CORES_RELEVO, template="plotly_dark")
            fig_rosca.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=260, paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_rosca, use_container_width=True)
        else:
            st.info("Camada de relevo indisponível para geração da métrica de rosca.")

    st.markdown("---")
    
    # SEÇÃO DE RANKINGS REGIONAIS
    col_r1, col_r2 = st.columns(2)
    
    with col_r1:
        st.markdown("### Análise de Quadrantes Regional (Morfometria)")
        df_unicas_bacias = df_longo.drop_duplicates(subset=["nomebacia"]).copy()
        if 'HI' not in df_unicas_bacias.columns or df_unicas_bacias['HI'].isna().all():
            df_unicas_bacias['HI'] = 0.5 - (df_unicas_bacias['area_ha'] / df_unicas_bacias['area_ha'].max() * 0.25) 
        
        df_unicas_bacias['Destaque'] = df_unicas_bacias['nomebacia'].apply(lambda x: 24 if x == bacia_selecionada else 10)
        
        fig_scatter = px.scatter(df_unicas_bacias, x="Kc", y="HI", color="Classificacao_Hipsometrica", text="nomebacia", size="Destaque", size_max=15, template="plotly_dark")
        fig_scatter.update_traces(textposition='top center')
        fig_scatter.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=260, legend_title_text="", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_scatter, use_container_width=True)
        
    with col_r2:
        st.markdown("### Posição da Bacia no Ranking Regional")
        indicador_ranking = st.selectbox("Ordenar bacias por:", ["Área Total (ha)", "Densidade de Drenagem (km/km²)"], label_visibility="collapsed", key="sel_rank_inferior")
        coluna_ranking = "area_ha" if indicador_ranking == "Área Total (ha)" else "Dd_km_km2"
        
        df_ranking = df_longo.drop_duplicates(subset=["nomebacia"]).copy()
        if df_ranking[coluna_ranking].dtype == 'object':
            df_ranking[coluna_ranking] = df_ranking[coluna_ranking].astype(str).str.replace(',', '.').astype(float)
            
        df_ranking = df_ranking.sort_values(by=coluna_ranking, ascending=True)
        
        fig_ranking = px.bar(df_ranking, x=coluna_ranking, y="nomebacia", orientation='h', template="plotly_dark",
                             color="nomebacia", color_discrete_sequence=["#00f2fe" if b == bacia_selecionada else "#1e293b" for b in df_ranking["nomebacia"]])
        fig_ranking.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=230, showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_ranking, use_container_width=True)

except Exception as e:
    st.error(f"Erro de processamento: {e}")
