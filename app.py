import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from colorthief import ColorThief
from io import BytesIO
from urllib.parse import urljoin
import random

# --- 1. SETUP PAGE ---
st.set_page_config(page_title="Pomelli Clone", page_icon="🎨", layout="centered")

# --- 2. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("Google Gemini API Key", type="password")
    st.caption("Required for text. Images are free.")
    st.markdown("[Get Gemini Key](https://aistudio.google.com/app/apikey)")

# --- 3. FUNCTIONS ---

def get_brand_dna(url):
    """Scrapes the URL for Logo and Colors"""
    if not url.startswith('http'):
        url = 'https://' + url
    
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, timeout=10, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Title
        title = soup.title.string.strip() if soup.title else "My Brand"
        
        # Logo (Favicon)
        icon_link = soup.find("link", rel=lambda x: x and 'icon' in x.lower())
        logo_url = "https://cdn-icons-png.flaticon.com/512/3678/3678443.png"
        if icon_link and icon_link.get('href'):
            logo_url = urljoin(url, icon_link.get('href'))

        # Color
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

def generate_real_image(prompt):
    """Generates an image using Pollinations.ai (Free, No Key required)"""
    # Clean prompt for URL
    clean_prompt = prompt.replace(" ", "%20")
    # Add seed to make it random every time
    seed = random.randint(1, 10000)
    image_url = f"https://image.pollinations.ai/prompt/{clean_prompt}?width=1080&height=1080&nologo=true&seed={seed}&model=flux"
    return image_url

# --- 4. MAIN APP ---
st.title("🎨 Brand DNA Studio")
st.write("Extract branding and generate **Real AI Images**.")

# A. SCANNER
url = st.text_input("Enter Website URL:", placeholder="example.com")

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
                st.success("Brand DNA Found!")
            else:
                st.error("Could not load website. Try another one.")

# B. GENERATOR
if st.session_state["brand"]:
    b = st.session_state["brand"]
    
    st.divider()
    col1, col2 = st.columns([1, 4])
    with col1:
        st.image(b['logo'], width=60)
    with col2:
        st.subheader(b['name'])
        b['color'] = st.color_picker("Brand Color:", b['color'])

    st.divider()
    st.subheader("✨ Create Campaign")
    
    topic = st.text_input("Post Topic", "Summer Sale Announcement")
    style = st.selectbox("Image Style", ["Minimalist", "Neon", "Luxury", "Professional", "3D Render"])
    
    if st.button("Generate Content"):
        if not api_key:
            st.error("⚠️ Please add your Gemini API Key in the sidebar for the text.")
        else:
            with st.spinner("Gemini is writing text & AI is painting the image..."):
                
                # 1. TEXT GENERATION (Gemini)
                try:
                    genai.configure(api_key=api_key)
                    # Use 'gemini-1.5-flash' explicitly
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    text_prompt = f"""
                    Write a short Instagram caption for '{b['name']}' about '{topic}'.
                    Tone: {style}. Max 30 words. No hashtags.
                    """
                    response = model.generate_content(text_prompt)
                    caption = response.text
                except Exception as e:
                    caption = f"Error generating text. Ensure your API key is valid. (Details: {e})"

                # 2. IMAGE GENERATION (Pollinations)
                # We construct a prompt based on the brand info
                image_prompt = f"professional product photography for {b['name']}, {topic}, {style} style, dominant color {b['color']}, high quality, 4k"
                image_url = generate_real_image(image_prompt)

                # 3. SHOW RESULTS
                st.markdown("### Result")
                out_col1, out_col2 = st.columns(2)
                
                with out_col1:
                    # Display the AI generated image
                    st.image(image_url, caption="AI Generated Image")
                
                with out_col2:
                    st.text_area("Caption", caption, height=200)
                    st.markdown(f"[Download Image]({image_url})")
