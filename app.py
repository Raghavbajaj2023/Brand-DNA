import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from colorthief import ColorThief
from io import BytesIO
from urllib.parse import urljoin, urlparse
from PIL import Image, ImageDraw, ImageFont, ImageOps
import random

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Pomelli Clone", page_icon="🧪", layout="centered")

# Custom CSS to make it look a bit more like the Pomelli Dark Theme
st.markdown("""
<style>
    .step-header { font-size: 24px; font-weight: bold; margin-bottom: 10px; color: #a4c639; }
    .dna-box { background-color: #2b2b2b; padding: 20px; border-radius: 10px; border: 1px solid #444; }
</style>
""", unsafe_allow_html=True)

# --- STATE MANAGEMENT (Tracks which step the user is on) ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'dna' not in st.session_state: st.session_state.dna = None
if 'ideas' not in st.session_state: st.session_state.ideas = []
if 'selected_idea' not in st.session_state: st.session_state.selected_idea = ""

# --- SIDEBAR: API KEY ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3678/3678443.png", width=50)
    st.title("Settings")
    api_key = st.text_input("Google Gemini API Key", type="password")
    st.markdown("[Get Free Key](https://aistudio.google.com/app/apikey)")

# --- FUNCTIONS ---

def scrape_website(url):
    """Step 1: Extract Brand DNA (Tone, Colors, Images)"""
    if not url.startswith('http'): url = 'https://' + url
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(url, timeout=10, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Title & Text for Tone Analysis
        title = soup.title.string.strip() if soup.title else "Brand"
        paragraphs = [p.text for p in soup.find_all('p')[:10]] # Get first 10 paragraphs
        website_text = " ".join(paragraphs)
        
        # 2. Logo & Colors
        icon_link = soup.find("link", rel=lambda x: x and 'icon' in x.lower())
        logo_url = "https://cdn-icons-png.flaticon.com/512/3678/3678443.png"
        if icon_link and icon_link.get('href'):
            logo_url = urljoin(url, icon_link.get('href'))

        try:
            logo_resp = requests.get(logo_url, headers=headers, timeout=5)
            ct = ColorThief(BytesIO(logo_resp.content))
            dom_color = ct.get_color(quality=1)
            hex_color = '#{:02x}{:02x}{:02x}'.format(*dom_color)
        except:
            hex_color = "#D4E157" # Pomelli Green Fallback

        # 3. Images
        images = []
        for img in soup.find_all('img'):
            src = img.get('src')
            if src:
                full_url = urljoin(url, src)
                if any(x in full_url.lower() for x in ['.jpg', '.jpeg', '.png', '.webp']):
                    if full_url not in images: images.append(full_url)
        
        return {
            "name": title, "logo": logo_url, "color": hex_color, 
            "images": images[:8], "text": website_text
        }
    except Exception as e:
        return None

def analyze_tone(text, model):
    """Uses Gemini to figure out the brand's 'Tone of Voice'"""
    prompt = f"Analyze this website text and describe the brand's 'Tone of Voice' in exactly 3 adjectives (e.g., Professional, Bold, Friendly): {text[:2000]}"
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return "Modern, Engaging, Professional"

def generate_campaign_ideas(brand_name, tone, model):
    """Step 2: Generate Marketing Ideas"""
    prompt = f"Generate 3 short, distinct social media campaign ideas for '{brand_name}' using a '{tone}' tone. Example: 'Flash Sale Alert', 'Behind the Scenes', 'Product Spotlight'. Output as a numbered list."
    try:
        response = model.generate_content(prompt)
        # Parse the numbered list into a Python list
        lines = [line.strip().lstrip("1234567890. ") for line in response.text.split("\n") if line.strip()]
        return lines[:3]
    except:
        return ["Launch New Product", "Customer Testimonials", "Seasonal Sale Promotion"]

def create_branded_creative(image_url, logo_url, brand_name, headline, color):
    """Step 3: Overlay Brand DNA onto Website Image"""
    try:
        # Load background image
        resp = requests.get(image_url)
        base = Image.open(BytesIO(resp.content)).convert("RGBA")
        base = ImageOps.fit(base, (1080, 1080), Image.Resampling.LANCZOS)
        
        # Add a colored gradient/overlay box at the bottom
        overlay = Image.new("RGBA", (1080, 1080), (0,0,0,0))
        draw = ImageDraw.Draw(overlay)
        
        # Convert hex to RGB for the overlay
        color = color.lstrip('#')
        r, g, b = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        draw.rectangle([(0, 650), (1080, 1080)], fill=(r, g, b, 230)) # 90% opacity
        
        final_img = Image.alpha_composite(base, overlay)
        draw = ImageDraw.Draw(final_img)

        # Add Logo
        try:
            l_resp = requests.get(logo_url)
            logo = Image.open(BytesIO(l_resp.content)).convert("RGBA")
            logo.thumbnail((120, 120))
            final_img.paste(logo, (480, 50), logo)
        except: pass

        # Add Headline Text
        try: font = ImageFont.truetype("DejaVuSans-Bold.ttf", 65)
        except: font = ImageFont.load_default() # Fallback

        import textwrap
        lines = textwrap.wrap(headline, width=20)
        y_text = 750
        for line in lines:
            draw.text((100, y_text), line, font=font, fill="white")
            y_text += 70

        return final_img
    except Exception as e:
        return None


# --- UI LAYOUT ---

st.title("🧪 Pomelli: AI Marketing Generator")
st.write("Generate high-quality, on-brand creatives in 3 steps.")

# Progress Bar
progress = st.progress(st.session_state.step / 3.0)

# ==========================================
# STEP 1: BUSINESS DNA
# ==========================================
if st.session_state.step == 1:
    st.markdown('<div class="step-header">1. Build your Business DNA</div>', unsafe_allow_html=True)
    st.write("Enter your website and we'll analyze your brand and business.")
    
    url = st.text_input("Website URL:", placeholder="https://yourbusiness.com")
    
    if st.button("🧬 Generate Business DNA"):
        if not api_key: st.error("Please add your Gemini API Key in the sidebar.")
        elif not url: st.warning("Please enter a URL.")
        else:
            with st.spinner("Analyzing website text, colors, and images..."):
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # Scrape
                dna = scrape_website(url)
                if dna:
                    # Analyze Tone
                    dna['tone'] = analyze_tone(dna['text'], model)
                    st.session_state.dna = dna
                    st.session_state.step = 2
                    st.rerun() # Move to Step 2
                else:
                    st.error("Failed to analyze website. Please check the URL.")

# ==========================================
# STEP 2: CAMPAIGN IDEAS
# ==========================================
elif st.session_state.step == 2:
    st.markdown('<div class="step-header">2. Get Campaign Ideas</div>', unsafe_allow_html=True)
    dna = st.session_state.dna
    
    # Show DNA Profile
    with st.expander("🧬 View Extracted Business DNA", expanded=True):
        col1, col2, col3 = st.columns([1,2,2])
        col1.image(dna['logo'], width=60)
        col2.write(f"**Tone:** {dna['tone']}")
        col3.color_picker("Brand Color:", dna['color'], disabled=True)
        st.write("**Extracted Images:**")
        st.image(dna['images'][:4], width=100)

    st.write("We used your Business DNA to create tailored marketing ideas:")
    
    # Generate Ideas if not already done
    if not st.session_state.ideas:
        with st.spinner("Brainstorming campaign ideas..."):
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            st.session_state.ideas = generate_campaign_ideas(dna['name'], dna['tone'], model)

    # User Selection
    selected = st.radio("Choose a campaign focus:", st.session_state.ideas + ["Write my own idea..."])
    custom_idea = ""
    if selected == "Write my own idea...":
        custom_idea = st.text_input("What is your campaign idea?")

    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        if st.button("⬅️ Back"):
            st.session_state.step = 1
            st.rerun()
    with col_btn2:
        if st.button("🎨 Next: Generate Creatives"):
            st.session_state.selected_idea = custom_idea if custom_idea else selected
            st.session_state.step = 3
            st.rerun()

# ==========================================
# STEP 3: GENERATE CREATIVES
# ==========================================
elif st.session_state.step == 3:
    st.markdown('<div class="step-header">3. Generate Creatives</div>', unsafe_allow_html=True)
    st.write(f"Creating assets for: **{st.session_state.selected_idea}**")
    
    dna = st.session_state.dna
    
    if st.button("✨ Regenerate Creatives"):
        st.rerun()

    # Generate the actual creatives using the scraped images
    with st.spinner("Designing on-brand creatives..."):
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 1. AI writes Headlines
        prompt = f"Write a 4-word catchy headline for a social media ad about '{st.session_state.selected_idea}' for '{dna['name']}'. Tone: {dna['tone']}. No quotes."
        response = model.generate_content(prompt)
        headline = response.text.strip()
        
        # 2. Display Generated Images (Using the first 2 scraped images)
        st.subheader("Your Generated Assets")
        cols = st.columns(2)
        
        for i, img_url in enumerate(dna['images'][:2]):
            creative = create_branded_creative(img_url, dna['logo'], dna['name'], headline, dna['color'])
            if creative:
                with cols[i]:
                    st.image(creative, use_container_width=True)
                    # Download
                    buf = BytesIO()
                    creative.save(buf, format="PNG")
                    st.download_button(f"Download Asset {i+1}", buf.getvalue(), f"pomelli_asset_{i+1}.png", "image/png")

    if st.button("⬅️ Back to Ideas"):
        st.session_state.step = 2
        st.rerun()
