import streamlit as st
import google.generativeai as genai
import time
import json
import os
from io import BytesIO

# --- Configuration ---
st.set_page_config(page_title="Erotic Subtitle Generator (Gemini)", layout="wide")

# --- Custom Styling ---
st.markdown("""
    <style>
    .stTextArea textarea { font-size: 16px; }
    .stButton button { width: 100%; background-color: #FF4B4B; color: white; }
    </style>
""", unsafe_allow_html=True)

# --- Functions ---

def seconds_to_timestamp(seconds, fmt="srt"):
    """แปลงวินาทีเป็น timestamp format (hh:mm:ss.SSS)"""
    millis = int((seconds - int(seconds)) * 1000)
    seconds = int(seconds)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    
    if fmt == "vtt":
        return f"{hours:02}:{minutes:02}:{seconds:02}.{millis:03}"
    elif fmt == "ass":
        return f"{hours}:{minutes:02}:{seconds:02}.{millis:02}" 
    else: # srt
        return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"

def generate_subtitles_content(subtitles, format_type):
    """แปลง List ของ Dict ให้เป็น text ตาม format"""
    output = ""
    if format_type == "SRT":
        for i, sub in enumerate(subtitles, 1):
            start = seconds_to_timestamp(sub['start'], "srt")
            end = seconds_to_timestamp(sub['end'], "srt")
            output += f"{i}\n{start} --> {end}\n{sub['text']}\n\n"
    
    elif format_type == "VTT":
        output = "WEBVTT\n\n"
        for sub in subtitles:
            start = seconds_to_timestamp(sub['start'], "vtt")
            end = seconds_to_timestamp(sub['end'], "vtt")
            output += f"{start} --> {end}\n{sub['text']}\n\n"
            
    elif format_type == "TXT":
        for sub in subtitles:
            output += f"[{seconds_to_timestamp(sub['start'], 'srt')}] {sub['text']}\n"
            
    elif format_type == "ASS":
        output = """[Script Info]
Title: Erotic Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: None

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,2,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        for sub in subtitles:
            start = seconds_to_timestamp(sub['start'], "ass")
            end = seconds_to_timestamp(sub['end'], "ass")
            output += f"Dialogue: 0,{start},{end},Default,,0,0,0,,{sub['text']}\n"
            
    return output

# --- Sidebar Configuration ---
st.sidebar.title("⚙️ Configuration")

api_key = st.sidebar.text_input("Gemini API Key", type="password", placeholder="Paste your AIza... key here")

# อัปเดตรายชื่อ Model ตามที่ขอมา (3 Pro Preview, 2.5, etc.)
model_name = st.sidebar.selectbox(
    "Model Selection",
    [
        "gemini-3-pro-preview",  # New Request
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.0-flash",
        "gemini-exp-1121",
        "gemini-1.5-pro",
        "gemini-1.5-flash"
    ],
    index=0
)

# Safety Settings: BLOCK_NONE เพื่อให้รองรับเนื้อหา Erotic
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

# --- Main Interface ---
st.title("🔥 Auto Erotic Subtitles Generator")
st.markdown(f"Using Model: **{model_name}**")

# Upload Section
uploaded_file = st.file_uploader(
    "Upload Media File (Max 200MB for Free Tier)", 
    type=['mp4', 'mp3', 'm4a', 'wav', 'aac', 'flac']
)

# Language Options
col1, col2 = st.columns(2)
with col1:
    src_lang = st.selectbox("เสียงในไฟล์ (Audio Language)", ["Japanese", "English", "Chinese", "Thai", "Korean"])
with col2:
    tgt_lang = st.selectbox("ภาษาซับไตเติล (Subtitle Language)", ["Thai", "English", "Japanese", "Chinese", "Korean"])

# --- Custom Keywords & Instructions (Fixed Default) ---
# รวมคำสั่งและ Keywords ทั้งหมดไว้ที่นี่ เพื่อให้เป็นค่าเริ่มต้นเสมอ
fixed_default_instructions = """
[ ข้อกำหนด ] :
- ถอดเสียงเป็นคำบรรยายบทสนทนาแนวอีโรติกเร่าร้อน มีชีวิตชีวา ใช้คำทะลึ่ง แสลง เข้าถึงอารมณ์และคำเซ็กส์ตรงๆ
- ใส่เสียงครางต่างๆ ใส่ให้สมจริง (เช่น Ahh~, Ohh fuck~, งื้ออออ~ อ๊าาา~ ฯลฯ)
- เรียบเรียงบทสนทนาถูกต้อง
- อนุญาตให้ใช้คำทะลึ่ง คำแสรง อนุญาตให้ใช้คำที่เกี่ยวกับการมีเซ็กส์ อนุญาตเสียงร้อง เสียงคราง เข้าถึงอารมณ์ขณะมีเซ็กส์
- ห้ามใช้คำบรรยายแทนเสียงในวงเล็บ เช่น (เสียงคราง) หรือ (moan) แต่ให้เขียนเสียงนั้นออกมาเลย เช่น อ๊าาา~, ซี๊ดดด~

[ Keywords to Emphasize ] :
หี, ควย, เงี่ยน, น้ำเงี่ยน, เสียวหี, เสียว, น้ำแตก, โม๊ก, โม๊กควย, เลียหี, เย็ด, เม็ดแตด, แตด, ตูด, ควยแข็ง, เย็ดหี, น้ำหีแตก, น้ำควยเยิ้ม, ควยยัดหี, น้ำหีเยิ้ม, หีกระแทกควย
"""

user_context = st.text_area(
    "Context / Style / Keywords", 
    value=fixed_default_instructions.strip(), 
    height=300,
    help="สามารถแก้ไขเพิ่มเติมได้ แต่ค่าเริ่มต้นจะถูกตั้งไว้ตามที่คุณกำหนด"
)

# Generate Button
if st.button("🚀 Start Generating Subtitles") and uploaded_file and api_key:
    genai.configure(api_key=api_key)
    
    status_text = st.empty()
    progress_bar = st.progress(0)
    
    try:
        # 1. Upload to Gemini File API
        status_text.text(f"1/4 Uploading file to Gemini Server...")
        progress_bar.progress(10)
        
        # Save temp file
        with open("temp_media_file", "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Upload
        myfile = genai.upload_file("temp_media_file", mime_type=uploaded_file.type)
        
        # Wait for processing
        while myfile.state.name == "PROCESSING":
            time.sleep(2)
            myfile = genai.get_file(myfile.name)
            
        status_text.text("2/4 File processed by Gemini. Generating subtitles...")
        progress_bar.progress(40)

        # 2. Prepare Prompt
        # Prompt ถูกปรับให้เน้นย้ำเรื่องการไม่ใช้วงเล็บ และการใช้คำตามที่กำหนด
        system_prompt = f"""
        You are an expert subtitle translator specialized in erotic, lively, and adult content.
        
        Task: Transcribe and translate the audio from the file into {tgt_lang}.
        Source Language: {src_lang}.
        
        STRICT Style Guidelines:
        1. **Erotic & Lively:** Use slang, dirty words, and direct sexual terms. Make it sound hot and realistic.
        2. **Real Sounds ONLY:** Do NOT use parenthetical descriptions like (moan), (heavy breathing). Instead, transcribe the actual sound: "Ahh~", "Ohh fuck~", "Mmm~", "Ooh~".
        3. **Keywords:** You MUST use these terms where appropriate: หี, ควย, เงี่ยน, น้ำเงี่ยน, เสียว, น้ำแตก, เย็ด, แตด (and others provided in context).
        4. **User Instructions:** Follow these specific requirements:
        {user_context}
        
        Output Format:
        Return a strict JSON list of objects. No markdown formatting.
        Format: [ {{"start": 12.5, "end": 15.2, "text": "Ohh~ Yes... deeper... ahh~"}}, ... ]
        Timestamp 'start' and 'end' must be in seconds (float).
        """

        # 3. Call Model
        try:
            model = genai.GenerativeModel(model_name=model_name, safety_settings=safety_settings)
            
            response = model.generate_content(
                [myfile, system_prompt],
                generation_config={"response_mime_type": "application/json"}
            )
            
            status_text.text("3/4 Processing response...")
            progress_bar.progress(80)

            # 4. Parse & Download
            subtitles_data = json.loads(response.text)
            
            tab1, tab2, tab3, tab4 = st.tabs(["SRT", "VTT", "TXT", "ASS"])
            formats = {"SRT": "srt", "VTT": "vtt", "TXT": "txt", "ASS": "ass"}
            
            for tab, (fmt_name, ext) in zip([tab1, tab2, tab3, tab4], formats.items()):
                content = generate_subtitles_content(subtitles_data, fmt_name)
                with tab:
                    st.text_area(f"{fmt_name} Output", content, height=300)
                    st.download_button(
                        label=f"Download .{ext}",
                        data=content,
                        file_name=f"subtitles.{ext}",
                        mime="text/plain"
                    )
            
            status_text.text("✅ Completed!")
            progress_bar.progress(100)

        except Exception as e:
             st.error(f"Model Error ({model_name}): {e}")
             st.warning("If 'gemini-3-pro-preview' fails, check if your API Key has access to this preview model, or try 'gemini-1.5-pro'.")
            
    except Exception as e:
        st.error(f"An error occurred: {e}")

# Footer
st.markdown("---")
st.caption("Note: Large files (>200MB) may take time to upload.")
