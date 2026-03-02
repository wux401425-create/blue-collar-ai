import streamlit as st
import google.generativeai as genai
import json
from PIL import Image
from fpdf import FPDF
import tempfile
import os
import time # 新增：用于时间计算的库

# ================= Page Configuration =================
st.set_page_config(page_title="AI Quote Pro | Contractor Tools", page_icon="💼", layout="centered")

# ================= Session State 初始化 =================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
# 新增：记录上一次点击生成按钮的时间
if 'last_clicked' not in st.session_state:
    st.session_state.last_clicked = 0

# ================= Login Gateway =================
if not st.session_state.logged_in:
    st.title("Welcome to AI Quote Pro 💼")
    st.markdown("Professional, error-free contractor quotes generated in seconds.")
    
    with st.container(border=True):
        st.subheader("Login to your account")
        username = st.text_input("Username or Email")
        password = st.text_input("Password", type="password")
        
        if st.button("Log In", type="primary", use_container_width=True):
            if username and password:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Please enter both username and password.")
                
    st.markdown("<p style='text-align: center; color: gray; font-size: 14px;'>Don't have an account? <a href='#'>Start your 7-day free trial</a></p>", unsafe_allow_html=True)

# ================= Main Application =================
else:
    st.title("💼 AI Auto-Quote Pro")
    st.markdown("Upload a worksite photo and provide a brief description.")

    with st.sidebar:
        st.header("⚙️ Account Settings")
        company_name = st.text_input("Company Name (Header):", value="TopTier Plumbing & Repair")
        st.divider()
        if st.button("Log Out"):
            st.session_state.logged_in = False
            st.rerun()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. Worksite Photo")
        uploaded_file = st.file_uploader("Upload image (JPG/PNG)", type=["jpg", "jpeg", "png"])
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.image(image, caption="Worksite Photo", use_container_width=True)

    with col2:
        st.subheader("2. Job Description")
        voice_notes = st.text_area("Voice Notes / Text Input", height=150, 
                                   placeholder="Example: The main water pipe is completely busted...")

    st.divider()
    
    # 新增：冷却时间计算逻辑（10秒内禁止连续点击）
    current_time = time.time()
    time_passed = current_time - st.session_state.last_clicked
    can_click = time_passed > 10 
    
    # 如果还在冷却中，按钮上会显示提示
    button_label = "🚀 Generate Professional Quote (PDF)" if can_click else f"⏳ Please wait {int(10 - time_passed)} seconds..."

    if st.button(button_label, type="primary", use_container_width=True, disabled=not can_click):
        # 记录这次点击的时间
        st.session_state.last_clicked = current_time
        
        if not company_name:
            st.error("⚠️ Please fill in your Company Name in the sidebar.")
        elif uploaded_file is None or not voice_notes:
            st.error("⚠️ Please provide both a worksite photo and a job description.")
        else:
            with st.spinner("AI is analyzing the site and calculating costs..."):
                try:
                    # 读取隐藏在后端的 API Key
                    if "GEMINI_API_KEY" in st.secrets:
                        api_key = st.secrets["GEMINI_API_KEY"]
                    else:
                        st.error("⚠️ System Configuration Error: API key is missing.")
                        st.stop()

                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-2.5-flash')

                    prompt = f"""
                    You are a highly professional contractor estimator in the United States. 
                    Analyze the provided image and the contractor's raw notes: "{voice_notes}".
                    You MUST extract the information and return it STRICTLY as a JSON object...
                    {{
                        "issue_summary": "A formal summary...",
                        "proposed_solution": "A professional explanation...",
                        "materials_cost": <raw number>,
                        "labor_cost": <raw number>
                    }}
                    """

                    response = model.generate_content(
                        [prompt, image],
                        generation_config=genai.GenerationConfig(
                            response_mime_type="application/json",
                            temperature=0.1
                        )
                    )
                    
                    quote_data = json.loads(response.text)
                    mat_cost = float(quote_data.get("materials_cost", 0))
                    lab_cost = float(quote_data.get("labor_cost", 0))
                    total_cost = mat_cost + lab_cost 

                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", 'B', 16)
                    pdf.cell(0, 10, txt=f"COMPANY: {company_name}", ln=True, align='C')
                    pdf.set_font("Arial", 'B', 12)
                    pdf.cell(0, 10, txt="DOCUMENT: Official Quote", ln=True, align='C')
                    pdf.line(10, 30, 200, 30) 
                    pdf.ln(10)
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_img:
                        img_to_save = image.convert('RGB')
                        img_to_save.save(tmp_img.name)
                        pdf.image(tmp_img.name, x=55, w=100) 
                        pdf.ln(5)
                        tmp_img_path = tmp_img.name

                    def write_section(title, content):
                        pdf.set_font("Arial", 'B', 11)
                        pdf.cell(0, 8, txt=title, ln=True)
                        pdf.set_font("Arial", '', 11)
                        clean_content = content.encode('latin-1', 'replace').decode('latin-1')
                        pdf.multi_cell(0, 6, txt=clean_content)
                        pdf.ln(5)

                    write_section("CUSTOMER ISSUE SUMMARY:", quote_data["issue_summary"])
                    write_section("PROPOSED SOLUTION:", quote_data["proposed_solution"])

                    if pdf.get_y() > 240: 
                        pdf.add_page()

                    pdf.set_font("Arial", 'B', 12)
                    pdf.cell(0, 8, txt="ESTIMATED BREAKDOWN:", ln=True)
                    pdf.set_font("Arial", '', 11)
                    pdf.cell(0, 6, txt=f"- Materials: ${mat_cost:.2f}", ln=True)
                    pdf.cell(0, 6, txt=f"- Labor: ${lab_cost:.2f}", ln=True)
                    
                    pdf.ln(2)
                    pdf.set_font("Arial", 'B', 12)
                    pdf.cell(0, 8, txt=f"TOTAL ESTIMATED COST: ${total_cost:.2f}", ln=True)
                    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                    pdf.ln(5)
                    pdf.set_font("Arial", 'I', 10)
                    pdf.cell(0, 6, txt="Terms: Valid for 30 days. Final cost may vary if hidden damages are found.", ln=True)

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                        pdf.output(tmp_file.name)
                        with open(tmp_file.name, "rb") as f:
                            pdf_bytes = f.read()
                    
                    st.success("✅ Commercial-grade quote generated successfully!")
                    st.download_button(
                        label="📥 Download Quote (PDF)",
                        data=pdf_bytes,
                        file_name="Pro_Official_Quote.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                    
                    os.unlink(tmp_img_path)
                    os.unlink(tmp_file.name)

                except Exception as e:
                    st.error(f"❌ An error occurred: {e}")
