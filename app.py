import io
import re
import requests
import streamlit as st
from PIL import Image
import instaloader

# Page configuration
st.set_page_config(
    page_title="InstaSlide — Instagram Carousel to PDF",
    page_icon="📸",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom Styling
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.3rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.2rem;
        background: linear-gradient(90deg, #833ab4, #fd1d1d, #fcb045);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .sub-title {
        text-align: center;
        color: #6c757d;
        font-size: 1.05rem;
        margin-bottom: 2rem;
    }
    .preview-card {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #e1e4e8;
        padding: 6px;
        background-color: #fafbfc;
    }
    </style>
    <div class="main-title">📸 InstaSlide PDF Converter</div>
    <div class="sub-title">Convert any public Instagram carousel or multi-image post into a clean PDF</div>
    """,
    unsafe_allow_html=True,
)


def extract_shortcode(url: str):
    """Cleanly extracts shortcode from multiple Instagram URL variations."""
    url = url.split("?")[0].rstrip("/")
    match = re.search(r"/(?:p|reel|tv)/([^/?#]+)", url)
    return match.group(1) if match else None


def fetch_instagram_data(shortcode: str):
    """Fetches post data using Instaloader with fallback headers."""
    L = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        save_metadata=False,
        download_comments=False,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    )
    post = instaloader.Post.from_shortcode(L.context, shortcode)

    image_urls = []
    if post.typename == "GraphSidecar":
        for node in post.get_sidecar_nodes():
            if not node.is_video:
                image_urls.append(node.display_url)
    elif not post.is_video:
        image_urls.append(post.url)

    return post, image_urls


def format_for_a4(img: Image.Image, landscape: bool = False):
    """Fits an image onto a white A4-proportioned canvas without distortion."""
    # A4 standard at 150 DPI
    a4_w, a4_h = (1754, 1240) if landscape else (1240, 1754)
    canvas = Image.new("RGB", (a4_w, a4_h), (255, 255, 255))

    # Resize image keeping aspect ratio
    img_ratio = img.width / img.height
    a4_ratio = a4_w / a4_h

    if img_ratio > a4_ratio:
        new_w = a4_w - 80
        new_h = int(new_w / img_ratio)
    else:
        new_h = a4_h - 80
        new_w = int(new_h * img_ratio)

    resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    offset = ((a4_w - new_w) // 2, (a4_h - new_h) // 2)
    canvas.paste(resized_img, offset)
    return canvas


# --- Search & Options Section ---
col1, col2 = st.columns([3, 1])

with col1:
    post_url = st.text_input(
        "Instagram Post URL",
        placeholder="https://www.instagram.com/p/C3x9.../",
        help="Paste a link to any public post or carousel",
    )

with col2:
    pdf_layout = st.selectbox(
        "Page Layout",
        options=["Original Image Dimensions", "A4 Portrait", "A4 Landscape"],
        index=0,
    )

generate_btn = st.button("🚀 Fetch & Convert to PDF", use_container_width=True, type="primary")

if generate_btn:
    if not post_url.strip():
        st.warning("⚠️ Please paste a valid Instagram URL first.")
    else:
        shortcode = extract_shortcode(post_url.strip())
        if not shortcode:
            st.error("❌ Invalid Instagram link format. Make sure it contains `/p/` or `/reel/`.")
        else:
            with st.status("Fetching slides from Instagram...", expanded=True) as status:
                try:
                    post, image_urls = fetch_instagram_data(shortcode)

                    if not image_urls:
                        status.update(label="No images found", state="error")
                        st.error("⚠️ This post appears to be video-only or private.")
                    else:
                        st.write(f"✅ Found **{len(image_urls)}** slide(s) by **@{post.owner_username}**")

                        # Progress bar for downloading images
                        progress_bar = st.progress(0, text="Downloading high-res images...")
                        headers = {"User-Agent": "Mozilla/5.0"}
                        pil_images = []

                        for i, url in enumerate(image_urls):
                            res = requests.get(url, headers=headers, timeout=15)
                            if res.status_code == 200:
                                img = Image.open(io.BytesIO(res.content)).convert("RGB")

                                if pdf_layout == "A4 Portrait":
                                    img = format_for_a4(img, landscape=False)
                                elif pdf_layout == "A4 Landscape":
                                    img = format_for_a4(img, landscape=True)

                                pil_images.append(img)
                            progress_bar.progress((i + 1) / len(image_urls), text=f"Processing slide {i+1} of {len(image_urls)}...")

                        # Compile PDF buffer
                        pdf_buffer = io.BytesIO()
                        pil_images[0].save(
                            pdf_buffer,
                            format="PDF",
                            save_all=True,
                            append_images=pil_images[1:],
                            resolution=100.0,
                        )
                        pdf_buffer.seek(0)

                        status.update(label="🎉 Conversion complete!", state="complete", expanded=False)

                        # Success UI & Action Row
                        st.balloons()
                        st.success(f"Successfully generated a {len(pil_images)}-page PDF!")

                        st.download_button(
                            label=f"⬇️ Download {post.owner_username}_{shortcode}.pdf",
                            data=pdf_buffer,
                            file_name=f"{post.owner_username}_{shortcode}.pdf",
                            mime="application/pdf",
                            type="primary",
                            use_container_width=True,
                        )

                        # Slide Preview Gallery
                        st.markdown("### 🖼️ Slides Preview")
                        cols = st.columns(min(len(pil_images), 5))
                        for idx, img in enumerate(pil_images):
                            with cols[idx % 5]:
                                st.image(img, caption=f"Slide {idx + 1}", use_container_width=True)

                except Exception as e:
                    status.update(label="Failed to fetch post", state="error")
                    st.error(f"Error: {e}")
                    st.info("Tip: If Instagram blocks the request, make sure the post is 100% public and not age-restricted.")
