import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from colorthief import ColorThief
from io import BytesIO
from urllib.parse import urljoin
from PIL import Image, ImageDraw, ImageFont

# --- 1. SETUP PAGE ---
st.set_page_config(page_title="Pomelli Clone", page_icon="🎨", layout="centered")

# --- 2. SIDEBAR (API KEY INPUT) ---
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("Paste Google Gemini API Key", type="password")
    st.info("Get key here: https://aistudio.google.com/app/apikey")

    # --- MODEL SELECTOR ---
    # If Gemini 3 is available to you, type "gemini-3.0" below. 
    # Otherwise keep "gemini-1.5-flash" (it is the current fast standard).
    model_version = st.selectbox(
        "Select Gemini Version", 
        ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-3.0-flash"] 
    )

# --- 3. HELPER FUNCTION: SCAN WEBSITE ---
def get_brand_dna(url):
    """Scrapes the URL for Logo and Colors"""
    if not url.startswith('http'):
        url = 'https://' + url
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    try:
        response = requests.get(url, timeout=10, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get Title
        title = soup.title.string.strip() if soup.title else "My Brand"
        
        # Get Logo (Favicon)
        icon_link = soup.find("link", rel=lambda x: x and 'icon' in x.lower())
        logo_url = "https://cdn-icons-png.flaticon.com/512/3678/3678443.png" # Default
        
        if icon_link and icon_link.get('href'):
            logo_url = urljoin(url, icon_link.get('href'))

        # Get Color from Logo
        try:
            logo_resp = requests.get(logo_url, headers=headers, timeout=5)
            color_thief = ColorThief(BytesIO(logo_resp.content))
            dom_color = color_thief.get_color(quality=1)
            hex_color = '#{:02x}{:02x}{:02x}'.format(*dom_color)
        except:
            hex_color = "#000000"

        return {"name": title, "logo": logo_url, "color": hex_color}
    except:
        return None

# --- 4. MAIN APP INTERFACE ---
st.title("🎨 Brand DNA Studio")
st.write("Generate on-brand content using **Google Gemini**.")

# Step A: Enter URL
url = st.text_input("Enter your Website URL:", placeholder="example.com")

if "brand" not in st.session_state:
    st.session_state["brand"] = None

if st.button("🧬 Scan Website"):
    if not url:
        st.warning("Please type a URL first.")
    else:
        with st.spinner("Analyzing visual identity..."):
            data = get_brand_dna(url)
            if data:
                st.session_state["brand"] = data
                st.success("Success! Brand DNA extracted.")
            else:
                st.error("Could not load website. Try another one.")

# Step B: Show Results & Generate
if st.session_state["brand"]:
    b = st.session_state["brand"]
    
    st.divider()
    col1, col2 = st.columns([1, 3])
    with col1:
        st.image(b['logo'], width=80)
    with col2:
        st.subheader(b['name'])
        b['color'] = st.color_picker("Brand Color detected:", b['color'])

    st.divider()
    st.subheader("✨ Create Content")
    
    topic = st.text_input("Post Topic", "Summer Sale Announcement")
    
    if st.button("Run Gemini Generator"):
        if not api_key:
            st.error("⚠️ Please paste your API Key in the sidebar first!")
        else:
            with st.spinner(f"Generating with {model_version}..."):
                # 1. SETUP GEMINI
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel(model_version)
                    
                    # 2. WRITE COPY
                    prompt = f"""
                    You are the social media manager for '{b['name']}'.
                    Write a short, engaging social media caption about '{topic}'.
                    Tone: Professional but exciting. Max 25 words.
                    """
                    response = model.generate_content(prompt)
                    caption = response.text
                    
                    # 3. CREATE IMAGE (Simple Design)
                    # Create background
                    img = Image.new('RGB', (1080, 1080), color=b['color'])
                    d = ImageDraw.Draw(img)
                    
                    # White card
                    d.rectangle([(100, 300), (980, 780)], fill="white")
                    
                    # Add Text (Fallback font)
                    d.text((150, 400), b['name'].upper(), fill="black")
                    d.text((150, 450), topic, fill=b['color'])
                    
                    # Add Logo overlay
                    try:
                        l_req = requests.get(b['logo'])
                        l_img = Image.open(BytesIO(l_req.content)).convert("RGBA")
                        l_img.thumbnail((100, 100))
                        img.paste(l_img, (490, 150), l_img)
                    except:
                        pass
                    
                    # 4. SHOW OUTPUT
                    out_col1, out_col2 = st.columns(2)
                    with out_col1:
                        st.image(img, caption="Generated Visual", use_container_width=True)
                    with out_col2:
                        st.text_area("Caption", caption, height=200)
                        
                except Exception as e:
                    st.error(f"Error: {e}")
                    st.write("If you chose 'Gemini 3' and it failed, Google may not have released it to your account yet. Try 'Gemini 1.5 Flash'.")