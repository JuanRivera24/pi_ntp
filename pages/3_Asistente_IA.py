import streamlit as st
import pandas as pd
from data_manager import obtener_vista_citas_completa
from report_generator import generar_pdf_reporte
import google.generativeai as genai
import traceback
from io import StringIO
import sys
from PIL import Image

# --- Configuración de la Página ---
st.set_page_config(page_title="Asistente IA", page_icon="🤖", layout="wide")
st.title("🤖 Asistente de Inteligencia Artificial")
st.markdown("Tu centro de mando para análisis avanzados, reportes y marketing inteligente.")

# --- Cargar y cachear los datos desde la API ---
@st.cache_data
def cargar_datos():
    return obtener_vista_citas_completa()

df_citas_completa = cargar_datos()

if df_citas_completa.empty:
    st.error("No se pudieron cargar los datos desde la API. Asegúrate de que la API (index.js) esté corriendo.")
    st.stop()

# --- Conexión al API de Gemini con el modelo correcto ---
model = None
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    # --- LA SOLUCIÓN DEFINITIVA: Usamos un nombre de la lista que nos dio el diagnóstico ---
    model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
except Exception as e:
    st.error(f"No se pudo configurar la conexión con Google Gemini. Verifica tu API Key. Error: {e}")

# --- Función para generar análisis de reportes ---
def generar_analisis_ia_con_gemini(datos_filtrados_str):
    if not model: return "El modelo de IA no está disponible."
    try:
        prompt = f"""
Actúa como un analista de datos y estratega de negocios experto para la cadena de barberías, Kingdom Barber.
A continuación, tu análisis debe basarse en esta lista de objetos.
Datos: {datos_filtrados_str}

Proporciona un análisis siguiendo esta estructura exacta:
1. **Resumen Ejecutivo:** Un buen párrafo con los 2 hallazgos más importantes basado en los filtros aplicados. Cuantifica el hallazgo principal (ej. "el 60% de los ingresos...").
2. **Observaciones Clave:** De 3 a 5 puntos. Cada punto DEBE estar respaldado por cifras, porcentajes o datos específicos del texto proporcionado.
3. **Recomendaciones Estratégicas:** De 2 a 3 acciones concretas. Cada recomendación DEBE derivar lógicamente de una de las observaciones anteriores.

El tono debe ser profesional y orientado a la acción. Basa el 100% de tu análisis estrictamente en los datos proporcionados y filtrados. No inventes información, eres profesional.
"""
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        traceback.print_exc()
        return "No se pudo generar el análisis debido a un error de conexión con la IA."

# --- Barra Lateral de Filtros ---
with st.sidebar:
    st.header("Filtros para el Reporte")
    df_citas_completa['Fecha'] = pd.to_datetime(df_citas_completa['Fecha'], errors='coerce')
    sedes_disponibles = ["Todas"] + df_citas_completa['Nombre_Sede'].dropna().unique().tolist()
    sede_seleccionada = st.selectbox("Selecciona una Sede", sedes_disponibles)
    fechas_validas = df_citas_completa['Fecha'].dropna()
    min_date = fechas_validas.min().date() if not fechas_validas.empty else pd.Timestamp.now().date()
    max_date = fechas_validas.max().date() if not fechas_validas.empty else pd.Timestamp.now().date()
    if min_date > max_date: min_date = max_date
    rango_fechas = st.date_input("Selecciona un Rango de Fechas", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    barberos_disponibles = ["Todos"] + sorted(df_citas_completa['Nombre_Completo_Barbero'].dropna().unique().tolist())
    barbero_seleccionado = st.selectbox("Selecciona un Barbero", barberos_disponibles)
    servicios_disponibles = ["Todos"] + sorted(df_citas_completa['Nombre_Servicio'].dropna().unique().tolist())
    servicio_seleccionado = st.selectbox("Selecciona un Servicio", servicios_disponibles)

# --- Aplicar filtros a los datos ---
df_filtrado = df_citas_completa.copy()
if sede_seleccionada != "Todas": df_filtrado = df_filtrado[df_filtrado['Nombre_Sede'] == sede_seleccionada]
if len(rango_fechas) == 2:
    fecha_inicio, fecha_fin = pd.to_datetime(rango_fechas[0]), pd.to_datetime(rango_fechas[1])
    df_filtrado = df_filtrado.dropna(subset=['Fecha'])
    df_filtrado = df_filtrado[(df_filtrado['Fecha'] >= fecha_inicio) & (df_filtrado['Fecha'] <= fecha_fin)]
if barbero_seleccionado != "Todos": df_filtrado = df_filtrado[df_filtrado['Nombre_Completo_Barbero'] == barbero_seleccionado]
if servicio_seleccionado != "Todos": df_filtrado = df_filtrado[df_filtrado['Nombre_Servicio'] == servicio_seleccionado]

# --- Interfaz Principal con Pestañas ---
tab_reportes, tab_analista, tab_marketing, tab_oportunidades, tab_asesor = st.tabs([
    "📈 Generador de Reportes", "🕵️ Analista de Datos Interactivo", "🎯 Asistente de Marketing",
    "💎 Detector de Oportunidades", "✂️ Asesor de Estilo Virtual"
])

with tab_reportes:
    st.header("Generador de Reportes a Medida")
    st.markdown("Selecciona los filtros y haz clic en el botón para generar un reporte en PDF con análisis de IA.")
    if st.button("🚀 Generar Reporte PDF"):
        if df_filtrado.empty:
            st.warning("No hay datos para los filtros seleccionados.")
        else:
            with st.spinner("Preparando datos y consultando a la IA... 🤖"):
                analisis_ia = generar_analisis_ia_con_gemini(df_filtrado.head(50).to_string())
            with st.spinner("Creando el archivo PDF... 📄"):
                contexto_reporte = {"sede": sede_seleccionada, "rango_fechas": f"{rango_fechas[0].strftime('%d/%m/%Y')} - {rango_fechas[1].strftime('%d/%m/%Y')}", "barbero": barbero_seleccionado, "servicio": servicio_seleccionado}
                pdf_bytes = generar_pdf_reporte(df_filtrado, analisis_ia, contexto_reporte)
            st.success("¡Reporte generado con éxito!")
            st.download_button(label="📥 Descargar Reporte PDF", data=pdf_bytes, file_name=f"Reporte_{sede_seleccionada.replace(' ', '_')}.pdf", mime="application/pdf")

with tab_analista:
    # (El resto de las pestañas no requieren cambios, sus prompts ya estaban mejorados)
    st.header("🕵️ Chatea con tus Datos")
    st.info(f"Tengo acceso a las **{len(df_filtrado)} citas** que coinciden con tus filtros. Hazme cualquier pregunta y generaré el código para encontrar la respuesta.")
    pregunta_usuario = st.text_input("Escribe tu pregunta aquí:", placeholder="Ej: ¿Cuál es el servicio que generó menos ingresos?")
    if st.button("🤖 Analizar y Responder"):
        if not model: st.error("No puedo conectarme con mi motor de IA.")
        elif not pregunta_usuario: st.warning("Por favor, escribe una pregunta.")
        elif df_filtrado.empty: st.warning("No hay datos disponibles para los filtros seleccionados.")
        else:
            with st.spinner("Generando plan de análisis... 🧠"):
                columnas = df_filtrado.columns.tolist()
                tipos_de_datos = df_filtrado.dtypes.to_string()
                prompt_agente = f"""
                Actúa comoun Agente de IA experto en análisis de datos con Pandas.
                Tu objetivo es generar un script de Python para responder la pregunta del usuario analizando un DataFrame llamado `df`.
                
                **Contexto del DataFrame `df`:**
                - Contiene datos de citas de una barbería.
                - 'Precio' representa ingresos.
                - 'Fecha' es crucial para análisis de tiempo.
                - 'Nombre_Completo_Barbero' y 'Nombre_Completo_Cliente' identifican a las personas.

                **Reglas Estrictas:**
                1.  **SOLO CÓDIGO:** Tu única respuesta debe ser un bloque de código Python. No incluyas explicaciones, solo el código.
                2.  **USA `df`:** El DataFrame a analizar SIEMPRE se llama `df`.
                3.  **CÓDIGO CLARO:** Añade comentarios breves en el código para explicar los pasos.
                4.  **IMPRIME EL RESULTADO:** El código DEBE terminar con una línea `print(resultado)` que muestre la respuesta final de forma clara.

                **Información del DataFrame disponible:**
                - COLUMNAS: {columnas}
                - TIPOS DE DATOS: {tipos_de_datos}

                **Pregunta del Usuario a Responder:**
                "{pregunta_usuario}"
                """
                try:
                    respuesta_ia = model.generate_content(prompt_agente)
                    codigo_generado = respuesta_ia.text.strip().replace("```python", "").replace("```", "")
                    with st.expander("🔍 Ver el Plan de Análisis (código generado)"):
                        st.code(codigo_generado, language='python')
                    with st.spinner("Ejecutando el análisis... ⚙️"):
                        df = df_filtrado
                        old_stdout, sys.stdout = sys.stdout, StringIO()
                        exec(codigo_generado, {'pd': pd, 'df': df})
                        resultado_analisis = sys.stdout.getvalue()
                        sys.stdout = old_stdout
                    with st.spinner("Interpretando los resultados... 🗣️"):
                        prompt_interprete = f"""
                        Eres "Alex", un asistente de datos amigable. Responde la pregunta del usuario de forma clara y directa, basándote en el resultado del análisis.
                        
                        **Pregunta Original del Usuario:**
                        "{pregunta_usuario}"
                        
                        **Resultado del Código (Datos Crudos):**
                        ---
                        {resultado_analisis}
                        ---
                        
                        **Tu Respuesta Final:**
                        Empieza con una respuesta directa. Luego, si es apropiado, añade un breve contexto o explicación.
                        """
                        respuesta_final_ia = model.generate_content(prompt_interprete)
                        st.markdown("### 💡 Aquí está tu análisis:")
                        st.success(respuesta_final_ia.text)
                except Exception as e:
                    st.error("¡Oops! Ocurrió un error al procesar tu pregunta.")
                    st.exception(e)

with tab_marketing:
    st.header("🎯 Asistente de Marketing Inteligente")
    st.markdown("Genera ideas y borradores para tus campañas de marketing basados en los datos.")
    col1, col2 = st.columns(2)
    with col1:
        tipo_campaña = st.selectbox("Selecciona el objetivo de la campaña:", ["Atraer nuevos clientes", "Fidelizar clientes existentes", "Promocionar un servicio poco popular", "Aumentar citas en días flojos"])
    with col2:
        canal_comunicacion = st.radio("Selecciona el canal:", ("WhatsApp", "Email", "Redes Sociales"), horizontal=True)
    if st.button("💡 Generar Idea de Campaña"):
        if not model: st.error("El modelo de IA no está disponible.")
        elif df_filtrado.empty: st.warning("No hay suficientes datos para generar una idea.")
        else:
            with st.spinner("Creando una campaña brillante... ✨"):
                try:
                    servicio_menos_popular = df_filtrado['Nombre_Servicio'].value_counts().idxmin()
                    dia_mas_flojo = df_filtrado['Fecha'].dt.day_name().value_counts().idxmin()
                except Exception:
                    servicio_menos_popular, dia_mas_flojo = "N/A", "N/A"
                prompt_marketing = f"""
                Actúa como un Director Creativo y Estratega de Marketing para la barbería 'Kingdom Barber'.
                Tu tarea es crear un borrador para una campaña de marketing.
                
                **INPUTS ESTRATÉGICOS:**
                - **Objetivo Principal:** {tipo_campaña}
                - **Canal de Difusión:** {canal_comunicacion}
                - **Insight de Datos 1 (Servicio a Potenciar):** {servicio_menos_popular}
                - **Insight de Datos 2 (Día de Baja Afluencia):** {dia_mas_flojo}

                **OUTPUT REQUERIDO (Formato Markdown):**
                Usa un tono creativo, masculino y directo.
                
                ###  Nombre de la Campaña
                - **Slogan:** Un eslogan corto y pegadizo.
                - **Público Objetivo:** ¿A quién nos dirigimos principalmente?
                - **Mensaje para {canal_comunicacion}:** Escribe el texto exacto para el post, email o mensaje de WhatsApp. Debe ser conciso y persuasivo.
                - **Llamada a la Acción (CTA):** ¿Qué queremos que haga el cliente?
                - **Sugerencia Creativa:** Una idea adicional (ej. un hashtag, tipo de imagen, colaboración).
                """
                try:
                    respuesta_ia = model.generate_content(prompt_marketing)
                    st.markdown(respuesta_ia.text)
                except Exception as e:
                    st.error(f"Ocurrió un error al generar la campaña: {e}")

with tab_oportunidades:
    st.header("💎 Detector de Oportunidades Personalizadas")
    st.markdown("Selecciona áreas de interés y analizaré los datos para encontrar insights accionables.")
    opciones_analisis = st.multiselect("Selecciona qué oportunidades quieres buscar:", ["Clientes en Riesgo de Abandono", "Oportunidades de Venta Cruzada (Cross-selling)", "Optimización de Servicios", "Rendimiento de Barberos", "Mejorar Días de Baja Demanda"], default=["Clientes en Riesgo de Abandono", "Optimización de Servicios"])
    if st.button("🔍 Encontrar Oportunidades Seleccionadas"):
        if not model: st.error("El modelo de IA no está disponible.")
        elif df_filtrado.empty or not opciones_analisis: st.warning("Selecciona al menos un área de interés y asegúrate de que haya datos filtrados.")
        else:
            with st.spinner("Buscando insights valiosos... 💎"):
                try:
                    df_filtrado['Fecha'] = pd.to_datetime(df_filtrado['Fecha'])
                    datos_clave_str = ""
                    try:
                        fecha_maxima = df_filtrado['Fecha'].max()
                        clientes_recientes = df_filtrado[df_filtrado['Fecha'] > (fecha_maxima - pd.Timedelta(days=90))]
                        todos_los_clientes = df_filtrado['Nombre_Completo_Cliente'].dropna().unique()
                        clientes_recientes_unicos = clientes_recientes['Nombre_Completo_Cliente'].dropna().unique()
                        clientes_en_riesgo = [c for c in todos_los_clientes if c and c not in clientes_recientes_unicos]
                        datos_clave_str += f"- Clientes en Riesgo (no visitan en 90 días): {len(clientes_en_riesgo)}.\n"
                    except Exception: pass
                    prompt_oportunidad = f"""Eres un estratega de negocios para barberías. Analiza los datos clave y las áreas de interés. Para CADA área, proporciona: 1. **Hallazgo Principal**. 2. **Oportunidad Estratégica**. 3. **Acción Concreta**. Usa Markdown. DATOS CLAVE: {datos_clave_str} ÁREAS DE INTERÉS: {', '.join(opciones_analisis)}"""
                    respuesta_ia = model.generate_content(prompt_oportunidad)
                    st.markdown(respuesta_ia.text)
                except Exception as e:
                    st.error(f"No se pudo generar el análisis de oportunidades: {e}")


with tab_asesor:
    st.header("✂️ Asesor de Estilo Virtual con IA")
    st.markdown("Sube una foto de tu rostro y te recomendaré cortes de cabello y estilos que te favorezcan.")
    uploaded_file = st.file_uploader("Sube una foto donde tu rostro se vea claramente", type=["jpg", "jpeg", "png"], key="style_uploader")
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        col1, col2 = st.columns([1, 2])
        with col1:
            st.image(image, caption="Imagen subida", width=250)
        with col2:
            st.write("")
            if st.button("✨ ¡Recomiéndame un corte!", key="style_button"):
                if not model:
                    st.error("El modelo de IA no está disponible.")
                else:
                    with st.spinner("Analizando tus rasgos... 🧐"):
                        try:
                            prompt_parts = [
                                """
                                Actúa como un estilista de élite y experto en visagismo masculino. Tu cliente te ha mostrado una foto para que le des una asesoría de imagen completa.
                                
                                **Tu Tarea (formato Markdown):**
                                1.  **Diagnóstico del Rostro:** Primero, identifica la forma del rostro (ej. Ovalado, Cuadrado, Redondo, etc.).
                                2.  **Recomendaciones de Cortes (Top 3):**
                                    - **Nombre del Estilo:** (ej. Pompadour Clásico, Buzz Cut, Quiff Texturizado).
                                    - **¿Por qué te favorece?:** Explica brevemente cómo el corte complementa la forma del rostro.
                                    - **Nivel de Mantenimiento:** (Bajo, Medio, Alto).
                                    - **Productos Recomendados:** Sugiere un tipo de producto ideal (ej. Cera mate, pomada base agua, spray de sal marina).
                                    - **Inspiración Visual:** Proporciona un enlace de búsqueda de Google Images para que el cliente vea ejemplos. Usa el formato: `[Ver Ejemplos](https://www.google.com/search?q=...&tbm=isch)`
                                
                                Sé profesional, alentador y específico en tus recomendaciones.
                                """,
                                image,
                            ]
                            response = model.generate_content(prompt_parts)
                            st.divider()
                            st.markdown("### 💈 Mis recomendaciones para ti:")
                            st.markdown(response.text)
                            st.link_button("📅 ¡Reserva tu cita ahora!", "http://localhost:3000", type="primary")
                        except Exception as e:
                            st.error("¡Oops! Ocurrió un error al analizar la imagen.")
                            st.exception(e)