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

# ================= 侧边栏：配置 API Key 和 公司信息 =================
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("输入你的 Gemini API Key:", type="password")
    # 修复 1：增加公司名称自定义输入框，彻底消灭幽灵公司名
    company_name = st.text_input("输入您的公司名称 (将显示在报价单顶部):", value="My Contractor Company")
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
    elif not company_name:
        st.error("请先在左侧边栏配置您的公司名称！")
    elif uploaded_file is None or not voice_notes:
        st.error("请同时提供现场照片和语音描述！")
    else:
        with st.spinner("AI 正在深度分析照片并生成专业报价..."):
            try:
                # 1. 初始化模型
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.5-flash')

                # 2. 设定极度专业的系统提示词 (注入真实的 Company Name)
                prompt = f"""
                You are a highly professional contractor estimator in the United States. 
                Based on the provided image of the worksite and the following raw notes from the contractor: "{voice_notes}", 
                generate a formal, professional quote for the customer in English.
                
                Format the output strictly as plain text (no markdown formatting, no emojis, standard ASCII characters only) in the following structure:
                
                COMPANY: {company_name}
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
                
                # 修复 2：将现场图片转换并嵌入到 PDF 顶部
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_img:
                    # 将图片转为 RGB 模式（防止 RGBA 报错）并保存为临时文件供 FPDF 读取
                    img_to_save = image.convert('RGB')
                    img_to_save.save(tmp_img.name)
                    
                    # 插入图片（设置宽度为 100，居中展示的粗略坐标）
                    pdf.image(tmp_img.name, x=55, w=100) 
                    pdf.ln(10) # 图片下方留白
                    tmp_img_path = tmp_img.name
                
                # 修复 3：使用 multi_cell 处理自动换行，彻底告别文字截断
                for line in quote_text.split('\n'):
                    clean_line = line.encode('latin-1', 'replace').decode('latin-1')
                    # 宽度设为 0 表示一直延伸到右侧页边距，高度为 8
                    pdf.multi_cell(0, 8, txt=clean_line)
                
                # 保存为临时文件并提供下载
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    pdf.output(tmp_file.name)
                    with open(tmp_file.name, "rb") as f:
                        pdf_bytes = f.read()
                
                st.download_button(
                    label="📥 下载专业级 PDF 报价单",
                    data=pdf_bytes,
                    file_name="Official_Quote.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
                
                # 清理产生的两个临时文件，防止内存泄漏
                os.unlink(tmp_img_path)
                os.unlink(tmp_file.name)

            except Exception as e:
                st.error(f"生成失败，请检查网络或配置: {e}")
