import streamlit as st
import google.generativeai as genai
import json
from PIL import Image
from fpdf import FPDF
import tempfile
import os

# ================= Page Configuration =================
st.set_page_config(page_title="AI Quote Pro | Contractor Tools", page_icon="💼", layout="centered")

# ================= Session State for Login =================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# ================= Login Gateway =================
if not st.session_state.logged_in:
    st.title("Welcome to AI Quote Pro 💼")
    st.markdown("Professional, error-free contractor quotes generated in seconds.")
    
    with st.container(border=True):
        st.subheader("Login to your account")
        # 演示用的简单登录，你可以随时改成连接数据库
        username = st.text_input("Username or Email")
        password = st.text_input("Password", type="password")
        
        if st.button("Log In", type="primary", use_container_width=True):
            if username and password:
                # 暂时允许任何输入登录，方便你发给别人试用
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Please enter both username and password.")
                
    st.markdown("<p style='text-align: center; color: gray; font-size: 14px;'>Don't have an account? <a href='#'>Start your 7-day free trial</a> (Coming soon)</p>", unsafe_allow_html=True)

# ================= Main Application (After Login) =================
else:
    st.title("💼 AI Auto-Quote Pro")
    st.markdown("Upload a worksite photo and provide a brief description. The AI will generate a professional, calculated PDF quote.")

    # --- Sidebar Settings ---
    with st.sidebar:
        st.header("⚙️ Account Settings")
        api_key = st.text_input("Gemini API Key:", type="password", help="Enter your Google Gemini API Key")
        company_name = st.text_input("Company Name (Header):", value="TopTier Plumbing & Repair")
        
        st.divider()
        st.markdown("💡 **Pro Tip**: This system uses strict JSON structuring to ensure zero calculation errors between materials and labor.")
        
        if st.button("Log Out"):
            st.session_state.logged_in = False
            st.rerun()

    # --- Main Inputs ---
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
                                   placeholder="Example: The main water pipe is completely busted. Need to replace a section of PVC and fittings. Materials are about $50, and I'll charge $150 for labor. Can be done tomorrow morning.")

    # --- Core Logic ---
    st.divider()
    if st.button("🚀 Generate Professional Quote (PDF)", type="primary", use_container_width=True):
        if not api_key or not company_name:
            st.error("⚠️ Please fill in your API Key and Company Name in the sidebar settings.")
        elif uploaded_file is None or not voice_notes:
            st.error("⚠️ Please provide both a worksite photo and a job description.")
        else:
            with st.spinner("AI is analyzing the site and calculating costs..."):
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-2.5-flash')

                    prompt = f"""
                    You are a highly professional contractor estimator in the United States. 
                    Analyze the provided image and the contractor's raw notes: "{voice_notes}".
                    
                    You MUST extract the information and return it STRICTLY as a JSON object with the following exact keys. Do not include any markdown formatting like ```json in your response, just the raw JSON:
                    {{
                        "issue_summary": "A formal, professional summary of the problem in English (1-2 sentences).",
                        "proposed_solution": "A professional explanation of the repair work to be done in English.",
                        "materials_cost": <extract the estimated materials cost as a raw number, e.g., 50>,
                        "labor_cost": <extract the estimated labor cost as a raw number, e.g., 150>
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

                    # Generate PDF
                    pdf = FPDF()
                    pdf.add_page()
                    
                    # Header
                    pdf.set_font("Arial", 'B', 16)
                    pdf.cell(0, 10, txt=f"COMPANY: {company_name}", ln=True, align='C')
                    pdf.set_font("Arial", 'B', 12)
                    pdf.cell(0, 10, txt="DOCUMENT: Official Quote", ln=True, align='C')
                    pdf.line(10, 30, 200, 30) 
                    pdf.ln(10)
                    
                    # Image
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_img:
                        img_to_save = image.convert('RGB')
                        img_to_save.save(tmp_img.name)
                        pdf.image(tmp_img.name, x=55, w=100) 
                        pdf.ln(5)
                        tmp_img_path = tmp_img.name

                    # Content
                    def write_section(title, content):
                        pdf.set_font("Arial", 'B', 11)
                        pdf.cell(0, 8, txt=title, ln=True)
                        pdf.set_font("Arial", '', 11)
                        clean_content = content.encode('latin-1', 'replace').decode('latin-1')
                        pdf.multi_cell(0, 6, txt=clean_content)
                        pdf.ln(5)

                    write_section("CUSTOMER ISSUE SUMMARY:", quote_data["issue_summary"])
                    write_section("PROPOSED SOLUTION:", quote_data["proposed_solution"])

                    # Smart Page Break
                    if pdf.get_y() > 240: 
                        pdf.add_page()

                    # Breakdown
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
                    pdf.cell(0, 6, txt="Terms: Valid for 30 days. Work will be completed as described. Final cost may vary if hidden damages are found.", ln=True)

                    # Output
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

                except json.JSONDecodeError:
                    st.error("❌ Failed to parse structured data. Please try again.")
                except Exception as e:
                    st.error(f"❌ An error occurred during generation: {e}")
