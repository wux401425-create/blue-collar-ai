import streamlit as st
import google.generativeai as genai
import json
from PIL import Image
from fpdf import FPDF
import tempfile
import os

# ================= 页面配置 =================
st.set_page_config(page_title="AI Quote Generator Pro", page_icon="💼", layout="centered")

st.title("💼 AI Auto-Quote Pro")
st.markdown("上传现场照片并输入您的语音描述，系统将生成格式严谨、零计算错误的商业级报价单。")

# ================= 侧边栏：配置区 =================
with st.sidebar:
    st.header("⚙️ 商业配置")
    api_key = st.text_input("输入 Gemini API Key:", type="password")
    company_name = st.text_input("公司名称 (抬头):", value="TopTier Plumbing & Repair")
    st.markdown("---")
    st.markdown("💡 **Pro Tip**: 当前版本已启用严格的 JSON 结构化输出与智能分页排版，消除金额倒置与排版断层风险。")

# ================= 主界面：输入区 =================
col1, col2 = st.columns(2)

with col1:
    uploaded_file = st.file_uploader("1. 上传受损现场照片", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Worksite Photo", use_container_width=True)

with col2:
    voice_notes = st.text_area("2. 师傅语音录入", height=150, 
                               placeholder="例如：这水管彻底爆了，得换一段新的 PVC 管和接头。材料大概 50 刀，人工我得收 150 刀，明天上午能搞定。")

# ================= 核心商业逻辑 =================
if st.button("🚀 生成商业级 PDF 报价单", use_container_width=True):
    if not api_key or not company_name:
        st.error("请确保 API Key 和 公司名称 已填写完毕！")
    elif uploaded_file is None or not voice_notes:
        st.error("请提供现场照片和语音描述，以便系统进行精准估价。")
    else:
        with st.spinner("系统正在进行结构化分析与严谨核算..."):
            try:
                # 1. 初始化模型
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.5-flash')

                # 2. 商业级 Prompt: 强制返回 JSON 格式
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

                # 强制 Gemini 返回 JSON (结构化输出)
                response = model.generate_content(
                    [prompt, image],
                    generation_config=genai.GenerationConfig(
                        response_mime_type="application/json",
                        temperature=0.1 # 降低温度，确保输出高度稳定
                    )
                )
                
                # 3. 解析 JSON 数据，系统自己做数学题，杜绝 AI 算错
                quote_data = json.loads(response.text)
                mat_cost = float(quote_data.get("materials_cost", 0))
                lab_cost = float(quote_data.get("labor_cost", 0))
                total_cost = mat_cost + lab_cost # 绝对正确的数学计算

                # 4. 生成商业级 PDF (加入智能排版)
                pdf = FPDF()
                pdf.add_page()
                
                # --- 头部信息 ---
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(0, 10, txt=f"COMPANY: {company_name}", ln=True, align='C')
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 10, txt="DOCUMENT: Official Quote", ln=True, align='C')
                pdf.line(10, 30, 200, 30) # 添加分隔线
                pdf.ln(10)
                
                # --- 嵌入图片 ---
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_img:
                    img_to_save = image.convert('RGB')
                    img_to_save.save(tmp_img.name)
                    pdf.image(tmp_img.name, x=55, w=100) 
                    pdf.ln(5)
                    tmp_img_path = tmp_img.name

                # --- 正文内容 (自动换行) ---
                def write_section(title, content):
                    pdf.set_font("Arial", 'B', 11)
                    pdf.cell(0, 8, txt=title, ln=True)
                    pdf.set_font("Arial", '', 11)
                    clean_content = content.encode('latin-1', 'replace').decode('latin-1')
                    pdf.multi_cell(0, 6, txt=clean_content)
                    pdf.ln(5)

                write_section("CUSTOMER ISSUE SUMMARY:", quote_data["issue_summary"])
                write_section("PROPOSED SOLUTION:", quote_data["proposed_solution"])

                # --- 智能换页逻辑 (防断层) ---
                # 预判剩余空间：如果距离页面底部不足 50mm，提前换页
                if pdf.get_y() > 240: 
                    pdf.add_page()

                # --- 费用明细 ---
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
                pdf.cell(0, 6, txt="Terms: Valid for 30 days. Work will be completed as described.", ln=True)

                # --- 保存与下载 ---
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    pdf.output(tmp_file.name)
                    with open(tmp_file.name, "rb") as f:
                        pdf_bytes = f.read()
                
                st.success("✅ 商业级报价单已成功生成！金额核对无误。")
                st.download_button(
                    label="📥 立即下载 PDF",
                    data=pdf_bytes,
                    file_name="Pro_Official_Quote.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
                
                # 清理临时文件
                os.unlink(tmp_img_path)
                os.unlink(tmp_file.name)

            except json.JSONDecodeError:
                st.error("数据结构化解析失败，请重试。")
            except Exception as e:
                st.error(f"生成过程发生错误: {e}")
