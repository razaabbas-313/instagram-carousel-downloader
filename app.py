import streamlit as st
import instaloader
import requests
from PIL import Image
import io
import re

st.set_page_config(page_title="Insta Carousel to PDF", page_icon="📑", layout="centered")

st.title("📑 Instagram Carousel to PDF")
st.caption("Paste any public Instagram carousel link to download all slides as a single PDF.")

post_url = st.text_input("Instagram Post URL", placeholder="https://www.instagram.com/p/...")

def extract_shortcode(url):
    match = re.search(r"/(?:p|reel)/([^/?]+)", url)
    return match.group(1) if match else None

if st.button("Generate PDF", type="primary"):
    if not post_url.strip():
        st.warning("Please enter a valid Instagram URL.")
    else:
        shortcode = extract_shortcode(post_url.strip())
        if not shortcode:
            st.error("Invalid Instagram URL format.")
        else:
            with st.spinner("Fetching carousel slides from Instagram..."):
                try:
                    L = instaloader.Instaloader(
                        download_pictures=False,
                        download_videos=False,
                        download_video_thumbnails=False,
                        save_metadata=False,
                        download_comments=False
                    )
                    post = instaloader.Post.from_shortcode(L.context, shortcode)
                    
                    image_urls = []
                    if post.typename == "GraphSidecar":
                        for node in post.get_sidecar_nodes():
                            if not node.is_video:
                                image_urls.append(node.display_url)
                    elif not post.is_video:
                        image_urls.append(post.url)
                    
                    if not image_urls:
                        st.error("No image slides found in this post (it may be a video or private post).")
                    else:
                        images = []
                        headers = {"User-Agent": "Mozilla/5.0"}
                        
                        for u in image_urls:
                            res = requests.get(u, headers=headers)
                            if res.status_code == 200:
                                img = Image.open(io.BytesIO(res.content))
                                if img.mode != "RGB":
                                    img = img.convert("RGB")
                                images.append(img)
                        
                        pdf_buffer = io.BytesIO()
                        images[0].save(
                            pdf_buffer,
                            format="PDF",
                            save_all=True,
                            append_images=images[1:],
                            resolution=100.0
                        )
                        pdf_buffer.seek(0)
                        
                        st.success(f"Successfully converted {len(images)} slides!")
                        st.download_button(
                            label="⬇️ Download PDF",
                            data=pdf_buffer,
                            file_name=f"instagram_{shortcode}.pdf",
                            mime="application/pdf"
                        )
                except Exception as e:
                    st.error(f"Error fetching post: {e}")
