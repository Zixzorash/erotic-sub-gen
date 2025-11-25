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
        return f"{hours}:{minutes:02}:{seconds:02}.{millis:02}" # ASS ใช้ทศนิยม 2 ตำแหน่ง
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

model_name = st.sidebar.selectbox(
    "Model Selection",
    [
        "gemini-1.5-pro-latest", 
        "gemini-1.5-flash-latest", 
        "gemini-exp-1121", 
        "gemini-1.5-pro",
        "gemini-3-pro" # Placeholder as requested
    ],
    index=0
)

# Safety Settings: สำคัญมากสำหรับการถอดเสียงแนว Erotic ต้องปิดการ Block
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

# --- Main Interface ---
st.title("🔥 Auto Erotic Subtitles Generator")
st.markdown("ถอดเสียงและสร้างซับไตเติลแนวเร่าร้อนด้วย Gemini AI")

# Upload Section
uploaded_file = st.file_uploader(
    "Upload Media File (Max 500MB recommended)", 
    type=['mp4', 'mp3', 'm4a', 'wav', 'aac', 'flac']
)

# Language Options
col1, col2 = st.columns(2)
with col1:
    src_lang = st.selectbox("เสียงในไฟล์ (Audio Language)", ["Japanese", "English", "Chinese", "Thai", "Korean"])
with col2:
    tgt_lang = st.selectbox("ภาษาซับไตเติล (Subtitle Language)", ["Thai", "English", "Japanese", "Chinese", "Korean"])

# Custom Keywords (Hidden from UI code primarily, but user can edit here)
default_keywords = "ใช้คำแสลง, คำหยาบ, คำแสดงอารมณ์ทางเพศ, เสียงคราง (Ahh~, Ohh~), แปลให้ได้อารมณ์เงี่ยน"
user_context = st.text_area("Context / Style / Keywords (Optional)", value=default_keywords, help="ใส่คำค้นหาหรือสไตล์ที่ต้องการเน้นเพิ่มเติมที่นี่")

# Generate Button
if st.button("🚀 Start Generating Subtitles") and uploaded_file and api_key:
    genai.configure(api_key=api_key)
    
    status_text = st.empty()
    progress_bar = st.progress(0)
    
    try:
        # 1. Upload to Gemini File API
        status_text.text("1/4 Uploading file to Gemini Server...")
        progress_bar.progress(10)
        
        # Save temp file
        with open("temp_media_file", "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Upload
        myfile = genai.upload_file("temp_media_file", mime_type=uploaded_file.type)
        
        # Wait for processing (Video only, but good practice for all)
        while myfile.state.name == "PROCESSING":
            time.sleep(2)
            myfile = genai.get_file(myfile.name)
            
        status_text.text("2/4 File processed by Gemini. Generating subtitles...")
        progress_bar.progress(40)

        # 2. Prepare Prompt
        # Prompt นี้ถูกออกแบบมาให้คืนค่าเป็น JSON เพื่อความแม่นยำของ Timecode
        system_prompt = f"""
        You are an expert subtitle translator specialized in erotic, lively, and adult content.
        
        Task: Transcribe and translate the audio from the file into {tgt_lang}.
        Source Language: {src_lang}.
        
        Style Guidelines:
        - Strict Rule: Use erotic, slang, dirty words, and highly expressive language suitable for adult films.
        - Include sounds: Transcribe moans, breathing, and reaction sounds (e.g., Ahh~, Ohh fuck~, Hmm~).
        - Keywords to emphasize: {user_context}
        - The translation must be accurate to the timestamp but localized to be extremely arousing.
        
        Output Format:
        Return a strict JSON list of objects. No markdown formatting.
        Format: [ {{"start": 12.5, "end": 15.2, "text": "Ohh~ Yes... deeper..."}}, ... ]
        Timestamp 'start' and 'end' must be in seconds (float).
        """

        # 3. Call Model
        model = genai.GenerativeModel(model_name=model_name, safety_settings=safety_settings)
        
        response = model.generate_content(
            [myfile, system_prompt],
            generation_config={"response_mime_type": "application/json"}
        )
        
        status_text.text("3/4 Processing response...")
        progress_bar.progress(80)

        # 4. Parse & Download
        try:
            subtitles_data = json.loads(response.text)
            
            # Create tabs for formats
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
            
        except json.JSONDecodeError:
            st.error("Error: The model returned a format that couldn't be parsed as JSON. Try again or adjust the prompt.")
            st.code(response.text) # Debug output
            
        # Cleanup (Optional: Delete file from Gemini Cloud to save storage)
        # genai.delete_file(myfile.name)
        
    except Exception as e:
        st.error(f"An error occurred: {e}")

# Footer
st.markdown("---")
st.caption("Note: Large files (>200MB) may take time to upload depending on your internet connection.")
