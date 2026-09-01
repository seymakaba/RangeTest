import base64
import imghdr
import io
from datetime import datetime

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Ürün Etiket Doğrulama",
    page_icon="🧥",
    layout="wide",
)

# ------------------------------------------------------------------
# Varsayılan sınıf (etiket) kolonları — dosyanızda bunlar varsa
# otomatik olarak seçilir, yoksa kenar çubuğundan siz seçersiniz.
# ------------------------------------------------------------------
DEFAULT_LABEL_COLS = ["YakaTipi", "KolBoyu", "Desen", "CepTuru", "Stil"]
CUSTOM_OPTION = "✏️ Diğer (yeni etiket gir)"


# ------------------------------------------------------------------
# Yardımcı fonksiyonlar
# ------------------------------------------------------------------
def guess_image_col(df: pd.DataFrame) -> str | None:
    """Görsel URL'sini tutan kolonu isim ve içerikten tahmin eder."""
    name_hits = [c for c in df.columns if any(k in c.lower() for k in ["url", "link", "gorsel", "image", "img", "foto"])]
    for c in name_hits:
        sample = df[c].dropna().astype(str).head(20)
        if sample.str.startswith(("http://", "https://")).any():
            return c
    for c in df.columns:
        sample = df[c].dropna().astype(str).head(20)
        if len(sample) and sample.str.startswith(("http://", "https://")).all():
            return c
    return name_hits[0] if name_hits else None


def guess_label_cols(df: pd.DataFrame) -> list[str]:
    present = [c for c in DEFAULT_LABEL_COLS if c in df.columns]
    if present:
        return present
    # Confidence kolonu olan ve sayısal olmayan kolonları sınıf kabul et
    candidates = []
    for c in df.columns:
        conf_col = f"{c}_Confidence"
        if conf_col in df.columns:
            candidates.append(c)
    return candidates


def confidence_col(df: pd.DataFrame, col: str) -> str | None:
    cand = f"{col}_Confidence"
    return cand if cand in df.columns else None


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Duzeltilmis")
    return buffer.getvalue()


@st.cache_data(show_spinner=False, ttl=3600, max_entries=500)
def fetch_image_data_uri(img_url: str) -> str:
    """Görseli sunucu tarafında indirir ve base64 data URI olarak döner.

    Tarayıcı üzerinden doğrudan yüklemek yerine burada indirmemizin sebebi:
    birçok CDN, kendi sitesi dışından gelen (hotlink) istekleri engeller.
    Sunucu tarafında indirip base64 gömünce bu engel devre dışı kalır.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ),
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }
    resp = requests.get(img_url, headers=headers, timeout=12)
    resp.raise_for_status()
    content = resp.content
    kind = imghdr.what(None, h=content) or "jpeg"
    mime = f"image/{'jpeg' if kind == 'jpg' else kind}"
    b64 = base64.b64encode(content).decode("ascii")
    return f"data:{mime};base64,{b64}"


def render_zoomable_image(img_url: str, height: int = 430):
    """Görseli sunucu tarafında indirip, tıklayınca büyüyen (lightbox) şekilde gösterir."""
    try:
        data_uri = fetch_image_data_uri(img_url)
    except Exception as exc:  # noqa: BLE001
        st.error("Görsel indirilemedi.")
        with st.expander("Hata detayı"):
            st.write(f"URL: {img_url}")
            st.write(f"Hata: {exc}")
        st.markdown(f"[Görseli tarayıcıda açmayı dene]({img_url})")
        return

    html = f"""
    <html>
      <head>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/medium-zoom@1.0.8/dist/style.css">
        <style>
          html, body {{ margin:0; padding:0; background:transparent; }}
          .wrap {{
            display:flex; justify-content:center; align-items:center;
            height:{height - 20}px; background:#f4f4f6; border-radius:12px;
            border:1px solid #e5e5ea;
          }}
          img {{
            max-height:{height - 40}px; max-width:100%;
            object-fit:contain; cursor:zoom-in; border-radius:8px;
          }}
          .hint {{
            text-align:center; color:#8a8a90; font-family:sans-serif;
            font-size:12px; margin-top:6px;
          }}
        </style>
      </head>
      <body>
        <div class="wrap"><img id="zoomable" src="{data_uri}" /></div>
        <div class="hint">Büyütmek için görsele tıklayın</div>
        <script src="https://cdn.jsdelivr.net/npm/medium-zoom@1.0.8/dist/medium-zoom.min.js"></script>
        <script>
          mediumZoom('#zoomable', {{ margin: 24, background: 'rgba(0,0,0,0.92)' }});
        </script>
      </body>
    </html>
    """
    components.html(html, height=height + 10)


# ------------------------------------------------------------------
# Oturum durumu (session state)
# ------------------------------------------------------------------
def init_state():
    ss = st.session_state
    ss.setdefault("df", None)
    ss.setdefault("orig_df", None)
    ss.setdefault("image_col", None)
    ss.setdefault("label_cols", [])
    ss.setdefault("edited_rows", set())
    ss.setdefault("pos", 0)
    ss.setdefault("file_name", None)


init_state()

# ------------------------------------------------------------------
# Kenar çubuğu — dosya yükleme ve ayarlar
# ------------------------------------------------------------------
st.sidebar.title("🧥 Etiket Doğrulama")
uploaded = st.sidebar.file_uploader("Excel dosyasını yükleyin (.xlsx)", type=["xlsx"])

if uploaded is not None and st.session_state.file_name != uploaded.name:
    df = pd.read_excel(uploaded)
    st.session_state.df = df.copy()
    st.session_state.orig_df = df.copy()
    st.session_state.image_col = guess_image_col(df)
    st.session_state.label_cols = guess_label_cols(df)
    st.session_state.edited_rows = set()
    st.session_state.pos = 0
    st.session_state.file_name = uploaded.name

df = st.session_state.df

if df is None:
    st.title("Ürün Görseli — Etiket Doğrulama Arayüzü")
    st.info(
        "Başlamak için sol menüden, görsel URL kolonu eklenmiş Excel dosyanızı yükleyin.\n\n"
        "Beklenen yapı: her satır bir ürün; bir kolonda görsel URL'si, diğer kolonlarda "
        "**YakaTipi, KolBoyu, Desen, CepTuru, Stil** gibi tahmin edilen etiketler bulunur."
    )
    st.stop()

# Kolon eşleme ayarları
with st.sidebar.expander("⚙️ Kolon eşleme", expanded=(st.session_state.image_col is None)):
    cols = list(df.columns)
    image_col = st.selectbox(
        "Görsel URL kolonu",
        options=cols,
        index=cols.index(st.session_state.image_col) if st.session_state.image_col in cols else 0,
    )
    st.session_state.image_col = image_col

    label_cols = st.multiselect(
        "Doğrulanacak etiket (sınıf) kolonları",
        options=[c for c in cols if c != image_col and "_Confidence" not in c],
        default=[c for c in st.session_state.label_cols if c in cols],
    )
    st.session_state.label_cols = label_cols

image_col = st.session_state.image_col
label_cols = st.session_state.label_cols

if not label_cols:
    st.warning("Lütfen sol menüden en az bir etiket kolonu seçin.")
    st.stop()

# Benzersiz değer listelerini önceden hazırla (dropdown seçenekleri için)
unique_values = {c: sorted(df[c].dropna().astype(str).unique().tolist()) for c in label_cols}

# ------------------------------------------------------------------
# Filtre ve arama
# ------------------------------------------------------------------
st.sidebar.markdown("---")
filter_mode = st.sidebar.radio(
    "Gösterilecek kayıtlar",
    ["Tümü", "Sadece düşük güvenli (<0.5)", "Sadece düzenlenenler", "Sadece düzenlenmeyenler"],
)

if filter_mode == "Sadece düşük güvenli (<0.5)":
    conf_cols = [confidence_col(df, c) for c in label_cols if confidence_col(df, c)]
    mask = pd.Series(False, index=df.index)
    for cc in conf_cols:
        mask = mask | (df[cc] < 0.5)
    filtered_idx = df.index[mask].tolist()
elif filter_mode == "Sadece düzenlenenler":
    filtered_idx = [i for i in df.index if i in st.session_state.edited_rows]
elif filter_mode == "Sadece düzenlenmeyenler":
    filtered_idx = [i for i in df.index if i not in st.session_state.edited_rows]
else:
    filtered_idx = df.index.tolist()

search = st.sidebar.text_input("Ara (GorselAdi / MarkaKodu içinde)")
if search:
    search_cols = [c for c in ["GorselAdi", "MarkaKodu"] if c in df.columns]
    if search_cols:
        smask = pd.Series(False, index=df.index)
        for c in search_cols:
            smask = smask | df[c].astype(str).str.contains(search, case=False, na=False)
        filtered_idx = [i for i in filtered_idx if smask.get(i, False)]

if not filtered_idx:
    st.warning("Bu filtreye uyan kayıt yok.")
    st.stop()

st.session_state.pos = min(st.session_state.pos, len(filtered_idx) - 1)
st.session_state.pos = max(st.session_state.pos, 0)

# ------------------------------------------------------------------
# Gezinme (prev / next / doğrudan git)
# ------------------------------------------------------------------
st.sidebar.markdown("---")
c1, c2, c3 = st.sidebar.columns([1, 2, 1])
if c1.button("⬅️", use_container_width=True) and st.session_state.pos > 0:
    st.session_state.pos -= 1
    st.rerun()
c2.markdown(
    f"<div style='text-align:center; padding-top:6px;'>{st.session_state.pos + 1} / {len(filtered_idx)}</div>",
    unsafe_allow_html=True,
)
if c3.button("➡️", use_container_width=True) and st.session_state.pos < len(filtered_idx) - 1:
    st.session_state.pos += 1
    st.rerun()

jump = st.sidebar.number_input(
    "Kayda git (sıra no)", min_value=1, max_value=len(filtered_idx), value=st.session_state.pos + 1
)
if jump - 1 != st.session_state.pos:
    st.session_state.pos = int(jump) - 1
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.metric("Düzenlenen kayıt sayısı", len(st.session_state.edited_rows))
st.sidebar.metric("Toplam kayıt", len(df))

# ------------------------------------------------------------------
# Excel olarak dışa aktar
# ------------------------------------------------------------------
st.sidebar.markdown("---")
export_df = st.session_state.df.copy()
export_df["Duzenlendi_mi"] = export_df.index.isin(st.session_state.edited_rows)
excel_bytes = to_excel_bytes(export_df)
out_name = f"{st.session_state.file_name.rsplit('.', 1)[0]}_SonHal_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
st.sidebar.download_button(
    "💾 Son hali Excel olarak indir",
    data=excel_bytes,
    file_name=out_name,
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
    type="primary",
)

# ------------------------------------------------------------------
# Ana ekran — görsel + etiketler
# ------------------------------------------------------------------
row_id = filtered_idx[st.session_state.pos]
row = df.loc[row_id]

st.title("Ürün Görseli — Etiket Doğrulama")

info_bits = []
for c in ["GorselAdi", "MarkaKodu", "CinsiyetKodu"]:
    if c in df.columns:
        info_bits.append(f"**{c}:** {row[c]}")
st.caption(" &nbsp;|&nbsp; ".join(info_bits))

left, right = st.columns([1.1, 1])

with left:
    img_url = row.get(image_col)
    if isinstance(img_url, str) and img_url.startswith(("http://", "https://")):
        render_zoomable_image(img_url)
    else:
        st.warning("Bu satırda geçerli bir görsel URL'si bulunamadı.")

with right:
    st.subheader("Etiketler")
    for col in label_cols:
        current_val = row[col]
        current_val = "" if pd.isna(current_val) else str(current_val)
        conf_c = confidence_col(df, col)
        conf_txt = ""
        if conf_c and not pd.isna(row[conf_c]):
            conf_txt = f"  ·  güven: {row[conf_c]:.2f}"

        options = unique_values.get(col, [])
        options = list(dict.fromkeys(options + ([current_val] if current_val else [])))
        display_options = options + [CUSTOM_OPTION]
        default_index = display_options.index(current_val) if current_val in display_options else 0

        sel = st.selectbox(
            f"{col}{conf_txt}",
            display_options,
            index=default_index,
            key=f"sel_{col}_{row_id}",
        )

        new_val = sel
        if sel == CUSTOM_OPTION:
            new_val = st.text_input(
                f"Yeni değer — {col}",
                value=current_val if current_val not in options else "",
                key=f"custom_{col}_{row_id}",
            )
            if not new_val:
                new_val = current_val

        if new_val != current_val:
            st.session_state.df.at[row_id, col] = new_val
            st.session_state.edited_rows.add(row_id)

    if row_id in st.session_state.edited_rows:
        st.success("Bu kayıt düzenlendi ✓")

st.markdown("---")
st.caption(
    "İpucu: Etiketleri değiştirdikten sonra sol menüdeki **'Son hali Excel olarak indir'** "
    "butonuyla tüm düzeltmeleri tek dosyada dışa aktarabilirsiniz."
)
