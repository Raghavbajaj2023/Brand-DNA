import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from colorthief import ColorThief
from io import BytesIO
from urllib.parse import urljoin, urlparse
from PIL import Image, ImageDraw, ImageFont, ImageOps

# --- 1. SETUP & CONFIG ---
st.set_page_config(page_title="Pomelli: Real Image Remix", page_icon="🖼️", layout="centered")

# --- 2. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("Google Gemini API Key", type="password")
    st.markdown("[Get Key Here](https://aistudio.google.com/app/apikey)")

# --- 3. HELPER FUNCTIONS ---

def get_brand_dna(url):
    """Extracts Logo, Title, and Color"""
    if not url.startswith('http'): url = 'https://' + url
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, timeout=10, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title = soup.title.string.strip() if soup.title else "Brand"
        
        # Find Logo
        icon_link = soup.find("link", rel=lambda x: x and 'icon' in x.lower())
        logo_url = "https://cdn-icons-png.flaticon.com/512/3678/3678443.png"
        if icon_link and icon_link.get('href'):
            logo_url = urljoin(url, icon_link.get('href'))

        # Extract Color
        try:
            logo_resp = requests.get(logo_url, headers=headers, timeout=5)
            ct = ColorThief(BytesIO(logo_resp.content))
            dom_color = ct.get_color(quality=1)
            hex_color = '#{:02x}{:02x}{:02x}'.format(*dom_color)
        except:
            hex_color = "#000000"

        return {"name": title, "logo": logo_url, "color": hex_color}
    except:
        return None

def scrape_website_images(url):
    """Finds all standard images on the page"""
    if not url.startswith('http'): url = 'https://' + url
    headers = {"User-Agent": "Mozilla/5.0"}
    image_urls = []
    
    try:
        response = requests.get(url, timeout=10, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all img tags
        for img in soup.find_all('img'):
            src = img.get('src')
            if src:
                full_url = urljoin(url, src)
                # Filter out tiny icons or SVGs (basic filter)
                ext = urlparse(full_url).path.lower()
                if any(x in ext for x in ['.jpg', '.jpeg', '.png', '.webp']):
                    if full_url not in image_urls:
                        image_urls.append(full_url)
        
        return image_urls[:20] # Return top 20 images to save memory
    except:
        return []

def create_social_post(base_img_url, logo_url, brand_name, headline, brand_color):
    """Composites the final image: Base Photo + Dark Overlay + Text + Logo"""
    try:
        # 1. Load Base Image
        response = requests.get(base_img_url)
        base_img = Image.open(BytesIO(response.content)).convert("RGBA")
        
        # 2. Resize to Square (Instagram style) - 1080x1080
        target_size = (1080, 1080)
        base_img = ImageOps.fit(base_img, target_size, method=Image.Resampling.LANCZOS)
        
        # 3. Create Drawing Context
        final_img = Image.new("RGBA", target_size)
        final_img.paste(base_img, (0,0))
        draw = ImageDraw.Draw(final_img)
        
        # 4. Add "Gradient" Overlay (Dark at bottom to make text pop)
        # We simulate a gradient by drawing a semi-transparent box at the bottom
        overlay = Image.new("RGBA", target_size, (0,0,0,0))
        overlay_draw = ImageDraw.Draw(overlay)
        # Draw a black box with 60% opacity at the bottom half
        overlay_draw.rectangle([(0, 500), (1080, 1080)], fill=(0, 0, 0, 160))
        final_img = Image.alpha_composite(final_img, overlay)
        draw = ImageDraw.Draw(final_img)

        # 5. Add Logo (Top Center)
        try:
            logo_resp = requests.get(logo_url)
            logo = Image.open(BytesIO(logo_resp.content)).convert("RGBA")
            logo.thumbnail((150, 150)) # Resize logo
            # Center the logo
            logo_x = (1080 - logo.width) // 2
            final_img.paste(logo, (logo_x, 80), logo)
        except:
            pass # Skip logo if fails

        # 6. Add Text (Headline)
        # Simple text wrapping logic
        font_size = 60
        # NOTE: Since we can't easily upload fonts, we use the default PIL font 
        # which is small, or try to load a system font if possible. 
        # For this demo, we use default but scale logic is limited.
        # Ideally, you'd include a .ttf file in your repo.
        
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
        except:
            font = ImageFont.load_default()
            # Default font is tiny, so we can't do much with it without a .ttf file
            # But let's try to proceed.

        # Draw Headline
        text_y = 650
        margin = 100
        import textwrap
        lines = textwrap.wrap(headline, width=25) # Wrap text
        
        for line in lines:
            # We calculate width to center it
            # precise calculation depends on font, simplified here
            draw.text((margin, text_y), line, font=font, fill="white")
            text_y += font_size + 10
            
        # Draw "Shop Now" Button
        button_y = text_y + 50
        draw.rectangle([(margin, button_y), (margin + 300, button_y + 80)], fill=brand_color)
        draw.text((margin + 80, button_y + 25), "LEARN MORE", font=font, fill="white")

        return final_img
        
    except Exception as e:
        print(e)
        return None

# --- 4. MAIN APP INTERFACE ---

st.title("🖼️ Brand Remix Studio")
st.write("Turn your existing website photos into social media ads.")

# A. SCANNER
url_input = st.text_input("Website URL", placeholder="https://www.nike.com")
if "scanned_images" not in st.session_state:
    st.session_state["scanned_images"] = []
if "brand_info" not in st.session_state:
    st.session_state["brand_info"] = None

if st.button("🔍 Scan Website"):
    if not url_input:
        st.warning("Enter a URL")
    else:
        with st.spinner("Finding logos and products..."):
            # 1. Get DNA
            st.session_state["brand_info"] = get_brand_dna(url_input)
            # 2. Get Images
            st.session_state["scanned_images"] = scrape_website_images(url_input)
            
            if not st.session_state["scanned_images"]:
                st.warning("No images found. The site might block scrapers. Try a different site.")
            else:
                st.success(f"Found {len(st.session_state['scanned_images'])} images!")

# B. EDITOR
if st.session_state["brand_info"] and st.session_state["scanned_images"]:
    b = st.session_state["brand_info"]
    
    st.divider()
    st.subheader("1. Select an Image")
    
    # Show images in a grid
    imgs = st.session_state["scanned_images"]
    
    # Let user select by index using a clearer selector
    # We display thumbnails to help them choose
    cols = st.columns(4)
    for i, img_url in enumerate(imgs[:8]): # Show first 8
        with cols[i % 4]:
            st.image(img_url, use_container_width=True)
            st.caption(f"Image #{i+1}")

    selected_index = st.number_input("Enter Image # to use:", min_value=1, max_value=len(imgs), value=1) - 1
    selected_img_url = imgs[selected_index]
    
    st.divider()
    st.subheader("2. Customize Design")
    
    col1, col2 = st.columns(2)
    with col1:
        topic = st.text_input("Topic", "New Collection Available")
        b['color'] = st.color_picker("Brand Color", b['color'])
    
    if st.button("✨ Generate Creative"):
        if not api_key:
            st.error("Need Gemini API Key")
        else:
            with st.spinner("Designing..."):
                # 1. AI writes the text
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = f"Write a 5-word catchy headline for {b['name']} about {topic}. No hashtags. No quotes."
                try:
                    resp = model.generate_content(prompt)
                    headline = resp.text.strip().replace('"', '')
                except:
                    headline = topic.upper()

                # 2. Python designs the image
                final_image = create_social_post(
                    selected_img_url, 
                    b['logo'], 
                    b['name'], 
                    headline, 
                    b['color']
                )
                
                if final_image:
                    st.image(final_image, caption="Final Ad Creative")
                    
                    # Download Button
                    buf = BytesIO()
                    final_image.save(buf, format="PNG")
                    st.download_button("Download Image", buf.getvalue(), "ad_creative.png", "image/png")
                else:
                    st.error("Error creating image. The source image format might not be supported.")
