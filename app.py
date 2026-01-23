import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from colorthief import ColorThief
from io import BytesIO
from urllib.parse import urljoin, urlparse
from PIL import Image, ImageDraw, ImageFont, ImageOps
import random
import os
from dotenv import load_dotenv

# --- 1. SETUP & CONFIG ---
st.set_page_config(page_title="Pomelli Clone", page_icon="💡", layout="centered")

# Load API Key from .env file for security
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    st.sidebar.error("Gemini API Key not found. Please add it to your .env file.")
    st.sidebar.markdown("Create a `.env` file with `GEMINI_API_KEY=YOUR_KEY`")
else:
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        st.sidebar.error(f"API Key configuration error: {e}")

# --- 2. SIDEBAR FOR SETTINGS ---
with st.sidebar:
    st.header("⚙️ Settings")
    if api_key:
        st.success("Gemini API Key loaded.")
    st.markdown("---")
    st.header("Model Options")
    # Allow selection of Gemini models for text generation
    gemini_model_options = ["gemini-1.5-flash", "gemini-1.5-pro"] # Add others if needed
    selected_gemini_model = st.selectbox("Select Gemini Model (for text)", gemini_model_options)
    
    st.markdown("---")
    st.header("Image Generation")
    st.write("Uses free Stable Diffusion API.")
    st.markdown("---")
    st.header("Help")
    st.markdown("[Get Gemini Key](https://aistudio.google.com/app/apikey)")

# --- 3. HELPER FUNCTIONS ---

def get_brand_dna(url):
    """Extracts Logo, Title, and Color from a website URL."""
    if not url.startswith('http'):
        url = 'https://' + url
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, timeout=10, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title = soup.title.string.strip() if soup.title else "Brand"
        
        icon_link = soup.find("link", rel=lambda x: x and 'icon' in x.lower())
        logo_url = "https://cdn-icons-png.flaticon.com/512/3678/3678443.png" # Default
        if icon_link and icon_link.get('href'):
            logo_url = urljoin(url, icon_link.get('href'))

        try:
            logo_resp = requests.get(logo_url, headers=headers, timeout=5)
            ct = ColorThief(BytesIO(logo_resp.content))
            dom_color = ct.get_color(quality=1)
            hex_color = '#{:02x}{:02x}{:02x}'.format(*dom_color)
        except:
            hex_color = "#4A90E2" # Default blue

        return {"name": title, "logo": logo_url, "color": hex_color}
    except Exception as e:
        st.error(f"Error getting brand DNA: {e}")
        return None

def generate_campaign_ideas(brand_dna):
    """Uses Gemini to generate campaign ideas based on Brand DNA."""
    if not api_key: return "Gemini API Key required for campaign ideas."
    try:
        model = genai.GenerativeModel(selected_gemini_model)
        prompt = f"""
        Generate 3 distinct social media campaign ideas for a business with the following DNA:
        Brand Name: {brand_dna['name']}
        Tone: Professional but engaging.
        Key Color: {brand_dna['color']}
        
        For each idea, provide:
        1. A catchy Campaign Title.
        2. A brief Campaign Description (1-2 sentences).
        3. A suggested Post Topic for Gemini to elaborate on later.
        
        Format the output clearly, perhaps using bullet points or numbered lists.
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating campaign ideas: {e}"

def generate_caption(brand_dna, campaign_idea_prompt, campaign_topic):
    """Uses Gemini to generate a specific caption."""
    if not api_key: return "Gemini API Key required."
    try:
        model = genai.GenerativeModel(selected_gemini_model)
        prompt = f"""
        Based on the following campaign context, write a short, impactful social media caption (max 30 words).
        
        Brand DNA:
        - Name: {brand_dna['name']}
        - Color: {brand_dna['color']}
        
        Campaign Idea: {campaign_idea_prompt}
        Specific Topic for this Post: {campaign_topic}
        
        Caption Requirements:
        - Tone: Professional and engaging.
        - Action: Encourage user engagement (e.g., "Learn more", "Shop now").
        - Format: No hashtags.
        """
        response = model.generate_content(prompt)
        return response.text.strip().replace('"', '')
    except Exception as e:
        return f"Error generating caption: {e}"

def generate_stable_diffusion_image(prompt):
    """Generates an image using a free Stable Diffusion API."""
    # Using a free, public API. Be mindful of rate limits.
    # This API is for demonstration; for production, consider paid services.
    try:
        api_url = "https://api.pollinations.ai/prompt/"
        # Clean prompt for URL encoding
        encoded_prompt = requests.utils.quote(prompt)
        # Use a consistent image size and model (e.g., flux)
        full_url = f"{api_url}{encoded_prompt}?width=1080&height=1080&nologo=true&model=flux&seed={random.randint(1, 10000)}"
        
        # We don't need the image data directly, just the URL
        return full_url 
    except Exception as e:
        st.error(f"Error generating image URL: {e}")
        return None

# --- 4. MAIN APP FLOW ---

st.title("💡 Pomelli: AI Marketing Studio")
st.write("Generate on-brand campaigns and creatives automatically.")

# Session state initialization
if "brand_dna" not in st.session_state: st.session_state["brand_dna"] = None
if "campaign_ideas" not in st.session_state: st.session_state["campaign_ideas"] = None
if "selected_campaign_idea" not in st.session_state: st.session_state["selected_campaign_idea"] = None
if "user_prompt" not in st.session_state: st.session_state["user_prompt"] = ""
if "generated_caption" not in st.session_state: st.session_state["generated_caption"] = ""
if "generated_image_url" not in st.session_state: st.session_state["generated_image_url"] = None

# --- Step 1: Build Business DNA ---
st.header("1. Build Your Business DNA")
url_input = st.text_input("Enter your Website URL:", placeholder="e.g., https://www.nike.com")

if st.button("Analyze Website"):
    if not url_input:
        st.warning("Please enter a website URL.")
    elif not api_key:
        st.error("Please enter your Gemini API Key in the sidebar.")
    else:
        with st.spinner("Analyzing brand identity..."):
            brand_data = get_brand_dna(url_input)
            if brand_data:
                st.session_state["brand_dna"] = brand_data
                st.success(f"Brand DNA for '{brand_data['name']}' created!")
                # Automatically move to next step if DNA is found
                if st.session_state["brand_dna"]:
                    st.session_state["campaign_ideas"] = None # Reset ideas if DNA changes
            else:
                st.error("Failed to analyze website. Please check the URL.")

# Display Brand DNA if available
if st.session_state["brand_dna"]:
    b = st.session_state["brand_dna"]
    st.markdown("---")
    st.subheader("Your Brand Profile")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        st.image(b['logo'], width=80, caption="Logo")
    with col2:
        st.text_input("Brand Name", b['name'], key="brand_name_input")
        b['name'] = st.session_state.brand_name_input # Update if changed
    with col3:
        b['color'] = st.color_picker("Brand Color:", b['color'])
    st.markdown("---")

    # --- Step 2: Generate Campaign Ideas ---
    st.header("2. Get Campaign Ideas")
    if st.button("Generate Campaign Ideas"):
        if not api_key:
            st.error("Gemini API Key is required.")
        else:
            with st.spinner("Brainstorming campaign ideas..."):
                st.session_state["campaign_ideas"] = generate_campaign_ideas(st.session_state["brand_dna"])
                st.session_state["selected_campaign_idea"] = None # Reset selection

    if st.session_state["campaign_ideas"]:
        st.subheader("Choose a Campaign Focus:")
        
        # Display ideas and allow selection
        ideas = st.session_state["campaign_ideas"].split('\n')
        
        # Simple way to present ideas - user selects by number
        idea_mapping = {}
        display_ideas = []
        for item in ideas:
            if item.strip():
                if "Campaign Title:" in item:
                    campaign_title = item.split(":", 1)[1].strip()
                    display_ideas.append(campaign_title)
                    idea_mapping[campaign_title] = item # Store full idea details
        
        if display_ideas:
            selected_title = st.selectbox("Select an Idea", ["Or enter your own prompt below"] + display_ideas)
            
            if selected_title != "Or enter your own prompt below":
                st.session_state["selected_campaign_idea"] = idea_mapping[selected_title]
                st.info(f"Selected: {selected_title}")
            else:
                st.session_state["selected_campaign_idea"] = None
                st.session_state["user_prompt"] = st.text_area("Enter your custom campaign prompt:", key="custom_prompt_input")
                st.session_state["user_prompt"] = st.session_state.custom_prompt_input # Update if changed

        else:
            st.warning("Could not parse campaign ideas. Please check the output.")
            st.text(st.session_state["campaign_ideas"])
    
    st.markdown("---")

    # --- Step 3: Edit and Create Creatives ---
    st.header("3. Create Your Creative")
    
    current_campaign_context = st.session_state.get("selected_campaign_idea")
    if not current_campaign_context and st.session_state.get("user_prompt"):
        current_campaign_context = f"User prompt: {st.session_state['user_prompt']}"
        
    post_topic = st.text_input("Describe the specific post topic:", key="post_topic_input")
    
    if st.button("Generate Creative"):
        if not api_key:
            st.error("Gemini API Key required.")
        elif not current_campaign_context:
            st.error("Please select or enter a campaign idea first.")
        elif not post_topic:
            st.error("Please describe the specific post topic.")
        else:
            with st.spinner("Designing creative..."):
                # 1. Generate Caption
                st.session_state["generated_caption"] = generate_caption(
                    st.session_state["brand_dna"],
                    current_campaign_context,
                    post_topic
                )
                
                # 2. Generate Image Prompt (using Brand DNA and Topic)
                image_prompt = f"""
                {current_campaign_context}, specifically about "{post_topic}".
                Brand: {st.session_state['brand_dna']['name']}.
                Style: {st.session_state['brand_dna']['color']} as dominant color. Professional, engaging, high quality.
                Visuals: Use relevant imagery for the topic.
                """
                st.session_state["generated_image_url"] = generate_stable_diffusion_image(image_prompt)

    # Display the generated creative
    if st.session_state["generated_image_url"]:
        st.markdown("### Your Creative:")
        col1, col2 = st.columns(2)
        
        with col1:
            st.image(st.session_state["generated_image_url"], caption="Generated Image", use_container_width=True)
        
        with col2:
            st.text_area("Caption:", st.session_state["generated_caption"], height=200)
            st.markdown(f"[Download Image]({st.session_state['generated_image_url']})")
