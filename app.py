import streamlit as st
import google.generativeai as genai
from PIL import Image
from fpdf import FPDF
import tempfile
import os

# ================= 页面配置 =================
st.set_page_config(page_title="AI Quote Generator Pro", page_icon="🔧", layout="centered")

st.title("🔧 AI Auto-Quote for Contractors")
st.markdown("上传现场照片并输入您的语音描述，AI 将为您生成专业的英文报价单。")

# ================= 侧边栏：配置 API Key =================
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("输入你的 Gemini API Key:", type="password")
    st.markdown("---")
    st.markdown("💡 **Tip**: 测试通过后，可以推送到你的 wux401425-create GitHub 仓库进行版本管理，但记得在代码外层配置环境变量，不要把 Key 硬编码提交。")

# ================= 主界面：输入区 =================
col1, col2 = st.columns(2)

with col1:
    uploaded_file = st.file_uploader("1. 上传受损现场照片 (JPG/PNG)", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Photo", use_container_width=True)

with col2:
    voice_notes = st.text_area("2. 师傅语音录入 (可用中文口述)", height=150, 
                               placeholder="例如：这水管彻底爆了，得换一段新的 PVC 管和接头。材料大概 50 刀，人工我得收 150 刀，明天上午能搞定。")

# ================= 核心逻辑：生成与 PDF 构建 =================
if st.button("🚀 一键生成全英文专业报价单", use_container_width=True):
    if not api_key:
        st.error("请先在左侧边栏输入您的 API Key！")
    elif uploaded_file is None or not voice_notes:
        st.error("请同时提供现场照片和语音描述！")
    else:
        with st.spinner("AI 正在深度分析照片并生成专业报价..."):
            try:
                # 1. 初始化模型 (使用速度极快、支持多模态的 Flash 模型)
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')

                # 2. 设定极度专业的系统提示词 (Prompt)
                prompt = f"""
                You are a highly professional contractor estimator in the United States. 
                Based on the provided image of the worksite and the following raw notes from the contractor: "{voice_notes}", 
                generate a formal, professional quote for the customer in English.
                
                Format the output strictly as plain text (no markdown formatting, no emojis, standard ASCII characters only) in the following structure:
                
                COMPANY: TopTier Services
                DOCUMENT: Official Quote
                --------------------------------------------------
                CUSTOMER ISSUE SUMMARY:
                (Write a professional summary of the problem seen in the image and notes)
                
                PROPOSED SOLUTION:
                (Write a professional explanation of the work to be done)
                
                ESTIMATED BREAKDOWN:
                - Materials: (Estimate based on notes)
                - Labor: (Estimate based on notes)
                
                TOTAL ESTIMATED COST: (Calculate the total)
                --------------------------------------------------
                Terms: Valid for 30 days. Work will be completed as described.
                """

                # 3. 调用 AI 大脑
                response = model.generate_content([prompt, image])
                quote_text = response.text

                # 4. 在页面上展示结果
                st.success("✅ 报价单生成成功！")
                st.text_area("报价单预览 (可手动微调):", value=quote_text, height=300)

                # 5. 将文本转化为高大上的 PDF
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                
                # FPDF 处理多行文本
                for line in quote_text.split('\n'):
                    # 将 utf-8 转换为 latin-1 以适配 FPDF 的默认编码
                    clean_line = line.encode('latin-1', 'replace').decode('latin-1')
                    pdf.cell(200, 10, txt=clean_line, ln=True, align='L')
                
                # 保存为临时文件并提供下载
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    pdf.output(tmp_file.name)
                    with open(tmp_file.name, "rb") as f:
                        pdf_bytes = f.read()
                
                st.download_button(
                    label="📥 下载 PDF 报价单发送给客户",
                    data=pdf_bytes,
                    file_name="Official_Quote.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
                
                # 清理临时文件
                os.unlink(tmp_file.name)

            except Exception as e:
                st.error(f"生成失败，请检查网络或 API Key: {e}")
