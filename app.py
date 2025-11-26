import streamlit as st
import google.generativeai as genai
import time
import json
import re
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
    try:
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
    except:
        return "00:00:00,000"

def generate_subtitles_content(subtitles, format_type):
    """แปลง List ของ Dict ให้เป็น text ตาม format"""
    output = ""
    try:
        if format_type == "SRT":
            for i, sub in enumerate(subtitles, 1):
                start = seconds_to_timestamp(sub.get('start', 0), "srt")
                end = seconds_to_timestamp(sub.get('end', 0), "srt")
                text = sub.get('text', '')
                output += f"{i}\n{start} --> {end}\n{text}\n\n"
        
        elif format_type == "VTT":
            output = "WEBVTT\n\n"
            for sub in subtitles:
                start = seconds_to_timestamp(sub.get('start', 0), "vtt")
                end = seconds_to_timestamp(sub.get('end', 0), "vtt")
                text = sub.get('text', '')
                output += f"{start} --> {end}\n{text}\n\n"
                
        elif format_type == "TXT":
            for sub in subtitles:
                start = seconds_to_timestamp(sub.get('start', 0), "srt")
                text = sub.get('text', '')
                output += f"[{start}] {text}\n"
                
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
                start = seconds_to_timestamp(sub.get('start', 0), "ass")
                end = seconds_to_timestamp(sub.get('end', 0), "ass")
                text = sub.get('text', '')
                output += f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n"
    except Exception as e:
        output += f"\nError generating format: {e}"
            
    return output

def clean_json_response(text):
    """ลบ Markdown block ออกจาก Response ก่อน Parse JSON"""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

# --- Sidebar Configuration ---
st.sidebar.title("⚙️ Configuration")

api_key = st.sidebar.text_input("Gemini API Key", type="password", placeholder="Paste your AIza... key here")

model_name = st.sidebar.selectbox(
    "Model Selection",
    [
        "gemini-3-pro-preview",
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.0-flash",
        "gemini-exp-1121",
        "gemini-1.5-pro",
        "gemini-1.5-flash"
    ],
    index=0
)

# Safety Settings
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

# --- Main Interface ---
st.title("🔥 Auto Erotic Subtitles Generator")
st.markdown(f"Using Model: **{model_name}**")

uploaded_file = st.file_uploader(
    "Upload Media File (Max 200MB for Free Tier)", 
    type=['mp4', 'mp3', 'm4a', 'wav', 'aac', 'flac']
)

col1, col2 = st.columns(2)
with col1:
    src_lang = st.selectbox("เสียงในไฟล์ (Audio Language)", ["Japanese", "English", "Chinese", "Thai", "Korean"])
with col2:
    tgt_lang = st.selectbox("ภาษาซับไตเติล (Subtitle Language)", ["Thai", "English", "Japanese", "Chinese", "Korean"])

# --- Custom Keywords (Fixed Default) ---
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
    height=300
)

if st.button("🚀 Start Generating Subtitles") and uploaded_file and api_key:
    genai.configure(api_key=api_key)
    
    status_text = st.empty()
    progress_bar = st.progress(0)
    
    try:
        # 1. Upload
        status_text.text(f"1/4 Uploading file to Gemini Server...")
        progress_bar.progress(10)
        
        with open("temp_media_file", "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        myfile = genai.upload_file("temp_media_file", mime_type=uploaded_file.type)
        
        while myfile.state.name == "PROCESSING":
            time.sleep(2)
            myfile = genai.get_file(myfile.name)
            
        status_text.text("2/4 File processed. Generating subtitles (This may take a while)...")
        progress_bar.progress(40)

        # 2. Prompt
        system_prompt = f"""
        You are an expert subtitle translator specialized in erotic, lively, and adult content.
        
        Task: Transcribe and translate the audio from the file into {tgt_lang}.
        Source Language: {src_lang}.
        
        STRICT Style Guidelines:
        1. **Erotic & Lively:** Use slang, dirty words, and direct sexual terms. Make it sound hot and realistic.
        2. **Real Sounds ONLY:** Do NOT use parenthetical descriptions like (moan). Instead, transcribe the actual sound: "Ahh~", "Ohh fuck~", "Mmm~".
        3. **Keywords:** You MUST use these terms: หี, ควย, เงี่ยน, น้ำเงี่ยน, เสียว, น้ำแตก, เย็ด, แตด (and others provided).
        4. **User Instructions:**
        {user_context}
        
        Output Format:
        Return a strict JSON list of objects. No markdown formatting.
        Format: [ {{"start": 12.5, "end": 15.2, "text": "Ohh~ Yes... deeper..."}}, ... ]
        """

        # 3. Call Model with High Token Limit
        try:
            model = genai.GenerativeModel(model_name=model_name, safety_settings=safety_settings)
            
            # เพิ่ม max_output_tokens เพื่อลดโอกาสข้อความขาด
            response = model.generate_content(
                [myfile, system_prompt],
                generation_config={
                    "response_mime_type": "application/json",
                    "max_output_tokens": 8192, 
                    "temperature": 0.6
                }
            )
            
            status_text.text("3/4 Processing response...")
            progress_bar.progress(80)

            # 4. Parse & Download
            cleaned_text = clean_json_response(response.text)
            
            try:
                subtitles_data = json.loads(cleaned_text)
                
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
                
                status_text.text("✅ Completed successfully!")
                progress_bar.progress(100)

            except json.JSONDecodeError as e:
                # --- Rescue Mode ---
                st.error(f"⚠️ Warning: The output was truncated or invalid JSON (Line {e.lineno}).")
                st.info("Showing RAW output instead so you can salvage the subtitles.")
                
                # พยายามแสดง Raw Text
                st.text_area("RAW Output (Copy this manually)", cleaned_text, height=400)
                
                # สร้างปุ่ม Download สำหรับ Raw Text เผื่อเอาไปแก้เอง
                st.download_button(
                    label="Download Raw Text (.json)",
                    data=cleaned_text,
                    file_name="raw_subtitles_partial.json",
                    mime="application/json"
                )
                progress_bar.progress(100)

        except Exception as e:
             st.error(f"Model API Error ({model_name}): {e}")
             st.warning("Try switching models or checking your API Key.")
            
    except Exception as e:
        st.error(f"System Error: {e}")
