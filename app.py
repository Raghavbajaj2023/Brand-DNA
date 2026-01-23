import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from colorthief import ColorThief
from io import BytesIO
from urllib.parse import urljoin
from PIL import Image, ImageDraw, ImageFont
import os
from dotenv import load_dotenv

# --- 1. SETUP ---
st.set_page_config(page_title="Pomelli (Gemini 3 Edition)", page_icon="🍌", layout="centered")

# Load API Key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# Configure SDK
if api_key:
    genai.configure(api_key=api_key)

# --- 2. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Settings")
    
    if not api_key:
        st.error("🔑 API Key Missing")
        st.info("Add GEMINI_API_KEY to your .env file")
        api_input = st.text_input("Or paste here (temporary)", type="password")
        if api_input:
            genai.configure(api_key=api_input)
            api_key = api_input
            
    st.markdown("---")
    st.markdown("### 🧠 Models Active")
    st.success("📝 Text: **Gemini 3 Pro**")
    st.info("🎨 Image: **Nano Banana Pro**")
    st.caption("(gemini-3-pro-image-preview)")

# --- 3. FUNCTIONS ---

def get_brand_dna(url):
    """Scrapes website for Brand Name, Logo, and Color"""
    if not url.startswith('http'): url = 'https://' + url
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, timeout=10, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Title
        title = soup.title.string.strip() if soup.title else "Brand"
        
        # 2. Logo
        icon_link = soup.find("link", rel=lambda x: x and 'icon' in x.lower())
        logo_url = "https://cdn-icons-png.flaticon.com/512/3678/3678443.png"
        if icon_link and icon_link.get('href'):
            logo_url = urljoin(url, icon_link.get('href'))
            
        # 3. Color
        try:
            logo_resp = requests.get(logo_url, headers=headers, timeout=5)
            ct = ColorThief(BytesIO(logo_resp.content))
            dom_color = ct.get_color(quality=1)
            hex_color = '#{:02x}{:02x}{:02x}'.format(*dom_color)
        except:
            hex_color = "#333333"

        return {"name": title, "logo": logo_url, "color": hex_color}
    except Exception as e:
        return None

def generate_campaign_text(brand_dna):
    """Uses Gemini 3 Pro to brainstorm ideas"""
    try:
        # Using Gemini 3 Pro
        model = genai.GenerativeModel('gemini-3-pro-preview')
        
        prompt = f"""
        You are a marketing director. 
        Brand: {brand_dna['name']}
        Brand Color: {brand_dna['color']}
        
        Generate 3 high-impact social media campaign ideas.
        For each, give a "Title" and a 1-sentence "Concept".
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error with Gemini 3: {e}"

def generate_nano_banana_image(prompt):
    """Uses Nano Banana Pro (Gemini 3 Image) to generate visuals"""
    try:
        # Note: In the latest SDK, image models are often accessed via specialized methods
        # We try the standard pattern for Imagen/Gemini Image models
        image_model = genai.GenerativeModel('gemini-3-pro-image-preview')
        
        response = image_model.generate_content(prompt)
        
        # Extract image from response
        # Gemini 3 returns image parts directly in the response structure
        if response.parts and hasattr(response.parts[0], 'image'):
            return response.parts[0].image
            
        # Fallback for some SDK versions (Imagen style)
        if hasattr(response, 'images'):
             return response.images[0]
             
        return None
    except Exception as e:
        st.error(f"Nano Banana Pro Error: {e}")
        return None

# --- 4. APP INTERFACE ---

st.title("🍌 Pomelli AI")
st.caption("Powered by **Gemini 3** & **Nano Banana Pro**")

if "brand" not in st.session_state: st.session_state["brand"] = None
if "ideas" not in st.session_state: st.session_state["ideas"] = None
if "generated_img" not in st.session_state: st.session_state["generated_img"] = None

# STEP 1: SCAN
st.subheader("1. Business DNA")
url = st.text_input("Website URL", "https://www.tesla.com")
if st.button("🧬 Analyze DNA"):
    with st.spinner("Scanning..."):
        data = get_brand_dna(url)
        if data:
            st.session_state["brand"] = data
            st.session_state["ideas"] = None # Reset
            st.rerun()
        else:
            st.error("Could not scan website.")

if st.session_state["brand"]:
    b = st.session_state["brand"]
    col1, col2 = st.columns([1, 4])
    with col1:
        st.image(b['logo'], width=60)
    with col2:
        st.write(f"**{b['name']}**")
        st.color_picker("Brand Color", b['color'], disabled=True)
    
    st.divider()
    
    # STEP 2: IDEAS
    st.subheader("2. Campaign Strategy")
    if st.button("💡 Ask Gemini 3 for Ideas"):
        with st.spinner("Gemini 3 is thinking..."):
            ideas = generate_campaign_text(b)
            st.session_state["ideas"] = ideas
            
    if st.session_state["ideas"]:
        st.info(st.session_state["ideas"])
        
        st.divider()
        
        # STEP 3: CREATIVE
        st.subheader("3. Generate Creative (Nano Banana Pro)")
        
        topic = st.text_input("What should the image show?", f"A futuristic product shot for {b['name']}, cinematic lighting, 8k")
        
        if st.button("🎨 Generate with Nano Banana"):
            with st.spinner("Nano Banana Pro is rendering..."):
                # 1. Refine prompt with Gemini 3
                text_model = genai.GenerativeModel('gemini-3-pro-preview')
                refine_prompt = f"Optimize this image prompt for a pro photorealistic AI: '{topic}'. Keep it under 40 words."
                optimized_prompt = text_model.generate_content(refine_prompt).text
                
                st.caption(f"Optimized Prompt: {optimized_prompt}")
                
                # 2. Generate Image
                img = generate_nano_banana_image(optimized_prompt)
                
                if img:
                    st.session_state["generated_img"] = img
                else:
                    st.error("Image generation failed. Ensure your API key has access to 'gemini-3-pro-image-preview'.")

if st.session_state["generated_img"]:
    st.image(st.session_state["generated_img"], caption="Generated by Nano Banana Pro", use_container_width=True)
    
    # Download logic would go here (converting PIL image to bytes)
