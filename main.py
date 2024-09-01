import os
import requests
import streamlit as st
from datetime import datetime
from urllib.parse import quote
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
from getdata import ApiClient, file_url
from utils import format_date, download_pdfs
from gtts import gTTS

# Load environment variables
load_dotenv()
os.environ['GROQ_API_KEY'] = os.getenv('GROQ_API_KEY')

# Initialize the language model
llm = ChatGroq(model='llama3-70b-8192')

# CSS to inject contained in a string
def add_custom_css():
    st.markdown("""
        <style>
            .main {
                background-color: #f7f9fc; /* Subtle light background */
                color: #333;
            }
            .stButton>button {
                background-color: #007acc; /* Vibrant blue button */
                color: white;
                border-radius: 8px;
                font-size: 16px;
                padding: 8px 16px;
                transition: background-color 0.3s ease;
                border: none;
                margin-top: 10px;
            }
            .stButton>button:hover {
                background-color: #005f99; /* Darker blue on hover */
                color: white;
            }
            .sidebar .sidebar-content {
                background-color: #e9f5ff; /* Soft blue sidebar */
                padding: 10px;
            }
            .sidebar .sidebar-content h2, .stSidebar h2 {
                color: #007acc;
            }
            .stSidebar .st-form {
                padding: 10px;
                background: #f0f8ff;
                border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }
            h1, h2, h3 {
                color: #333; /* Title color */
                font-family: 'Arial', sans-serif;
            }
            .stAudio {
                margin-top: 20px;
            }
        </style>
    """, unsafe_allow_html=True)

def convert_to_speech_vietnamese(text):
    """Convert text to speech in Vietnamese."""
    tts_vietnamese = gTTS(text=text, lang='vi')
    audio_file = "vietnamese_speech.mp3"
    tts_vietnamese.save(audio_file)
    return audio_file

def display_can_bo_info(can_bo_info):
    """Display staff information in the sidebar."""
    st.sidebar.subheader("Thông tin cán bộ")
    for can_bo in can_bo_info:
        st.sidebar.write(f"**Tên cán bộ:** {can_bo.get('ho_va_ten_can_bo', 'Không có dữ liệu')}")
        st.sidebar.write(f"**Chức vụ:** {can_bo.get('ten_chuc_vu', 'Không có dữ liệu')}")
        st.sidebar.write(f"**Đơn vị:** {can_bo.get('ten_don_vi', 'Không có dữ liệu')}")
        st.sidebar.write(f"**Số điện thoại:** {can_bo.get('di_dong_can_bo', 'Không có dữ liệu')}")
        st.sidebar.write("---")

def display_van_ban_info(van_ban, client):
    """Display document information and handle PDF summaries."""
    st.write(f"**Số ký hiệu:** {van_ban.get('so_ky_hieu', 'Không có dữ liệu')}")
    st.write(f"**Trích yếu:** {van_ban.get('trich_yeu', 'Không có dữ liệu')}")
    st.write(f"**Ngày ban hành:** {format_date(van_ban.get('ngay_ban_hanh', ''))}")
    st.write(f"**Người ký:** {van_ban.get('nguoi_ky', 'Không có dữ liệu')}")
    st.write(f"**Tên cơ quan ban hành:** {van_ban.get('ten_co_quan_ban_hanh', 'Không có dữ liệu')}")
    
    file_urls = [file_url(path=quote(file), type="view") for file in van_ban.get('file_dinh_kem', '').split(':') if file.lower().endswith('.pdf')]
    for url in file_urls:
        st.write(f"- [Tải về]({url})")

    summary_key = f'summary_{van_ban.get("so_ky_hieu")}'
    
    if st.button('Tạo tóm tắt', key=summary_key):
        if file_urls:
            download_pdfs(file_urls)
            loader = PyPDFDirectoryLoader("./PDF_Documents/")
            data = loader.load_and_split()
            
            prompt_1 = ChatPromptTemplate.from_messages([
                ("system", "You are a smart assistant. Please summarize the content of the user's PDF document. Be polite to the user and respond in Vietnamese. Do not add any concluding remarks or additional advice in the summary."),
                ("user", "{data}")
            ])

            output_parser = StrOutputParser()
            chain_1 = prompt_1 | llm | output_parser
            summary = chain_1.invoke({'data': data})
            st.write(summary)

            # Save audio file and display audio player
            audio_file = convert_to_speech_vietnamese(summary)
            st.audio(audio_file, format="audio/mp3")
                
    st.write("---")

def main():
    add_custom_css()  # Apply the custom CSS for styling
    st.title("Tóm tắt văn bản xử lý chính")

    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.client = None
        st.session_state.username = ''
        st.session_state.password = ''

    if not st.session_state.logged_in:
        with st.sidebar.form(key='login_form'):
            st.header("Thông tin đăng nhập")
            username = st.text_input("Tên đăng nhập")
            password = st.text_input("Mật khẩu", type="password")
            submit_button = st.form_submit_button("Tra cứu")

        if submit_button and username and password:
            try:
                client = ApiClient(username, password)
                can_bo_info = client.thong_tin_can_bo()
                if isinstance(can_bo_info, dict) and "error" in can_bo_info:
                    st.sidebar.error(can_bo_info["error"])
                else:
                    st.session_state.logged_in = True
                    st.session_state.client = client
                    st.session_state.username = username
                    st.session_state.password = password
                    st.rerun()
            except Exception as e:
                st.error(f"Đã xảy ra lỗi: {e}")
        elif submit_button:
            st.sidebar.error("Vui lòng nhập tên đăng nhập và mật khẩu.")
    else:
        st.sidebar.subheader("Đã đăng nhập")
        st.sidebar.write(f"**Tên đăng nhập:** {st.session_state.username}")

        if st.sidebar.button("Đăng xuất"):
            st.session_state.logged_in = False
            st.session_state.client = None
            st.session_state.username = ''
            st.session_state.password = ''
            st.rerun()

        client = st.session_state.client

        can_bo_info = client.thong_tin_can_bo()
        if isinstance(can_bo_info, dict) and "error" in can_bo_info:
            st.sidebar.error(can_bo_info["error"])
        elif can_bo_info:
            display_can_bo_info(can_bo_info)

            ma_ctcb_kc = can_bo_info[0].get('ma_ctcb_kc')
            ho_va_ten_can_bo = can_bo_info[0].get('ho_va_ten_can_bo')
            ma_don_vi_cha = can_bo_info[0].get('ma_don_vi_cha')

            if ma_ctcb_kc:
                van_ban_den = client.danh_sach_van_ban_den(ma_ctcb_kc, ho_va_ten_can_bo, ma_don_vi_cha)
                if isinstance(van_ban_den, list):
                    for van_ban in van_ban_den:
                        display_van_ban_info(van_ban, client)
                else:
                    st.write("Không có dữ liệu văn bản đến hoặc đã xảy ra lỗi.")
            else:
                st.error("Không thể lấy ma_ctcb_kc từ thông tin cán bộ.")

if __name__ == "__main__":
    main()
